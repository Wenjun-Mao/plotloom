"""F5A owner for upstream storyboard review revisions, not production shots."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from sqlalchemy import select

from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import contains_secret_setting, contains_secret_value, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...script_contracts import AcceptedScriptRevision, ScriptBinding
from ...storyboard_review_contracts import (
    AcceptedStoryboardReviewRevision, StoryboardReviewAcceptRequest,
    StoryboardReviewBinding, StoryboardReviewCandidate, StoryboardReviewState,
)
from ..schema.project_storyboard_review import (
    StoryboardReviewCandidateRow, StoryboardReviewHeadRow, StoryboardReviewRevisionRow,
)
from ..schema.project_script import ScriptRevisionRow
from .access import ProjectPersistenceAccess
from .script import ProjectScriptPersistence, _upstream_script_outline


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

    def _context(self, session: Any, project_id: str) -> tuple[StoryboardReviewBinding, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        script_head = self._script._head(session, project_id)
        accepted_row = session.scalar(select(ScriptRevisionRow).where(
            ScriptRevisionRow.project_id == project_id,
            ScriptRevisionRow.revision == script_head.revision,
        )) if script_head.revision else None
        if script_head.status != "accepted" or accepted_row is None:
            raise InvalidTransitionError("a current accepted F4 script revision is required before preparing storyboard review")
        script = AcceptedScriptRevision(revision=accepted_row.revision, candidate_job_id=accepted_row.candidate_job_id, content_hash=accepted_row.content_hash, binding=accepted_row.binding, script=accepted_row.script, accepted_at=accepted_row.accepted_at)
        inherited = ScriptBinding.model_validate(script.binding)
        if self._script._stale(session, project_id, inherited):
            raise InvalidTransitionError("the accepted F4 script context is stale")
        current, _source, outline, mapping, cast, art = self._script._context(session, project_id)
        if current != inherited:
            raise InvalidTransitionError("the accepted F4 script binding is stale")
        return StoryboardReviewBinding(**inherited.model_dump(mode="python"), script_revision=script.revision, script_content_hash=script.content_hash), script.script, _upstream_script_outline(outline, mapping, cast, inherited), cast, art

    def _stale(self, session: Any, project_id: str, binding: StoryboardReviewBinding) -> list[str]:
        try:
            current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error:
            return [str(error)]
        fields = tuple(StoryboardReviewBinding.model_fields)
        return [f"{field.replace('_content_hash', ' content').replace('_revision', ' revision').replace('_', ' ')} changed" for field in fields if getattr(current, field) != getattr(binding, field)]

    def get_state(self, project_id: str) -> StoryboardReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            candidate = session.get(StoryboardReviewCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            accepted = session.scalar(select(StoryboardReviewRevisionRow).where(StoryboardReviewRevisionRow.project_id == project_id, StoryboardReviewRevisionRow.revision == head.revision)) if head.revision else None
            raw_binding = accepted.binding if accepted else candidate.binding if candidate else None
            stale = self._stale(session, project_id, StoryboardReviewBinding.model_validate(raw_binding)) if raw_binding else []
            return StoryboardReviewState(candidate=self._candidate(candidate) if candidate else None, accepted_review=self._accepted(accepted) if accepted else None, status="stale" if stale else head.status, stale_reasons=stale)

    def prepare_candidate(self, project_id: str, job_id: str) -> tuple[StoryboardReviewCandidate, CreativeHandoffRequest]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if session.scalar(select(StoryboardReviewCandidateRow.job_id).where(
                StoryboardReviewCandidateRow.project_id == project_id,
                StoryboardReviewCandidateRow.status.in_(("prepared", "ready")),
            ).limit(1)):
                raise InvalidTransitionError("explicitly accept or cancel the current storyboard review candidate before preparing another")
            binding, script, outline, cast, art = self._context(session, project_id)
            admission = {"scriptRevision": binding.script_revision, "scriptContentHash": binding.script_content_hash, "sectionBindings": [item.model_dump(mode="json", by_alias=True) for item in binding.section_bindings]}
            request = CreativeHandoffRequest(job_id=job_id, project_id=project_id, section_id="pilot-storyboard", stage="storyboard", expected_stage_revision=head.revision, source={"acceptedScriptRevision": binding.script_revision, "acceptedScriptContentHash": binding.script_content_hash}, input_artifacts={"script.json": script, "outline.json": outline, "cast.json": cast, "art.json": art, "storyboard-admission.json": admission}, creative_brief="Create one raw upstream-shaped storyboard.json for the current accepted F4 script only. storyboard-admission.json freezes the exact accepted script revision/hash and the ordered stable section-to-episode mapping; retain every mapped episode exactly once and in that order. The script owns dialogue and story facts. Preserve upstream storyboard segments, cuts, frames and H3 prompt text as review direction only. Run the pinned novel-storyboard validate and render commands, and derive report.html unchanged. This is review evidence, not canonical Plotloom shots, a SceneBeats/Bible projection, selected reference, media prompt, player content, dispatch request, or approval. Do not generate media or infer deployed H3 duration support.")
            request.assert_secret_free(); now = utc_now()
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
            if row.status == "ready":
                if row.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "different delivery already occupies storyboard review candidate")
                return self._candidate(row)
            binding = StoryboardReviewBinding.model_validate(row.binding)
            if row.status != "prepared" or row.expected_review_revision != head.revision or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "storyboard review candidate context is stale")
            current, script, outline, cast, _art = self._context(session, project_id)
            self._validate(delivery.candidate, current, script, outline, cast)
            row.status, row.delivery_id, row.manifest_hash, row.storyboard, row.report_html, row.delivered_at = "ready", delivery.manifest.delivery_id, delivery.manifest_hash, delivery.candidate, delivery.report.decode("utf-8"), utc_now()
            head.status, head.updated_at = "candidate_ready", row.delivered_at
            return self._candidate(row)

    def accept_candidate(self, project_id: str, request: StoryboardReviewAcceptRequest) -> StoryboardReviewState:
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
            current, script, outline, cast, _art = self._context(session, project_id)
            self._validate(storyboard, current, script, outline, cast)
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
            return CreativeHandoffRequest.model_validate(row.request)

    @staticmethod
    def _validate(storyboard: dict[str, Any], binding: StoryboardReviewBinding, script: dict[str, Any], outline: dict[str, Any], cast: dict[str, Any]) -> None:
        if contains_secret_setting(storyboard) or contains_secret_value(storyboard):
            raise ValueError("storyboard must not contain credentials")
        episodes = storyboard.get("episodes")
        expected = [item.episode for item in binding.section_bindings]
        if not isinstance(episodes, list) or [item.get("ep") for item in episodes if isinstance(item, dict)] != expected or len(episodes) != len(expected):
            raise ValueError("storyboard episodes must exactly match the frozen F4 section-to-episode mapping")
        root = Path(__file__).resolve().parents[4]
        validator = root / "third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs"
        if not validator.is_file():
            raise ValueError("pinned upstream novel-storyboard validator is unavailable")
        with tempfile.TemporaryDirectory(prefix="plotloom-storyboard-review-") as directory:
            work = Path(directory)
            paths = {"storyboard": work / "storyboard.json", "script": work / "script.json", "outline": work / "outline.json", "cast": work / "cast.json"}
            for key, value in (("storyboard", storyboard), ("script", script), ("outline", outline), ("cast", cast)):
                paths[key].write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(["node", str(validator), "validate", str(paths["storyboard"]), "--script", str(paths["script"]), "--outline", str(paths["outline"]), "--cast", str(paths["cast"]), "--no-log"], capture_output=True, text=True, check=False)
        if result.returncode:
            raise ValueError(f"upstream novel-storyboard validation failed: {(result.stdout or result.stderr).strip()}")
