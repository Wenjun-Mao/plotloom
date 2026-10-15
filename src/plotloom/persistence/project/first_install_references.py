"""Named independence contract for exploratory work during first installation."""
from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, OperationScope
from ...autopilot_early_references import EarlyReferenceDiscovery
from ...exceptions import InvalidTransitionError
from ..codec import stable_hash
from ..schema import (
    ArtReferenceProposalRow,
    AutopilotCheckpointRow,
    AutopilotRunRow,
    CharacterReferenceProposalRow,
    ProductionBridgeAdmissionRow,
)
from .art import ProjectArtPersistence
from .autopilot_bindings import assert_checkpoint_binding
from .autopilot_closure import material_closure
from .cast import ProjectCastPersistence
from .media_character_references import cast_reference_context_from_subject


def first_install_reference_is_independent(access, session, project_id, proposal):
    """No skip list: prove exact same-run work with unchanged exploratory inputs."""
    owner = ("character-reference" if isinstance(proposal, CharacterReferenceProposalRow)
        else "art-reference" if isinstance(proposal, ArtReferenceProposalRow) else None)
    authority = access.authority()
    if owner is None or authority is None or authority.scope != OperationScope.INSTALL:
        return False
    run = session.get(AutopilotRunRow, authority.run_id)
    if (run is None or run.project_id != project_id or run.claim != authority.claim
            or run.state not in {"running", "waiting"}
            or run.expected_closure != material_closure(session, project_id)
            or run.policy_hash != stable_hash(run.policy)):
        return False
    policy = LaunchPolicy.model_validate(run.policy)
    if not policy.early_reference_limit:
        return False
    if session.scalar(select(ProductionBridgeAdmissionRow.id).where(
        ProductionBridgeAdmissionRow.project_id == project_id,
    ).limit(1)) is not None:
        return False
    checkpoints = session.scalars(select(AutopilotCheckpointRow).where(
        AutopilotCheckpointRow.run_id == run.id,
    )).all()
    if any(item.operation_key == "installation" for item in checkpoints):
        return False
    checkpoint = next((item for item in checkpoints if item.evidence.get("jobId") == proposal.id), None)
    if checkpoint is None or checkpoint.state not in {"prepared", "sent", "outcome_unknown"}:
        return False
    evidence = CheckpointEvidence.model_validate(checkpoint.evidence)
    if evidence.owner != owner or evidence.request_hash != proposal.request_hash:
        return False
    raw_discovery = evidence.result.get("earlyReference")
    if not isinstance(raw_discovery, dict):
        return False
    discovery = EarlyReferenceDiscovery.model_validate(raw_discovery)
    if not any(item.operation_key == checkpoint.operation_key for item in discovery.subjects):
        return False
    assert_checkpoint_binding(session.connection().connection.driver_connection, project_id,
        checkpoint.state, evidence, run_id=run.id, operation_key=checkpoint.operation_key)
    snapshot = proposal.request["frozenSnapshot"]
    cast = ProjectCastPersistence(access)
    if owner == "character-reference":
        subject = cast.reference_subject_in_session(session, project_id, proposal.character_id,
            expected_cast_revision=discovery.cast_revision)
        if subject is None or subject["acceptedCast"]["contentHash"] != discovery.cast_hash:
            return False
        return snapshot.get("characterContextHash") == stable_hash(cast_reference_context_from_subject(subject))
    art = ProjectArtPersistence(access, cast)
    try:
        revision, subject = art.accepted_current_subject(session, project_id, proposal.subject_type, proposal.subject_id)
    except InvalidTransitionError:
        return False
    return (revision.revision == discovery.art_revision and revision.content_hash == discovery.art_hash
        and snapshot.get("acceptedArt") == {"revision": revision.revision, "contentHash": revision.content_hash}
        and snapshot.get("subject", {}).get("contentHash") == stable_hash(subject))
