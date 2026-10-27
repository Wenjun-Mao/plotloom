"""F5A owner for upstream storyboard review revisions, not production shots."""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ...accepted_review_state import accepted_review_state
from ...authored_route_timing import validate_route_seconds
from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery
from ...creative_handoff_identity import canonical_json
from plotloom.public_values import contains_secret_setting, contains_secret_value
from plotloom.contract_identity import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...production_dialogue_timing import (
    TIMING_FILENAME,
    assert_f5_dialogue_capacity,
    freeze_f5_dialogue_timing,
)
from ...review_binding_diagnostics import review_binding_diagnostics
from ...review_context_diagnostics import ReviewContextDiagnostic, ReviewContextError
from ...script_contracts import AcceptedScriptRevision, ScriptBinding
from ...storyboard_review_contracts import DEFAULT_STORYBOARD_MAX_CUT_SECONDS
from ...storyboard_brief_style import (
    ADAPTER as BRIEF_ADAPTER,
)
from ...storyboard_brief_style import (
    CONTRACT_FILENAME,
    freeze_storyboard_brief_style,
    storyboard_brief_instructions,
    validate_storyboard_brief_authority,
)
from ...storyboard_review_contracts import (
    AcceptedStoryboardReviewRevision,
    StoryboardReviewAcceptRequest,
    StoryboardReviewBinding,
    StoryboardReviewCandidate,
    StoryboardReviewState,
)
from ..schema.project_script import ScriptRevisionRow
from ..schema.project_storyboard_review import (
    StoryboardReviewCandidateRow,
    StoryboardReviewHeadRow,
    StoryboardReviewRevisionRow,
)
from .access import ProjectPersistenceAccess
from .autopilot_authority import receipt_only
from .creative_execution_pins import freeze_execution_pin
from .script import ProjectScriptPersistence, _upstream_script_outline

StoryboardReviewContext = tuple[
    StoryboardReviewBinding, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
]


@dataclass(frozen=True)
class _ResolvedStoryboardContext:
    context: StoryboardReviewContext
    section_map: dict[str, Any]


class ProjectStoryboardReviewPersistence:
    """Retains raw `novel-storyboard` review data with F4 as its only creative seam."""

    def __init__(self, access: ProjectPersistenceAccess, script: ProjectScriptPersistence) -> None:
        self._access, self._script = access, script

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(StoryboardReviewHeadRow, project_id) is None:
            session.add(StoryboardReviewHeadRow(project_id=project_id, revision=0, candidate_job_id=None, status="missing", updated_at=created_at))

    @staticmethod
    def _head(session: Any, project_id: str) -> StoryboardReviewHeadRow:
        row = session.get(StoryboardReviewHeadRow, project_id)
        if row is None:
            raise NotFoundError("project storyboard review state is missing")
        return row

    @staticmethod
    def _candidate(row: StoryboardReviewCandidateRow) -> StoryboardReviewCandidate:
        return StoryboardReviewCandidate(job_id=row.job_id, expected_review_revision=row.expected_review_revision, binding=row.binding, status=row.status, delivery_id=row.delivery_id, manifest_hash=row.manifest_hash, storyboard=row.storyboard, report_available=row.report_html is not None, created_at=row.created_at, delivered_at=row.delivered_at)

    @staticmethod
    def _accepted(row: StoryboardReviewRevisionRow) -> AcceptedStoryboardReviewRevision:
        return AcceptedStoryboardReviewRevision(revision=row.revision, candidate_job_id=row.candidate_job_id, content_hash=row.content_hash, binding=row.binding, storyboard=row.storyboard, accepted_at=row.accepted_at)

    def _context(self, session: Any, project_id: str, *, max_cut_seconds: int = DEFAULT_STORYBOARD_MAX_CUT_SECONDS) -> StoryboardReviewContext:
        return self._resolve_context(session, project_id, max_cut_seconds=max_cut_seconds).context

    def _resolve_context(self, session: Any, project_id: str, *, max_cut_seconds: int = DEFAULT_STORYBOARD_MAX_CUT_SECONDS) -> _ResolvedStoryboardContext:
        """Keep the section map with the exact Script resolution that supplied it."""
        script_head = self._script._head(session, project_id)
        accepted_row = session.scalar(select(ScriptRevisionRow).where(
            ScriptRevisionRow.project_id == project_id,
            ScriptRevisionRow.revision == script_head.revision,
        )) if script_head.revision else None
        if script_head.status != "accepted" or accepted_row is None:
            raise ReviewContextError(ReviewContextDiagnostic(code="accepted_script_not_current", owner="script", technical_message="a current accepted F4 script revision is required before preparing storyboard review"))
        script = AcceptedScriptRevision(revision=accepted_row.revision, candidate_job_id=accepted_row.candidate_job_id, content_hash=accepted_row.content_hash, binding=accepted_row.binding, script=accepted_row.script, accepted_at=accepted_row.accepted_at)
        inherited = ScriptBinding.model_validate(script.binding)
        try:
            current, _source, outline, mapping, cast, art = self._script._context_for_binding(session, project_id, inherited)
        except ReviewContextError as error:
            raise ReviewContextError(ReviewContextDiagnostic(code="accepted_script_not_current", owner="script", technical_message="the accepted F4 script context is stale")) from error
        if self._script._binding_diagnostics(current, inherited):
            raise ReviewContextError(ReviewContextDiagnostic(code="accepted_script_not_current", owner="script", technical_message="the accepted F4 script context is stale"))
        if current != inherited:
            raise ReviewContextError(ReviewContextDiagnostic(code="accepted_script_not_current", owner="script", technical_message="the accepted F4 script binding is stale"))
        binding = StoryboardReviewBinding(
            **inherited.model_dump(mode="python"),
            script_revision=script.revision,
            script_content_hash=script.content_hash,
            review_min_cut_seconds=2,
            review_max_cut_seconds=max_cut_seconds,
            review_max_segment_seconds=15,
            dialogue_timing_contract=freeze_f5_dialogue_timing(
                script.script, script_content_hash=script.content_hash,
                language=self._access.rows.project(session, project_id).brief["language"],
            ),
        )
        return _ResolvedStoryboardContext(
            context=(binding, script.script, _upstream_script_outline(outline, mapping, cast, inherited), cast, art),
            section_map=mapping,
        )

    def context_for_binding(self, session: Any, project_id: str, binding: StoryboardReviewBinding) -> StoryboardReviewContext:
        """Resolve the current identity in the frozen F5A mode, including history."""
        return self._project_context(self._context(session, project_id), binding)

    @staticmethod
    def _project_context(context: StoryboardReviewContext, binding: StoryboardReviewBinding) -> StoryboardReviewContext:
        """Apply one binding's frozen mode without changing the shared read inputs."""
        current, *inputs = context
        current = current.model_copy(update={
            "review_max_cut_seconds": binding.review_max_cut_seconds,
            "storyboard_render_contract": None,
        })
        if binding.storyboard_render_contract is not None:
            try:
                contract = freeze_storyboard_brief_style(current.render_contract)
            except (ValueError, OSError) as error:
                raise ReviewContextError(ReviewContextDiagnostic(code="binding_value_changed", owner="storyboard-review", field="storyboard_render_contract", technical_message="storyboard render contract is unavailable or changed")) from error
            current = current.model_copy(update={"storyboard_render_contract": contract})
        return current, *inputs

    def _stale(self, session: Any, project_id: str, binding: StoryboardReviewBinding) -> list[ReviewContextDiagnostic]:
        try:
            context = self._context(session, project_id)
        except ReviewContextError as error:
            return [error.diagnostic]
        return self._binding_diagnostics(context, binding)

    def _binding_diagnostics(self, context: StoryboardReviewContext, binding: StoryboardReviewBinding) -> list[ReviewContextDiagnostic]:
        try:
            current, *_ = self._project_context(context, binding)
        except ReviewContextError as error:
            return [error.diagnostic]
        return review_binding_diagnostics(current, binding, tuple(StoryboardReviewBinding.model_fields))

    def get_state(self, project_id: str) -> StoryboardReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            candidate = session.get(StoryboardReviewCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            accepted = session.scalar(select(StoryboardReviewRevisionRow).where(StoryboardReviewRevisionRow.project_id == project_id, StoryboardReviewRevisionRow.revision == head.revision)) if head.revision else None
            accepted_binding = StoryboardReviewBinding.model_validate(accepted.binding) if accepted else None
            candidate_binding = StoryboardReviewBinding.model_validate(candidate.binding) if candidate else None
            context, context_diagnostic = None, None
            if accepted_binding is not None or candidate_binding is not None:
                try:
                    context = self._context(session, project_id)
                except ReviewContextError as error:
                    context_diagnostic = error.diagnostic

            def stale_for(binding: StoryboardReviewBinding) -> list[ReviewContextDiagnostic]:
                if context_diagnostic is not None:
                    return [context_diagnostic]
                assert context is not None
                return self._binding_diagnostics(context, binding)

            # A current replacement candidate is the active review seam even
            # when retained accepted evidence is stale. Share only this read's
            # base context; each binding keeps its own timing and render mode.
            accepted_stale = stale_for(accepted_binding) if accepted_binding is not None else []
            stale = stale_for(candidate_binding) if candidate_binding is not None else accepted_stale
            accepted_state = accepted_review_state(exists=accepted is not None, candidate_active=candidate is not None, head_status=head.status, stale_reasons=accepted_stale)
            return StoryboardReviewState(accepted_review_state=accepted_state, candidate=self._candidate(candidate) if candidate else None, accepted_review=self._accepted(accepted) if accepted else None, status="stale" if stale else head.status, stale_reasons=stale)

    def prepare_candidate(self, project_id: str, job_id: str, *, max_cut_seconds: int = DEFAULT_STORYBOARD_MAX_CUT_SECONDS, execution_pin: dict[str, str]) -> tuple[StoryboardReviewCandidate, CreativeHandoffRequest]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if session.scalar(select(StoryboardReviewCandidateRow.job_id).where(
                StoryboardReviewCandidateRow.project_id == project_id,
                StoryboardReviewCandidateRow.status.in_(("prepared", "ready")),
            ).limit(1)):
                raise InvalidTransitionError("explicitly accept or cancel the current storyboard review candidate before preparing another")
            binding, script, outline, cast, art = self._context(session, project_id, max_cut_seconds=max_cut_seconds)
            assert binding.dialogue_timing_contract is not None
            assert_f5_dialogue_capacity(binding.dialogue_timing_contract, max_cut_seconds=max_cut_seconds)
            style_contract = None
            if binding.render_contract and binding.render_contract.get("authority") == "saved_brief":
                style_contract = freeze_storyboard_brief_style(binding.render_contract)
                binding = binding.model_copy(update={"storyboard_render_contract": style_contract})
            admission = {
                "scriptRevision": binding.script_revision,
                "scriptContentHash": binding.script_content_hash,
                "sectionBindings": [item.model_dump(mode="json", by_alias=True) for item in binding.section_bindings],
                "routeBudgetHash": binding.route_budget_hash,
                "targetPlaythroughSeconds": binding.target_playthrough_seconds,
                "completeRouteSectionIds": binding.complete_route_section_ids,
                "routeOnlySectionIds": binding.route_only_section_ids,
                "reviewTiming": {
                    "minCutSeconds": binding.review_min_cut_seconds,
                    "maxCutSeconds": binding.review_max_cut_seconds,
                    "maxSegmentSeconds": binding.review_max_segment_seconds,
                },
            }
            artifacts = {"script.json": script, "outline.json": outline, "cast.json": cast, "art.json": art, "storyboard-admission.json": admission, TIMING_FILENAME: binding.dialogue_timing_contract.model_dump(mode="json", by_alias=True)}
            receiving = " Follow dialogue-timing-contract.json: every line, including VO, has a trusted canonical minimum in integer milliseconds. Each cut must fit the sum of minima for its owned flow beats, as well as every upstream timing gate. Spoken language is frozen separately from report lang; free-form performance notes do not select a faster pace. Do not change source text or the contract, raise limits, or distribute one line across cuts."
            if style_contract is not None:
                artifacts[CONTRACT_FILENAME] = style_contract
                receiving += storyboard_brief_instructions()
            else:
                receiving += " Run the pinned novel-storyboard gates through the Plotloom receiving adapter. From the repository root, run node scripts/storyboard-receiving.mjs validate <absolute-delivery/storyboard.json> --request <absolute-package/request.json>, then the same command with render redirected to report.html."
            request = CreativeHandoffRequest(job_id=job_id, project_id=project_id, section_id="pilot-storyboard", stage="storyboard", content_validation_contract="plotloom.typed-content-result.v1", expected_stage_revision=head.revision, source={"acceptedScriptRevision": binding.script_revision, "acceptedScriptContentHash": binding.script_content_hash}, input_artifacts=artifacts, creative_brief=f"Create one raw upstream-shaped storyboard.json for the current accepted F4 script only. storyboard-admission.json freezes the exact accepted script revision/hash, ordered stable section-to-episode mapping, the complete-route maximum and budget hash, and review timing. Preserve unequal authored section lengths; sum actual cuts along each complete route, not across mutually exclusive endings. Retain every mapped episode exactly once and in that order. Set storyboard.params exactly to minCutSeconds {binding.review_min_cut_seconds}, maxCutSeconds {binding.review_max_cut_seconds}, and maxSegmentSeconds {binding.review_max_segment_seconds}; every cut must be {binding.review_min_cut_seconds}–{binding.review_max_cut_seconds} seconds. The script owns dialogue and story facts. Preserve upstream storyboard segments, cuts, frames and H3 prompt text as review direction only. This is review evidence, not canonical Plotloom shots, a SceneBeats/Bible projection, selected reference, media prompt, player content, dispatch request, or approval. Do not generate media or infer deployed H3 duration support." + receiving)
            request.assert_secret_free(); freeze_execution_pin(session, request, execution_pin); now = utc_now()
            row = StoryboardReviewCandidateRow(job_id=job_id, project_id=project_id, expected_review_revision=head.revision, binding=binding.model_dump(mode="json", by_alias=True), request=request.model_dump(mode="json", by_alias=True), status="prepared", delivery_id=None, manifest_hash=None, storyboard=None, report_html=None, created_at=now, delivered_at=None)
            session.add(row); head.candidate_job_id, head.status, head.updated_at = job_id, "prepared", now
            return self._candidate(row), request

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> StoryboardReviewCandidate:
        request = delivery.request
        if request.stage != "storyboard" or request.project_id != project_id:
            raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this storyboard review")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head, row = self._head(session, project_id), session.get(StoryboardReviewCandidateRow, request.job_id)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.request != request.model_dump(mode="json", by_alias=True):
                raise CreativeHandoffError("delivery_stale", "delivery is not the current prepared storyboard review")
            if row.status == "cancelled":
                raise CreativeHandoffError("delivery_cancelled", "storyboard review candidate was cancelled")
            binding = StoryboardReviewBinding.model_validate(row.binding)
            if row.status not in {"prepared", "ready"} or row.expected_review_revision != head.revision or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "storyboard review candidate context is stale")
            if row.status == "ready":
                if row.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "different delivery already occupies storyboard review candidate")
                return self._candidate(row)
            _current, script, outline, cast, _art = self._context(session, project_id, max_cut_seconds=binding.review_max_cut_seconds)
            self._validate(delivery.candidate, binding, script, outline, cast, request)
            row.status, row.delivery_id, row.manifest_hash, row.storyboard, row.report_html, row.delivered_at = "ready", delivery.manifest.delivery_id, delivery.manifest_hash, delivery.candidate, delivery.report.decode("utf-8"), utc_now()
            if not receipt_only(self._access):
                head.status, head.updated_at = "candidate_ready", row.delivered_at
            return self._candidate(row)

    def accept_candidate(self, project_id: str, request: StoryboardReviewAcceptRequest) -> StoryboardReviewState:
        from ...autopilot_contracts import OperationScope
        from .autopilot_authority import allow_manual_or_machine
        allow_manual_or_machine(self._access, OperationScope.TEXT)
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head, row = self._head(session, project_id), session.get(StoryboardReviewCandidateRow, request.job_id)
            if head.revision != request.expected_review_revision:
                raise RevisionConflictError("storyboard review", request.expected_review_revision, head.revision)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.status != "ready" or row.storyboard is None:
                raise InvalidTransitionError("storyboard review candidate is not ready for explicit acceptance")
            # The report and raw candidate are one immutable upstream delivery.
            # Unlike F4's author-owned section edits, F5A has no acceptance-time
            # JSON editor or replacement seam.
            binding, storyboard = StoryboardReviewBinding.model_validate(row.binding), row.storyboard
            if binding != request.binding or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "storyboard review candidate context changed before acceptance")
            _current, script, outline, cast, _art = self._context(session, project_id, max_cut_seconds=binding.review_max_cut_seconds)
            self._validate(storyboard, binding, script, outline, cast, CreativeHandoffRequest.model_validate(row.request))
            now = utc_now(); head.revision += 1; head.candidate_job_id, head.status, head.updated_at, row.status = None, "accepted", now, "accepted"
            session.add(StoryboardReviewRevisionRow(id=new_id(), project_id=project_id, revision=head.revision, candidate_job_id=row.job_id, content_hash=sha256(canonical_json(storyboard)).hexdigest(), binding=binding.model_dump(mode="json", by_alias=True), storyboard=storyboard, accepted_at=now))
        return self.get_state(project_id)

    def cancel_candidate(self, project_id: str, job_id: str) -> StoryboardReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head, row = self._head(session, project_id), session.get(StoryboardReviewCandidateRow, job_id)
            if row is None or row.project_id != project_id:
                raise NotFoundError("project storyboard review candidate is unavailable")
            if row.status == "accepted":
                raise InvalidTransitionError("accepted storyboard review candidate cannot be cancelled")
            row.status = "cancelled"
            if head.candidate_job_id == job_id:
                head.candidate_job_id, head.status, head.updated_at = None, "accepted" if head.revision else "missing", utc_now()
        return self.get_state(project_id)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            row = session.get(StoryboardReviewCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status not in {"ready", "accepted"} or row.report_html is None:
                raise NotFoundError("ready storyboard review report is unavailable")
            return row.report_html

    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            row = session.get(StoryboardReviewCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status == "cancelled":
                raise NotFoundError("project storyboard review candidate is unavailable")
            if row.status in {"prepared", "ready"}:
                head = self._head(session, project_id)
                binding = StoryboardReviewBinding.model_validate(row.binding)
                if head.candidate_job_id != job_id or row.expected_review_revision != head.revision or self._stale(session, project_id, binding):
                    raise CreativeHandoffError("delivery_stale", "storyboard review handoff context is stale")
            return CreativeHandoffRequest.model_validate(row.request)

    @staticmethod
    def _validate(storyboard: dict[str, Any], binding: StoryboardReviewBinding, script: dict[str, Any], outline: dict[str, Any], cast: dict[str, Any], request: CreativeHandoffRequest | None = None) -> None:
        if contains_secret_setting(storyboard) or contains_secret_value(storyboard):
            raise ValueError("storyboard must not contain credentials")
        contract = binding.storyboard_render_contract
        frozen = request.input_artifacts.get(CONTRACT_FILENAME) if request else None
        if frozen != contract or (contract is not None and request is None):
            raise ValueError("storyboard request and binding visual authority must agree")
        if contract is not None:
            validate_storyboard_brief_authority(storyboard, contract, binding.render_contract)
        episodes = storyboard.get("episodes")
        expected = [item.episode for item in binding.section_bindings]
        if not isinstance(episodes, list) or [item.get("ep") for item in episodes if isinstance(item, dict)] != expected or len(episodes) != len(expected):
            raise ValueError("storyboard episodes must exactly match the frozen F4 section-to-episode mapping")
        params = storyboard.get("params")
        expected_params = {
            "minCutSeconds": binding.review_min_cut_seconds,
            "maxCutSeconds": binding.review_max_cut_seconds,
            "maxSegmentSeconds": binding.review_max_segment_seconds,
        }
        if not isinstance(params, dict) or any(params.get(key) != value for key, value in expected_params.items()):
            raise ValueError("storyboard params must exactly match the frozen review timing limits")
        actual: dict[str, float] = {}
        for section in binding.section_bindings:
            episode = next((item for item in episodes if isinstance(item, dict) and item.get("ep") == section.episode), None)
            segments = episode.get("segments") if isinstance(episode, dict) else None
            if not isinstance(segments, list):
                raise ValueError(f"episode {section.episode} is missing storyboard segments")
            episode_seconds = 0.0
            for segment in segments:
                cuts = segment.get("cuts") if isinstance(segment, dict) else None
                if not isinstance(cuts, list) or not cuts:
                    raise ValueError(f"episode {section.episode} has an invalid storyboard segment")
                segment_seconds = 0.0
                for cut in cuts:
                    seconds = cut.get("seconds") if isinstance(cut, dict) else None
                    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
                        raise ValueError(f"episode {section.episode} has a cut without seconds")
                    if not binding.review_min_cut_seconds <= seconds <= binding.review_max_cut_seconds:
                        raise ValueError(f"episode {section.episode} cut duration violates frozen review timing")
                    segment_seconds += seconds
                if segment_seconds > binding.review_max_segment_seconds + 0.0001:
                    raise ValueError(f"episode {section.episode} segment duration violates frozen review timing")
                episode_seconds += segment_seconds
            actual[section.section_id] = episode_seconds
        validate_route_seconds(durations=actual, routes=binding.complete_route_section_ids,
                               route_only_ids=binding.route_only_section_ids,
                               maximum=binding.target_playthrough_seconds, label="storyboard")
        timing = binding.dialogue_timing_contract
        if timing is None or request is None or request.input_artifacts.get(TIMING_FILENAME) != timing.model_dump(mode="json", by_alias=True):
            raise ValueError("storyboard request and binding canonical dialogue timing must agree")
        if request.input_artifacts.get("script.json") != script:
            raise ValueError("storyboard frozen Script differs from accepted Script")
        if timing != freeze_f5_dialogue_timing(script, script_content_hash=binding.script_content_hash, language=timing.language):
            raise ValueError("storyboard canonical dialogue timing differs from accepted Script")
        root = Path(__file__).resolve().parents[4]
        validator = BRIEF_ADAPTER if contract is not None else root / "scripts/storyboard-receiving.mjs"
        if not validator.is_file():
            raise ValueError("pinned upstream novel-storyboard validator is unavailable")
        with tempfile.TemporaryDirectory(prefix="plotloom-storyboard-review-") as directory:
            work = Path(directory)
            paths = {"storyboard": work / "storyboard.json", "script": work / "script.json", "outline": work / "outline.json", "cast": work / "cast.json"}
            for key, value in (("storyboard", storyboard), ("script", script), ("outline", outline), ("cast", cast)):
                paths[key].write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            args = ["node", str(validator), "validate", str(paths["storyboard"])]
            request_path = work / "request.json"
            request_path.write_text(request.model_dump_json(by_alias=True), encoding="utf-8")
            args += ["--request", str(request_path)]
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode:
            raise ValueError(f"upstream novel-storyboard validation failed: {(result.stdout or result.stderr).strip()}")
