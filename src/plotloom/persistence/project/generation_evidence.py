"""Legacy-compatible attempt, artifact, and compact trace persistence."""

from __future__ import annotations

from copy import deepcopy

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from plotloom.artifact_contracts import Artifact, ArtifactKind
from plotloom.run_contracts import AttemptStatus, GenerationAttempt, GenerationAttemptKind, RunStatus, WorkUnitFailureDisposition, WorkUnitStatus
from plotloom.stage_contracts import CanonicalSnapshot, StageName
from plotloom.run_evidence_contracts import RunTrace
from plotloom.public_values import contains_secret_setting, contains_secret_value, is_secret_setting_name
from plotloom.contract_identity import utc_now
from ...exceptions import InvalidTransitionError, NotFoundError
from ...generation.continuity_repair_contracts import (
    ContinuityFactAssignment,
    ContinuitySequenceRepairFact,
)
from ...generation.contracts import ValidationIssue
from ...generation.repair_facts import (
    parse_semantic_repair_fact,
    serialize_semantic_repair_fact,
)
from ...generation.work_unit_contracts import WorkUnitPromptContract
from ..codec import _contains_unredacted_secret_setting, _json_data
from ..schema import (
    ArtifactRow,
    GenerationAttemptRow,
    GenerationRunRow,
    GenerationWorkUnitRow,
)
from .generation_access import GenerationPersistenceAccess
from .generation_integrity import GenerationWorkUnitIntegrity
from .generation_snapshots import ProjectGenerationSnapshots


class ProjectGenerationEvidencePersistence:
    """Legacy-compatible attempt, artifact, and compact trace persistence."""

    def __init__(self, access: GenerationPersistenceAccess, integrity: GenerationWorkUnitIntegrity, snapshots: ProjectGenerationSnapshots) -> None:
        self._access = access
        self._integrity = integrity
        self._snapshots = snapshots

    def create_attempt(
        self,
        run_id: str,
        stage: StageName,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> GenerationAttempt:
        access = self._access
        with access.leases.write() as session:
            run = access.rows.run(session, run_id)
            if RunStatus(run.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot create generation attempt while run is {run.status}"
                )
            prior_count = len(
                session.scalars(
                    select(GenerationAttemptRow).where(
                        GenerationAttemptRow.run_id == run_id,
                        GenerationAttemptRow.stage == stage.value,
                    )
                ).all()
            )
            attempt = GenerationAttempt(
                run_id=run_id,
                stage=stage,
                attempt_number=prior_count + 1,
                status=AttemptStatus.RUNNING,
                provider=provider,
                model=model,
            )
            session.add(
                GenerationAttemptRow(
                    id=attempt.id,
                    run_id=run_id,
                    stage=stage.value,
                    attempt_number=attempt.attempt_number,
                    attempt_kind=GenerationAttemptKind.PRIMARY.value,
                    source_attempt_id=None,
                    status=attempt.status.value,
                    provider=provider,
                    model=model,
                    error=None,
                    outcome_code=None,
                    started_at=attempt.started_at,
                    finished_at=None,
                )
            )
            return attempt
    def finish_attempt(
        self,
        attempt_id: str,
        status: AttemptStatus,
        *,
        error: str | None = None,
        outcome_code: str | None = None,
        allow_correction: bool = False,
        failure_disposition: WorkUnitFailureDisposition | None = None,
    ) -> GenerationAttempt:
        access = self._access
        if status == AttemptStatus.RUNNING:
            raise InvalidTransitionError("finish_attempt requires a terminal attempt status")
        with access.leases.write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            unit = self._integrity.attempt_unsealed(session, row)
            if AttemptStatus(row.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish attempt from {row.status}")
            row.status = status.value
            row.error = error
            row.outcome_code = outcome_code
            row.finished_at = utc_now()
            if failure_disposition is not None and status != AttemptStatus.FAILED:
                raise InvalidTransitionError(
                    "only a failed attempt may declare a work-unit failure disposition"
                )
            if unit is not None:
                if status == AttemptStatus.SUCCEEDED:
                    unit.status = WorkUnitStatus.SUCCEEDED.value
                elif status == AttemptStatus.CANCELLED:
                    unit.status = WorkUnitStatus.CANCELLED.value
                elif allow_correction and not row.outcome_unknown:
                    if row.response_persisted_at is None or not outcome_code:
                        raise InvalidTransitionError(
                            "only a durably recorded rejected response may authorize correction"
                        )
                    unit.status = WorkUnitStatus.QUEUED.value
                elif not row.outcome_unknown:
                    if failure_disposition is None:
                        raise InvalidTransitionError(
                            "known work-unit failures require an explicit failed or quarantined disposition"
                        )
                    unit.status = WorkUnitStatus(failure_disposition.value).value
            return access.codecs.attempt(row)
    def add_artifact(self, artifact: Artifact) -> Artifact:
        access = self._access
        self._assert_secret_free_artifact_content(artifact.content, artifact=artifact)
        with access.leases.write() as session:
            access.rows.run(session, artifact.run_id)
            attempt: GenerationAttemptRow | None = None
            if artifact.attempt_id is not None:
                attempt = session.get(GenerationAttemptRow, artifact.attempt_id)
                if attempt is None:
                    raise NotFoundError(f"generation attempt not found: {artifact.attempt_id}")
                if attempt.run_id != artifact.run_id:
                    raise InvalidTransitionError("artifact attempt must belong to its declared run")
                if artifact.stage is not None and attempt.stage != artifact.stage.value:
                    raise InvalidTransitionError("artifact stage must match its declared attempt")
                if artifact.work_unit_id is not None and attempt.work_unit_id != artifact.work_unit_id:
                    raise InvalidTransitionError("artifact work unit must match its declared attempt")
                if attempt.work_unit_id is not None and artifact.work_unit_id is None:
                    raise InvalidTransitionError("work-unit attempt artifacts must retain their workUnitId")
            if artifact.work_unit_id is not None:
                unit = session.get(GenerationWorkUnitRow, artifact.work_unit_id)
                if unit is None:
                    raise NotFoundError(f"generation work unit not found: {artifact.work_unit_id}")
                if unit.run_id != artifact.run_id:
                    raise InvalidTransitionError("artifact work unit must belong to its declared run")
                if artifact.stage is None or unit.stage != artifact.stage.value:
                    raise InvalidTransitionError("artifact work unit must match its declared stage")
                self._integrity.assert_unsealed(session, unit)
                if artifact.kind == ArtifactKind.RESPONSE:
                    raise InvalidTransitionError(
                        "work-unit responses must be persisted through persist_attempt_response"
                    )
                if attempt is None:
                    raise InvalidTransitionError("work-unit artifacts require a producer attempt")
                existing = session.scalar(
                    select(ArtifactRow).where(
                        ArtifactRow.attempt_id == attempt.id,
                        ArtifactRow.kind == artifact.kind.value,
                    )
                )
                if existing is not None:
                    if (
                        existing.run_id == artifact.run_id
                        and existing.work_unit_id == artifact.work_unit_id
                        and existing.stage == (artifact.stage.value if artifact.stage else None)
                        and existing.content_hash == artifact.content_hash
                    ):
                        return access.codecs.artifact(existing)
                    raise InvalidTransitionError(
                        f"work-unit producer attempt already has immutable {artifact.kind.value} evidence"
                    )
            if artifact.source_artifact_id is not None:
                source = session.get(ArtifactRow, artifact.source_artifact_id)
                if source is None:
                    raise NotFoundError(
                        f"source artifact not found: {artifact.source_artifact_id}"
                    )
            session.add(
                ArtifactRow(
                    id=artifact.id,
                    run_id=artifact.run_id,
                    attempt_id=artifact.attempt_id,
                    work_unit_id=artifact.work_unit_id,
                    source_artifact_id=artifact.source_artifact_id,
                    stage=artifact.stage.value if artifact.stage else None,
                    kind=artifact.kind.value,
                    media_type=artifact.media_type,
                    content=_json_data(artifact.content),
                    content_hash=artifact.content_hash,
                    created_at=artifact.created_at,
                )
            )
        return artifact
    def get_artifact(self, artifact_id: str) -> Artifact:
        access = self._access
        with access.leases.read() as session:
            row = session.get(ArtifactRow, artifact_id)
            if row is None:
                raise NotFoundError(f"artifact not found: {artifact_id}")
            return access.codecs.artifact(row)
    def get_run_trace(self, run_id: str) -> RunTrace:
        access = self._access
        with access.leases.read() as session:
            run = access.codecs.run(access.rows.run(session, run_id))
            attempts = [
                access.codecs.attempt(row)
                for row in session.scalars(
                    select(GenerationAttemptRow)
                    .where(GenerationAttemptRow.run_id == run_id)
                    .order_by(GenerationAttemptRow.started_at, GenerationAttemptRow.attempt_number)
                ).all()
            ]
            artifacts = [
                access.codecs.artifact(row)
                for row in session.scalars(
                    select(ArtifactRow).where(ArtifactRow.run_id == run_id).order_by(ArtifactRow.created_at)
                ).all()
            ]
            if run.result_revision_ids:
                snapshot_is_current = self._run_outputs_are_current(session, access.rows.run(session, run_id))
            else:
                current = self._snapshots.snapshot_in_session(session, run.project_id)
                snapshot_is_current = current.snapshot_hash == run.canonical_snapshot.snapshot_hash
            return RunTrace(
                run=run,
                attempts=attempts,
                artifacts=artifacts,
                snapshot_is_current=snapshot_is_current,
            )

    @staticmethod
    def _assert_secret_free_artifact_content(content: object, *, artifact: Artifact | None = None) -> None:
        # Credential-shaped values are always screened in the original evidence.
        # Only a validated structural field in rejected continuity evidence can
        # be omitted from the separate setting-name scan; persisted bytes stay exact.
        if contains_secret_value(content):
            raise InvalidTransitionError("artifact evidence must not contain secret-shaped values")
        projection = (
            _continuity_secret_scan_projection(artifact)
            if artifact is not None and artifact.content is content
            else content
        )
        if contains_secret_setting(projection) and _contains_unredacted_secret_setting(projection):
            raise InvalidTransitionError("artifact evidence must not contain secret-shaped values")

    def _run_outputs_are_current(self, session: Session, run_row: GenerationRunRow) -> bool:
        snapshot = CanonicalSnapshot.model_validate(run_row.canonical_snapshot)
        project = self._access.rows.project(session, run_row.project_id)
        if project.revision != snapshot.project_revision:
            return False
        requested = {StageName(value) for value in run_row.requested_stages}
        from ..schema import EntityRevisionRow
        result_rows = session.scalars(select(EntityRevisionRow).where(
            EntityRevisionRow.id.in_(run_row.result_revision_ids or [""])
        )).all()
        by_stage = {StageName(item.stage): item for item in result_rows}
        if set(by_stage) != requested:
            return False
        from plotloom.stage_contracts import upstream_stages
        for stage in requested:
            if self._access.rows.stage(session, run_row.project_id, stage).entity_revision_id != by_stage[stage].id:
                return False
        return all(
            self._access.rows.stage(session, run_row.project_id, stage).revision == snapshot.stage_heads[stage].revision
            for requested_stage in requested for stage in upstream_stages(requested_stage)
            if stage not in requested
        )


def _continuity_secret_scan_projection(artifact: Artifact) -> object:
    """Recognize only typed fact-name slots in rejected work-unit validation.

    This is a nonmutating scan projection, never a persistence transformation or
    source-authority grant. Malformed, noncanonical or misplaced evidence keeps
    the original generic rejection. Source revalidation remains the runner's job.
    """
    content = artifact.content
    if (
        artifact.kind != ArtifactKind.VALIDATION
        or artifact.stage not in {StageName.SCENE_BEATS, StageName.STORYBOARD}
        or artifact.attempt_id is None
        or artifact.work_unit_id is None
        or not isinstance(content, dict)
        or content.get("accepted") is not False
        or not isinstance(content.get("repairFacts"), list)
        or not isinstance(content.get("issues"), list)
    ):
        return content
    try:
        contract = WorkUnitPromptContract.model_validate(content.get("contract"))
        if contract.stage != artifact.stage or contract.work_unit_id != artifact.work_unit_id:
            return content
        if any(not isinstance(item, dict) for item in content["repairFacts"]):
            raise InvalidTransitionError("artifact evidence requires canonical typed repair facts")
        issues = tuple(ValidationIssue.model_validate(item) for item in content["issues"])
        facts = tuple(parse_semantic_repair_fact(item) for item in content["repairFacts"])
        if any(serialize_semantic_repair_fact(fact) != raw for fact, raw in zip(facts, content["repairFacts"], strict=True)):
            return content
    except (ValidationError, TypeError, ValueError):
        return content
    projection = deepcopy(content)
    for fact_index, fact in enumerate(facts):
        if type(fact) is not ContinuitySequenceRepairFact:
            continue
        expected_code = (
            "semantic.continuity_beat_sequence_mismatch"
            if artifact.stage == StageName.SCENE_BEATS
            else "semantic.continuity_shot_sequence_mismatch"
        )
        if fact.code != expected_code or not any(issue.code == fact.code and issue.path == fact.path for issue in issues):
            return content
        for boundary_index, boundary in enumerate(fact.boundaries):
            for assignment_index, assignment in enumerate(boundary.assignments):
                if type(assignment) is ContinuityFactAssignment:
                    if is_secret_setting_name(assignment.key):
                        return content
                    del projection["repairFacts"][fact_index]["boundaries"][boundary_index]["assignments"][assignment_index]["key"]
    return projection
