"""Work-unit sealing and immutable producer-evidence rules."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    ArtifactKind, AttemptStatus, StageName, WorkUnitStatus,
)
from ...exceptions import InvalidTransitionError, NotFoundError
from ...provider_profiles import (
    TextProviderProfileSnapshot, TextProviderProfileSnapshotV3, is_v2_snapshot,
    is_v3_snapshot,
)
from ..codec import stable_hash
from ..schema import (
    ArtifactRow, GenerationAttemptRow, GenerationRunRow, GenerationWorkUnitRow,
    SealedStageAggregateRow,
)


class GenerationWorkUnitIntegrity:
    """Own the integrity rules shared by attempts, seals, and exact repair."""

    @staticmethod
    def is_sealed(session: Session, unit: GenerationWorkUnitRow) -> bool:
        return session.scalar(select(SealedStageAggregateRow.id).where(
            SealedStageAggregateRow.stage_plan_id == unit.stage_plan_id
        )) is not None

    def assert_unsealed(self, session: Session, unit: GenerationWorkUnitRow) -> None:
        if self.is_sealed(session, unit):
            raise InvalidTransitionError(
                "cannot change an attempt or artifact after its work-unit stage aggregate is sealed"
            )

    def attempt_unsealed(
        self, session: Session, attempt: GenerationAttemptRow
    ) -> GenerationWorkUnitRow | None:
        if attempt.work_unit_id is None:
            return None
        unit = session.get(GenerationWorkUnitRow, attempt.work_unit_id)
        if unit is None:
            raise NotFoundError(f"generation work unit not found: {attempt.work_unit_id}")
        self.assert_unsealed(session, unit)
        return unit

    @staticmethod
    def max_attempts(row: GenerationRunRow) -> int:
        if is_v2_snapshot(row.provider_snapshot) or is_v3_snapshot(row.provider_snapshot):
            profile = (
                TextProviderProfileSnapshotV3.model_validate(row.provider_snapshot)
                if is_v3_snapshot(row.provider_snapshot)
                else TextProviderProfileSnapshot.model_validate(row.provider_snapshot)
            )
            return 1 + profile.max_semantic_corrections
        return 1

    @staticmethod
    def fragment_from_artifact(stage: StageName, artifact: ArtifactRow) -> Any:
        from ...generation.fragments import (
            SceneBeatsFragment, StoryBibleFragment, StoryGraphFragment,
            StoryboardFragment,
        )

        return {
            StageName.STORY_BIBLE: StoryBibleFragment,
            StageName.STORY_GRAPH: StoryGraphFragment,
            StageName.SCENE_BEATS: SceneBeatsFragment,
            StageName.STORYBOARD: StoryboardFragment,
        }[stage].model_validate(artifact.content)

    @staticmethod
    def required_unit_evidence(
        session: Session,
        *,
        run_id: str,
        stage: StageName,
        unit: GenerationWorkUnitRow,
        candidate_id: str,
    ) -> tuple[ArtifactRow, GenerationAttemptRow, list[ArtifactRow]]:
        candidate = session.get(ArtifactRow, candidate_id)
        if candidate is None:
            raise NotFoundError(f"candidate artifact not found: {candidate_id}")
        if (
            candidate.run_id != run_id or candidate.stage != stage.value
            or candidate.kind != ArtifactKind.CANDIDATE.value
            or candidate.work_unit_id != unit.id or candidate.attempt_id is None
        ):
            raise InvalidTransitionError("candidate artifact does not belong to the declared run/stage/work unit")
        if candidate.content_hash != stable_hash(candidate.content):
            raise InvalidTransitionError("candidate artifact content hash does not match immutable content")
        attempt = session.get(GenerationAttemptRow, candidate.attempt_id)
        if (
            attempt is None or attempt.run_id != run_id or attempt.stage != stage.value
            or attempt.work_unit_id != unit.id
            or AttemptStatus(attempt.status) != AttemptStatus.SUCCEEDED
            or attempt.outcome_unknown
        ):
            raise InvalidTransitionError(
                "candidate artifact must be produced by a succeeded, known-outcome work-unit attempt"
            )
        evidence = session.scalars(select(ArtifactRow).where(
            ArtifactRow.attempt_id == attempt.id
        ).order_by(ArtifactRow.created_at, ArtifactRow.id)).all()
        required = {
            ArtifactKind.PROMPT.value, ArtifactKind.RESPONSE.value,
            ArtifactKind.VALIDATION.value, ArtifactKind.CANDIDATE.value,
        }
        by_kind: dict[str, list[ArtifactRow]] = {}
        for row in evidence:
            by_kind.setdefault(row.kind, []).append(row)
        if set(by_kind) != required or any(len(rows) != 1 for rows in by_kind.values()):
            raise InvalidTransitionError(
                "sealed work-unit producer attempts require exactly one prompt, response, validation, and candidate artifact"
            )
        if by_kind[ArtifactKind.CANDIDATE.value][0].id != candidate.id:
            raise InvalidTransitionError("candidate artifact must be the producer attempt's unique candidate")
        if attempt.response_persisted_at is None:
            raise InvalidTransitionError("sealed candidates require a durable provider response marker")
        if any(
            row.run_id != run_id or row.stage != stage.value or row.work_unit_id != unit.id
            or row.content_hash != stable_hash(row.content) for row in evidence
        ):
            raise InvalidTransitionError("attempt evidence fails run/stage/work-unit ownership or content-hash checks")
        validation = by_kind[ArtifactKind.VALIDATION.value][0]
        if not isinstance(validation.content, dict) or validation.content.get("accepted") is not True:
            raise InvalidTransitionError(
                "sealed work-unit candidates require an object validation artifact with accepted: true"
            )
        return candidate, attempt, evidence
