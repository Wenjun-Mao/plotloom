"""F5 review evidence to one explicitly accepted canonical V2 installation."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from ...canonical_schema import (
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryboardV2,
    default_dialogue_timing_profile,
)
from ...creative_handoff_exchange import canonical_json
from ...domain import ProjectBrief, StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...production_bridge_contracts import (
    BridgePrepareAvailable,
    BridgePrepareUnavailable,
    ProductionBridgeAcceptRequest,
    ProductionBridgeConflict,
    ProductionBridgeIntentJob,
    ProductionBridgeIntentPackage,
    ProductionBridgeIntentUpdateRequest,
    ProductionBridgePrepareRequest,
    ProductionBridgeProposal,
    ProductionBridgeState,
)
from ...production_presentation import ProductionPresentation, prepare_presentation
from ...storyboard_review_contracts import StoryboardReviewBinding
from ...validation import DomainValidationError, validate_stage_payload
from ..schema.project_production_bridge import (
    ProductionBridgeHeadRow,
    ProductionBridgeIntentJobRow,
    ProductionBridgeRevisionRow,
)
from ..schema.project_storyboard_review import StoryboardReviewRevisionRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .production_bridge_installation import ProductionBridgeInstallation
from .production_bridge_presentation import ProductionBridgePresentationPersistence
from .production_bridge_projection import ProductionBridgeProjection
from .production_rebuild_quiescence import assert_production_quiescent
from .storyboard_review import ProjectStoryboardReviewPersistence


class ProductionBridgePersistence(ProductionBridgeProjection, ProductionBridgePresentationPersistence, ProductionBridgeInstallation):
    """Own F5-to-V2 projection and explicit, source-bound review admission."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence, review: ProjectStoryboardReviewPersistence, source_graph) -> None:
        self._access, self._canonical, self._review = access, canonical, review
        self._source_graph = source_graph

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(ProductionBridgeHeadRow, project_id) is None:
            session.add(ProductionBridgeHeadRow(project_id=project_id, revision=0, status="missing", updated_at=created_at))

    @staticmethod
    def _head(session: Any, project_id: str) -> ProductionBridgeHeadRow:
        row = session.get(ProductionBridgeHeadRow, project_id)
        if row is None:
            raise InvalidTransitionError("production bridge state is unavailable")
        return row

    def _context(self, session: Any, project_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        project = self._access.rows.project(session, project_id)
        review_head = self._review._head(session, project_id)
        accepted = session.scalar(select(StoryboardReviewRevisionRow).where(
            StoryboardReviewRevisionRow.project_id == project_id,
            StoryboardReviewRevisionRow.revision == review_head.revision,
        )) if review_head.revision else None
        if review_head.status != "accepted" or accepted is None:
            raise InvalidTransitionError("a current accepted F5 storyboard review is required")
        binding = StoryboardReviewBinding.model_validate(accepted.binding)
        if self._review._stale(session, project_id, binding):
            raise InvalidTransitionError("the accepted F5 storyboard review is stale")
        current, script, _outline, cast, art = self._review._context(
            session, project_id, max_cut_seconds=binding.review_max_cut_seconds,
        )
        if current != binding:
            raise InvalidTransitionError("the accepted F5 storyboard review binding differs from current source")
        _, _, _, mapping, _, _ = self._review._script._context(session, project_id)
        inputs = {
            "reviewRevision": accepted.revision, "reviewContentHash": accepted.content_hash,
            "scriptRevision": binding.script_revision, "scriptContentHash": binding.script_content_hash,
            "graphRevision": binding.graph_revision, "graphContentHash": binding.graph_content_hash,
            "castRevision": binding.cast_revision, "castContentHash": binding.cast_content_hash,
            "artRevision": binding.art_revision, "artContentHash": binding.art_content_hash,
            "sectionMapRevision": binding.section_map_revision, "sectionMapContentHash": binding.section_map_content_hash,
            "briefRevision": project.revision,
            "briefContentHash": sha256(canonical_json(project.brief)).hexdigest(),
        }
        return inputs, accepted.storyboard, script, cast | {"__art__": art, "__section_map__": mapping}

    def _validate_payload(self, session: Any, project_id: str, payload: dict[str, Any]) -> list[ProductionBridgeConflict]:
        """Run the same V2 models and gates used by canonical installation early."""

        try:
            project = self._access.rows.project(session, project_id)
            brief = ProjectBrief.model_validate(project.brief)
            bible = StoryBibleV2.model_validate(payload["bible"])
            self._source_graph.validate_graph_bible_in_session(session, project, bible)
            beats = SceneBeatPlanV2.model_validate(payload["sceneBeats"])
            board = StoryboardV2.model_validate(payload["storyboard"])
            graph = self._canonical._load_stage_payload(session, project_id, StageName.STORY_GRAPH)
            validate_stage_payload(StageName.SCENE_BEATS, beats, schema_version=2, brief=brief, bible=bible, graph=graph, dialogue_timing_profile=default_dialogue_timing_profile())
            validate_stage_payload(StageName.STORYBOARD, board, schema_version=2, brief=brief, bible=bible, scene_beats=beats, dialogue_timing_profile=default_dialogue_timing_profile())
            return []
        except (ValidationError, DomainValidationError, InvalidTransitionError, TypeError, ValueError) as error:
            return [ProductionBridgeConflict(code="canonical_validation", message=f"不能安装：规范提案验证失败：{error}")]

    @staticmethod
    def _proposal_digest(inputs: dict[str, Any], proposal: dict[str, Any], conflicts: list[ProductionBridgeConflict]) -> str:
        return sha256(canonical_json({"inputs": inputs, "proposal": proposal, "conflicts": [item.model_dump(mode="json") for item in conflicts]})).hexdigest()

    def _intent_package(self, session: Any, row: ProductionBridgeRevisionRow) -> ProductionBridgeIntentPackage:
        """Read exactly the current intent package; never reconstruct old evidence."""
        return ProductionBridgeIntentPackage.model_validate(row.proposal["intentPackage"])

    def _apply_intent_package(self, payload: dict[str, Any], package: ProductionBridgeIntentPackage) -> dict[str, Any]:
        """Bind editable intent text to exactly the declared canonical targets."""

        patched = {"bible": payload["bible"], "sceneBeats": {key: [dict(item) for item in value] for key, value in payload["sceneBeats"].items()}, "storyboard": payload["storyboard"]}
        scenes = {item["id"]: item for item in patched["sceneBeats"]["scenes"]}
        beats = {item["id"]: item for item in patched["sceneBeats"]["beats"]}
        for entry in package.entries:
            if entry.target_kind == "scene_objective" and entry.target_id in scenes:
                scenes[entry.target_id]["objective"] = entry.text
            elif entry.target_kind == "beat_purpose" and entry.target_id in beats:
                beats[entry.target_id]["purpose"] = entry.text
            else:
                raise InvalidTransitionError("production bridge intent package has an unknown canonical target")
        return patched

    def _current(self, session: Any, project_id: str, inputs: dict[str, Any]) -> list[str]:
        try: current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error: return [str(error)]
        return [f"{key} changed" for key, value in inputs.items() if current.get(key) != value]

    def get_state(self, project_id: str) -> ProductionBridgeState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision)) if head.revision else None
            # Successful installation necessarily advances the frozen target.
            # Only a pending proposal is still authorized against that target.
            stale = (self._current(session, project_id, row.inputs) if head.status == "accepted"
                     else self._proposal_stale(session, project_id, row)) if row else []
            proposal = ProductionBridgeProposal(revision=row.revision, content_hash=row.content_hash, inputs=row.inputs, replacement_target=row.proposal["replacementTarget"], intent_package=self._intent_package(session, row), presentation=ProductionPresentation.model_validate(row.proposal["presentation"]), scenes=row.proposal["scenes"], cuts=row.proposal["cuts"], conflicts=[ProductionBridgeConflict.model_validate(item) for item in row.conflicts], advisories=[ProductionBridgeConflict.model_validate(item) for item in row.proposal["advisories"]], installable=row.installable, prepared_at=row.prepared_at) if row else None
            installation = self.installation_in_session(session, project_id)
            try:
                inputs, *_ = self._context(session, project_id)
                assert_production_quiescent(self._access, session, project_id)
                preparation = BridgePrepareAvailable(request=self._prepare_request(session, project_id, inputs))
            except InvalidTransitionError as error:
                preparation = BridgePrepareUnavailable(reason=str(error))
            job = session.scalar(select(ProductionBridgeIntentJobRow).where(ProductionBridgeIntentJobRow.project_id == project_id).order_by(ProductionBridgeIntentJobRow.created_at.desc(), ProductionBridgeIntentJobRow.id.desc()).limit(1))
            job_view = ProductionBridgeIntentJob(id=job.id, status=job.status, proposal_revision=job.proposal_revision, proposal_content_hash=job.proposal_content_hash, profile_id=job.profile_snapshot["profileId"], profile_version=job.profile_snapshot["profileVersion"], prompt_version=job.prompt_trace["prompt_version"], created_at=job.created_at, updated_at=job.updated_at, error_code=job.error_code, error_message=job.error_message, result_proposal_revision=job.result_proposal_revision, provider_request_id=job.provider_request_id, response_hash=job.response_hash) if job else None
            return ProductionBridgeState(proposal=proposal, status="stale" if stale else head.status, stale_reasons=stale, installation=installation, preparation=preparation, intent_job=job_view)

    def prepare(self, project_id: str, request: ProductionBridgePrepareRequest) -> ProductionBridgeState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            assert_production_quiescent(self._access, session, project_id)
            inputs, storyboard, script, cast_art = self._context(session, project_id)
            if request != self._prepare_request(session, project_id, inputs):
                raise InvalidTransitionError("production bridge preparation target changed")
            payload, intent_package, conflicts, advisories, scenes, cuts = self._build(session, project_id, inputs=inputs, storyboard=storyboard, script=script, cast_and_art=cast_art)
            presentation = prepare_presentation(inputs=inputs, script=script, storyboard=storyboard, mapping=cast_art["__section_map__"])
            conflicts.append(ProductionBridgeConflict(code="presentation_required", message="不能安装：请完整审阅实体动作、可见文字与运行时选择的呈现归属"))
            conflicts.append(ProductionBridgeConflict(code="dramatic_intent_required", message="不能安装：请先生成并审阅戏剧意图，或逐项填写并保存作者意图"))
            # The prepared payload intentionally has blank semantic fields.
            # Validate the complete canonical contract only after one whole
            # inferred or author-written package has been bound.
            proposal = {"replacementTarget": request.replacement_target.model_dump(mode="json", by_alias=True), "presentation": presentation.model_dump(mode="json", by_alias=True), "payload": payload, "intentPackage": intent_package.model_dump(mode="json", by_alias=True), "scenes": scenes, "cuts": cuts, "advisories": [item.model_dump(mode="json") for item in advisories]}; digest = self._proposal_digest(inputs, proposal, conflicts); now = utc_now()
            head.revision += 1; head.status, head.updated_at = "ready", now
            session.add(ProductionBridgeRevisionRow(id=new_id(), project_id=project_id, revision=head.revision, content_hash=digest, inputs=inputs, proposal=proposal, conflicts=[item.model_dump(mode="json") for item in conflicts], installable=not conflicts, prepared_at=now))
        return self.get_state(project_id)

    def update_intent_package(self, project_id: str, request: ProductionBridgeIntentUpdateRequest) -> ProductionBridgeState:
        """Create one new review binding; client text cannot alter provenance."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if head.status == "accepted":
                raise InvalidTransitionError("accepted production bridge evidence cannot be edited; prepare a new current proposal")
            if head.revision != request.expected_proposal_revision:
                raise RevisionConflictError("production bridge", request.expected_proposal_revision, head.revision)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision))
            if row is None or row.content_hash != request.expected_content_hash:
                raise InvalidTransitionError("production bridge proposal changed before its intent package was saved")
            if self._proposal_stale(session, project_id, row):
                raise InvalidTransitionError("production bridge proposal is stale")
            package = self._intent_package(session, row)
            updates = {item.id: item.text for item in request.entries}
            known = {item.id for item in package.entries}
            if len(updates) != len(request.entries) or set(updates) != known:
                raise InvalidTransitionError("production bridge intent package must update every exact package entry once")
            if any(not value.strip() for value in updates.values()):
                raise InvalidTransitionError("every production bridge intent value must be nonblank")
            updated = ProductionBridgeIntentPackage(
                suggestion_origin=package.suggestion_origin, review_state="author_saved",
                entries=[entry.model_copy(update={"text": updates[entry.id]}) for entry in package.entries],
                provenance=package.provenance,
            )
            payload = self._apply_intent_package(row.proposal["payload"], updated)
            conflicts = [ProductionBridgeConflict.model_validate(item) for item in row.conflicts if item.get("code") not in {"canonical_validation", "dramatic_intent_required"}]
            conflicts.extend(self._validate_payload(session, project_id, payload))
            proposal = {**row.proposal, "payload": payload, "intentPackage": updated.model_dump(mode="json", by_alias=True)}
            digest, now = self._proposal_digest(row.inputs, proposal, conflicts), utc_now()
            head.revision += 1; head.status, head.updated_at = "ready", now
            session.add(ProductionBridgeRevisionRow(id=new_id(), project_id=project_id, revision=head.revision, content_hash=digest, inputs=row.inputs, proposal=proposal, conflicts=[item.model_dump(mode="json") for item in conflicts], installable=not conflicts, prepared_at=now))
        return self.get_state(project_id)

    def accept(self, project_id: str, request: ProductionBridgeAcceptRequest) -> ProductionBridgeState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id); self._access.guards.active(project); head = self._head(session, project_id)
            assert_production_quiescent(self._access, session, project_id)
            if head.revision != request.expected_proposal_revision: raise RevisionConflictError("production bridge", request.expected_proposal_revision, head.revision)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision))
            if row is None or row.content_hash != request.expected_content_hash or not row.installable: raise InvalidTransitionError("production bridge proposal is not installable")
            if not ProductionPresentation.model_validate(row.proposal["presentation"]).reviewed:
                raise InvalidTransitionError("production bridge requires complete reviewed presentation")
            package = self._intent_package(session, row)
            if package.review_state == "pending" or any(not entry.text.strip() for entry in package.entries):
                raise InvalidTransitionError("production bridge requires a complete reviewed dramatic-intent package")
            if self._current(session, project_id, row.inputs): raise InvalidTransitionError("production bridge proposal is stale")
            self._install_bundle(session, project, row)
        return self.get_state(project_id)
