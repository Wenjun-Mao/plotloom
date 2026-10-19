"""Closed owner-granted QA scopes; project labels and API strings cannot enroll."""
from dataclasses import dataclass

from .delegated_qa_contracts import AgentQaAttribution
from .exceptions import InvalidTransitionError

REVIEWER_PREFIX = "@plotloom:agent-qa:"


@dataclass(frozen=True)
class QaMaterial:
    shot_id: str
    asset_id: str
    original_hash: str


@dataclass(frozen=True)
class DelegatedQaScope:
    id: str
    project_id: str
    storyboard_hash: str
    materials: tuple[QaMaterial, ...]
    profile_id: str
    max_submissions: int
    max_requested_seconds: int


# This immutable fixture grant is intentionally narrow. Extending it requires a
# new owner-authorized source decision, not a public enrollment endpoint.
SCOPES = (DelegatedQaScope(
    id="disposable-qa-20261019", project_id="326a5137-1851-4b5c-8ab2-b600ec7bda23",
    storyboard_hash="b4da9c96f5bfa09548446249960605e7a87671936d75e8fbec62ecef73043295",
    materials=(
        QaMaterial("SH01", "4c3cc979-1c8b-4ec0-8f4b-51b5b7162d1e", "663563c08200c9446c64a840a4d8bb3d0229da5c92ebb4bc799db2131209de7d"),
        QaMaterial("SH02", "3cd3e765-367d-4af5-926c-ca9b57425352", "95b940909d5de508d86216a190b0247efe08d6bf606f0ba6c51a0c4a58f26360"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2", max_submissions=2, max_requested_seconds=10,
),)


def project_scope(project_id):
    return next((scope for scope in SCOPES if scope.project_id == project_id), None)


def require_scope(project_id, attribution):
    parsed = AgentQaAttribution.model_validate(attribution)
    scope = project_scope(project_id)
    if scope is None or parsed.scope_id != scope.id:
        raise InvalidTransitionError("agent QA requires the exact owner-granted disposable project scope")
    return scope


def attribution_for_reviewer(project_id, reviewer):
    if not reviewer.startswith(REVIEWER_PREFIX):
        return None
    value = AgentQaAttribution(scope_id=reviewer.removeprefix(REVIEWER_PREFIX)).model_dump(mode="json", by_alias=True)
    require_scope(project_id, value)
    return value


def reject_reserved_reviewer(reviewer):
    if reviewer.strip().startswith(REVIEWER_PREFIX):
        raise InvalidTransitionError("reserved QA attribution requires a typed owner-granted decision")


def reviewer_for(attribution):
    return REVIEWER_PREFIX + attribution.scope_id


def direction_attribution(snapshot):
    """Observe an optional endorsement without making it dispatch authority."""
    package = snapshot.get("reviewedDirections")
    if package is None:
        return None
    if not isinstance(package, dict):
        raise TypeError("retained reviewed directions must be an object or absent")
    basis = package.get("reviewBasis")
    if basis is None:
        return None
    if not isinstance(basis, dict):
        raise TypeError("retained review basis must be an object or absent")
    actor = basis.get("attribution")
    if actor is not None and AgentQaAttribution.model_validate(actor).model_dump(mode="json", by_alias=True) != actor:
        raise ValueError("retained QA attribution must be canonical")
    return actor


def raw_connection(session):
    return session.connection().connection.driver_connection


def require_qa_write(session, project_id, attribution, *, board_hash=None, asset_id=None, shot_id=None):
    from .domain import StageName
    from .persistence.schema import EntityRevisionRow, ManagedAssetRow, StageHeadRow
    scope = require_scope(project_id, attribution)
    from .project_storage.delegated_qa_grants import require_command_context
    require_command_context(raw_connection(session), scope)
    head = session.query(StageHeadRow).filter_by(project_id=project_id, stage=StageName.STORYBOARD.value).one()
    revision = session.get(EntityRevisionRow, head.entity_revision_id)
    if revision.content_hash != scope.storyboard_hash or board_hash not in {None, scope.storyboard_hash}:
        raise InvalidTransitionError("QA authority does not cover a changed storyboard")
    if asset_id is not None:
        material = next((item for item in scope.materials if item.asset_id == asset_id and item.shot_id == shot_id), None)
        asset = session.get(ManagedAssetRow, asset_id)
        if material is None or asset is None or asset.project_id != project_id or asset.original_hash != material.original_hash:
            raise InvalidTransitionError("QA authority does not cover this material or shot")
    return scope


def binding_attribution(project_id, approval, intent, *, asset_id, shot_id):
    """Portable attribution validation; currentness remains the normal owner's job."""
    actor = attribution_for_reviewer(project_id, approval.reviewer)
    if actor != intent.get("attribution"):
        raise InvalidTransitionError("material decision and storyboard review attribution differ")
    if actor:
        scope = require_scope(project_id, actor)
        if approval.content_hash != scope.storyboard_hash or not any(
                item.asset_id == asset_id and item.shot_id == shot_id for item in scope.materials):
            raise InvalidTransitionError("QA binding exceeds its exact board and material scope")
    return actor
