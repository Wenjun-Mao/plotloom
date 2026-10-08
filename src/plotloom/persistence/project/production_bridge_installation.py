"""Installation authority, exact replacement targets and atomic bundle writes."""
from hashlib import sha256

from sqlalchemy import select

from ...canonical_schema import SceneBeatPlanV2, StoryBibleV2, StoryboardV2
from ...creative_handoff_exchange import canonical_json
from ...domain import StageName, StageStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError
from ...production_bridge_contracts import (
    CanonicalReplacementHead,
    InstalledProduction,
    ProductionBridgePrepareRequest,
    ProductionBridgeReplacementTarget,
)
from ..schema import (
    EntityRevisionRow,
    ProductionBridgeAdmissionRow,
    ProductionBridgeRevisionRow,
)

PRODUCTION_STAGES = (StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD)


class ProductionBridgeInstallation:
    @staticmethod
    def _latest_admission(session, project_id):
        return session.scalar(select(ProductionBridgeAdmissionRow).where(
            ProductionBridgeAdmissionRow.project_id == project_id,
        ).order_by(ProductionBridgeAdmissionRow.accepted_at.desc(), ProductionBridgeAdmissionRow.id.desc()).limit(1))

    def _replacement_target(self, session, project_id):
        admission = self._latest_admission(session, project_id)
        heads = {}
        for stage, field in zip(PRODUCTION_STAGES, ("bible", "graph", "scene_beats", "storyboard")):
            head = self._access.rows.stage(session, project_id, stage)
            heads[field] = CanonicalReplacementHead(
                revision=head.revision, entity_revision_id=head.entity_revision_id,
                content_hash=head.content_hash, status=head.status,
            )
        return ProductionBridgeReplacementTarget(installed_admission_id=admission.id if admission else None, **heads)

    def _prepare_request(self, session, project_id, inputs):
        head = self._head(session, project_id)
        row = session.scalar(select(ProductionBridgeRevisionRow).where(
            ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision,
        )) if head.revision else None
        return ProductionBridgePrepareRequest(
            expected_proposal_revision=head.revision,
            expected_proposal_content_hash=row.content_hash if row else None,
            expected_source_inputs_hash=sha256(canonical_json(inputs)).hexdigest(),
            replacement_target=self._replacement_target(session, project_id),
        )

    def installation_in_session(self, session, project_id):
        admission = self._latest_admission(session, project_id)
        if admission is None:
            return None
        row = session.scalar(select(ProductionBridgeRevisionRow).where(
            ProductionBridgeRevisionRow.project_id == project_id,
            ProductionBridgeRevisionRow.revision == admission.proposal_revision,
        ))
        stale = self._current(session, project_id, admission.inputs)
        if row is None or row.content_hash != admission.proposal_content_hash or row.inputs != admission.inputs:
            raise InvalidTransitionError("installed production proposal evidence is missing or inconsistent")
        if set(admission.installed_stage_revisions) != {stage.value for stage in PRODUCTION_STAGES}:
            raise InvalidTransitionError("installed production canonical identities are incomplete")
        for stage in PRODUCTION_STAGES:
            expected = admission.installed_stage_revisions[stage.value]
            installed = session.scalar(select(EntityRevisionRow).where(
                EntityRevisionRow.project_id == project_id, EntityRevisionRow.stage == stage.value,
                EntityRevisionRow.revision == expected,
            ))
            head = self._access.rows.stage(session, project_id, stage)
            if installed is None or head.status != StageStatus.READY.value or head.revision != expected or head.entity_revision_id != installed.id or head.content_hash != installed.content_hash:
                stale.append(f"installed {stage.value} canonical binding changed")
        return InstalledProduction(
            admission_id=admission.id, proposal_revision=admission.proposal_revision,
            proposal_content_hash=admission.proposal_content_hash,
            inputs=admission.inputs,
            installed_stage_revisions=admission.installed_stage_revisions,
            status="outdated" if stale else "current", stale_reasons=stale,
            cuts=row.proposal["cuts"], scenes=row.proposal["scenes"],
            runtime_choice=row.proposal["presentation"]["runtimeChoice"],
        )

    def _install_bundle(self, session, project, row):
        target = ProductionBridgeReplacementTarget.model_validate(row.proposal["replacementTarget"])
        if self._replacement_target(session, project.id) != target:
            raise InvalidTransitionError("production rebuild replacement target changed")
        payload, now = row.proposal["payload"], utc_now()
        bible = StoryBibleV2.model_validate(payload["bible"])
        self._source_graph.validate_graph_bible_in_session(session, project, bible)
        self._canonical._install_stage_in_session(
            session, project, StageName.STORY_BIBLE, bible,
            expected_revision=target.bible.revision, now=now, allow_noop=False,
        )
        self._source_graph.rebind_graph_bible_in_session(session, project, bible, now=now)
        for stage, model, field, expected in (
            (StageName.SCENE_BEATS, SceneBeatPlanV2, "sceneBeats", target.scene_beats.revision),
            (StageName.STORYBOARD, StoryboardV2, "storyboard", target.storyboard.revision),
        ):
            self._canonical._install_stage_in_session(
                session, project, stage, model.model_validate(payload[field]),
                expected_revision=expected, now=now, allow_noop=False,
            )
        revisions = {stage.value: self._access.rows.stage(session, project.id, stage).revision for stage in PRODUCTION_STAGES}
        session.add(ProductionBridgeAdmissionRow(
            id=new_id(), project_id=project.id, proposal_revision=row.revision,
            proposal_content_hash=row.content_hash, inputs=row.inputs,
            installed_stage_revisions=revisions, accepted_at=now,
        ))
        head = self._head(session, project.id)
        head.status, head.updated_at = "accepted", now
