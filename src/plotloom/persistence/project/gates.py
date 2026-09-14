from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER, AuthoringDraft, AuthoringDraftScope, DialogueTimingProfile,
    EntityRevision, GateEvaluation, GateEvidence, GateResult, InitialStage,
    LatestRunSummary, Project, ProjectBrief, ProjectCreation, ProjectDuplicateResult,
    ProjectLifecycleStatus, ProjectSummary, StageEnvelope, StageHead, StageName,
    StagePayload, StageStatus, downstream_stages, new_id, stage_payload_model,
    utc_now, upstream_stages, validate_initial_stage_prefix,
)
from ...exceptions import (
    IdempotencyConflictError, InvalidTransitionError, NotFoundError, ProjectBusyError,
    ProjectManagedAssetsPresentError, RevisionConflictError, SchemaResetRequiredError,
    StagePrerequisiteError,
)
from ...validation import STORYBOARD_GATE_SET_VERSION, validate_stage_payload
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ApprovalDecisionRow, AuthoringDraftRow, EntityRevisionRow, GateResultRow,
    GenerationRunRow, GenerationWorkUnitRow, ManagedAssetRow, MediaTaskRow,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectRow,
    StageHeadRow,
)
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from .access import ProjectPersistenceAccess

class ProjectGatePersistence:
    """Typed project persistence collaborator; the facade owns compatibility only."""

    def __init__(self, access: ProjectPersistenceAccess, catalog: Any) -> None:
        self._access = access
        self._catalog = catalog

    def list_stage_heads(self, project_id: str) -> list[StageHead]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(select(StageHeadRow).where(StageHeadRow.project_id == project_id)).all()
            by_stage = {StageName(row.stage): row for row in rows}
            return [self._access.codecs.stage_head(by_stage[stage]) for stage in STAGE_ORDER]

    def list_stage_envelopes(self, project_id: str) -> list[StageEnvelope]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            return self._catalog._stage_envelopes_in_session(session, project_id)

    def get_stage_head(self, project_id: str, stage: StageName) -> StageHead:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            return self._access.codecs.stage_head(self._access.rows.stage(session, project_id, stage))

    def get_entity_revision(self, revision_id: str) -> EntityRevision:
        with self._access.leases.read() as session:
            row = session.get(EntityRevisionRow, revision_id)
            if row is None:
                raise NotFoundError(f"entity revision not found: {revision_id}")
            return self._access.codecs.entity_revision(row)

    def record_gate_evaluation(
        self,
        project_id: str,
        entity_revision_id: str,
        evaluation: GateEvaluation,
    ) -> GateEvaluation:
        """Persist one immutable, versioned gate evaluation for a storyboard revision."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            revision = session.get(EntityRevisionRow, entity_revision_id)
            if revision is None or revision.project_id != project_id:
                raise NotFoundError(f"entity revision not found: {entity_revision_id}")
            head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if (
                head.status != StageStatus.READY.value
                or head.entity_revision_id != revision.id
                or head.revision != revision.revision
                or head.content_hash != revision.content_hash
            ):
                raise InvalidTransitionError(
                    "gate evaluation can only bind the current READY storyboard"
                )
            authoritative = self._evaluate_storyboard_revision_in_session(
                session,
                project,
                revision,
            )
            authoritative_semantics = authoritative.model_dump(
                mode="json", by_alias=False
            )
            supplied_semantics = evaluation.model_dump(mode="json", by_alias=False)
            for result in authoritative_semantics["results"]:
                result.pop("id", None)
            for result in supplied_semantics["results"]:
                result.pop("id", None)
            if supplied_semantics != authoritative_semantics:
                raise InvalidTransitionError(
                    "gate evaluation does not match the canonical evaluator receipt"
                )
            return self._record_gate_evaluation_in_session(
                session,
                project_id,
                revision,
                authoritative,
                now=utc_now(),
            )

    def _evaluate_storyboard_revision_in_session(
        self,
        session: Session,
        project: ProjectRow,
        storyboard_revision: EntityRevisionRow,
    ) -> GateEvaluation:
        """Rebuild the only accepted gate receipt from exact canonical inputs."""

        if storyboard_revision.stage != StageName.STORYBOARD.value:
            raise InvalidTransitionError(
                "gate evaluations can only bind storyboard revisions"
            )
        if storyboard_revision.schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(
                stage=StageName.STORYBOARD,
                schema_version=storyboard_revision.schema_version,
            )

        def exact_upstream(stage: StageName) -> StagePayload:
            revision_number = storyboard_revision.input_revisions.get(stage.value)
            if revision_number is None:
                raise InvalidTransitionError(
                    f"storyboard revision has no frozen {stage.value} input"
                )
            row = session.scalar(
                select(EntityRevisionRow).where(
                    EntityRevisionRow.project_id == project.id,
                    EntityRevisionRow.stage == stage.value,
                    EntityRevisionRow.revision == revision_number,
                )
            )
            if row is None:
                raise NotFoundError(
                    f"storyboard input revision not found: {stage.value}/{revision_number}"
                )
            return self._access.codecs.decode_current_stage_payload(
                stage, row.payload, row.schema_version
            )

        storyboard = self._access.codecs.decode_current_stage_payload(
            StageName.STORYBOARD,
            storyboard_revision.payload,
            storyboard_revision.schema_version,
        )
        bible = exact_upstream(StageName.STORY_BIBLE)
        scene_beats = exact_upstream(StageName.SCENE_BEATS)
        evaluation = validate_stage_payload(
            StageName.STORYBOARD,
            storyboard,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            brief=ProjectBrief.model_validate(project.brief),
            bible=bible,
            graph=None,
            scene_beats=scene_beats,
        )
        if evaluation is None:
            raise InvalidTransitionError(
                "canonical storyboard evaluator returned no gate receipt"
            )
        return evaluation

    def _record_gate_evaluation_in_session(
        self,
        session: Session,
        project_id: str,
        revision: EntityRevisionRow,
        evaluation: GateEvaluation,
        *,
        now: datetime,
    ) -> GateEvaluation:
        """Bind one deterministic receipt to an exact revision transactionally."""

        if revision.project_id != project_id:
            raise NotFoundError(f"entity revision not found: {revision.id}")
        if revision.stage != StageName.STORYBOARD.value:
            raise InvalidTransitionError("gate evaluations can only bind storyboard revisions")
        if revision.schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(
                stage=StageName.STORYBOARD, schema_version=revision.schema_version
            )
        if not evaluation.results:
            raise InvalidTransitionError("gate evaluation must contain at least one result")
        if any(
            result.gate_set_version != evaluation.gate_set_version
            or result.evaluated_input_hash != evaluation.evaluated_input_hash
            for result in evaluation.results
        ):
            raise InvalidTransitionError(
                "gate results must bind the evaluation's exact gate set and input hash"
            )

        existing = session.scalars(
            select(GateResultRow)
            .where(
                GateResultRow.entity_revision_id == revision.id,
                GateResultRow.gate_set_version == evaluation.gate_set_version,
            )
            .order_by(GateResultRow.sequence)
        ).all()
        if existing:
            persisted = GateEvaluation(
                gate_set_version=evaluation.gate_set_version,
                evaluated_input_hash=existing[0].evaluation_input_hash,
                results=tuple(self._access.codecs.gate_result(row) for row in existing),
            )
            persisted_semantics = [
                result.model_dump(mode="json", by_alias=False, exclude={"id"})
                for result in persisted.results
            ]
            requested_semantics = [
                result.model_dump(mode="json", by_alias=False, exclude={"id"})
                for result in evaluation.results
            ]
            if persisted_semantics != requested_semantics:
                raise InvalidTransitionError(
                    "gate evaluation is already recorded for this immutable revision"
                )
            return persisted

        persisted_results: list[GateResult] = []
        for sequence, result in enumerate(evaluation.results):
            identity = hashlib.sha256(
                f"{evaluation.gate_set_version}\0{result.gate_id}".encode("utf-8")
            ).hexdigest()
            persisted_result = result.model_copy(update={"id": f"{revision.id}:{identity}"})
            persisted_results.append(persisted_result)
            session.add(
                GateResultRow(
                    id=persisted_result.id,
                    project_id=project_id,
                    entity_revision_id=revision.id,
                    stage=revision.stage,
                    revision=revision.revision,
                    content_hash=revision.content_hash,
                    evaluation_input_hash=evaluation.evaluated_input_hash,
                    gate_set_version=evaluation.gate_set_version,
                    sequence=sequence,
                    gate_id=result.gate_id,
                    gate_version=result.gate_set_version,
                    required=result.required,
                    severity=result.severity.value,
                    status=result.status.value,
                    entity_path=list(result.entity_path),
                    evidence=[
                        item.model_dump(mode="json", by_alias=False)
                        for item in result.evidence
                    ],
                    reason=result.reason,
                    created_at=now,
                )
            )
        return GateEvaluation(
            gate_set_version=evaluation.gate_set_version,
            evaluated_input_hash=evaluation.evaluated_input_hash,
            results=tuple(persisted_results),
        )

    def get_gate_evaluation(
        self,
        entity_revision_id: str,
        gate_set_version: str,
    ) -> GateEvaluation:
        with self._access.leases.read() as session:
            revision = session.get(EntityRevisionRow, entity_revision_id)
            if revision is None:
                raise NotFoundError(f"entity revision not found: {entity_revision_id}")
            rows = session.scalars(
                select(GateResultRow)
                .where(
                    GateResultRow.entity_revision_id == entity_revision_id,
                    GateResultRow.gate_set_version == gate_set_version,
                )
                .order_by(GateResultRow.sequence)
            ).all()
            if not rows:
                raise NotFoundError(
                    f"gate evaluation not found: {entity_revision_id}/{gate_set_version}"
                )
            return GateEvaluation(
                gate_set_version=gate_set_version,
                evaluated_input_hash=rows[0].evaluation_input_hash,
                results=tuple(self._access.codecs.gate_result(row) for row in rows),
            )
