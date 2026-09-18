"""F4 source-bound owner for a whole-pilot upstream ``script.json``."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from sqlalchemy import select

from ...art_contracts import ArtBinding
from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import ProjectBrief, contains_secret_setting, contains_secret_value, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...generation.scene_timing_allocation import plan_scene_timing_allocation
from ...script_contracts import (
    AcceptedScriptRevision, ScriptAcceptRequest, ScriptBinding, ScriptCandidate,
    ScriptReopenRequest, ScriptReviewState, ScriptSectionBinding, ScriptSectionDurationCap,
    ScriptSectionSaveRequest,
)
from ...source_outline_contracts import SectionMap, compile_section_map_graph
from ..schema.project_art import ArtRevisionRow
from ..schema.project_script import ScriptCandidateRow, ScriptHeadRow, ScriptRevisionRow
from .access import ProjectPersistenceAccess
from .art import ProjectArtPersistence


class ProjectScriptPersistence:
    """Stores untransformed upstream JSON and binds its episodes to F1B IDs."""

    def __init__(self, access: ProjectPersistenceAccess, art: ProjectArtPersistence) -> None:
        self._access, self._art = access, art

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(ScriptHeadRow, project_id) is None:
            session.add(ScriptHeadRow(project_id=project_id, revision=0, candidate_job_id=None, status="missing", updated_at=created_at))

    @staticmethod
    def _head(session: Any, project_id: str) -> ScriptHeadRow:
        row = session.get(ScriptHeadRow, project_id)
        if row is None: raise NotFoundError("project script review state is missing")
        return row

    @staticmethod
    def _candidate(row: ScriptCandidateRow) -> ScriptCandidate:
        return ScriptCandidate(job_id=row.job_id, expected_script_revision=row.expected_script_revision, binding=row.binding, status=row.status, delivery_id=row.delivery_id, manifest_hash=row.manifest_hash, script=row.script, report_available=row.report_html is not None, created_at=row.created_at, delivered_at=row.delivered_at)

    @staticmethod
    def _accepted(row: ScriptRevisionRow) -> AcceptedScriptRevision:
        return AcceptedScriptRevision(revision=row.revision, candidate_job_id=row.candidate_job_id, content_hash=row.content_hash, binding=row.binding, script=row.script, accepted_at=row.accepted_at)

    def _context(self, session: Any, project_id: str) -> tuple[ScriptBinding, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        art_head = self._art._head(session, project_id)
        accepted = session.scalar(select(ArtRevisionRow).where(ArtRevisionRow.project_id == project_id, ArtRevisionRow.revision == art_head.revision)) if art_head.revision else None
        if art_head.status != "accepted" or accepted is None or self._art._stale(session, project_id, ArtBinding.model_validate(accepted.binding)):
            raise InvalidTransitionError("a current accepted art revision is required before preparing script")
        project = self._access.rows.project(session, project_id)
        target_seconds = int(project.brief.get("target_playthrough_seconds", 0))
        if target_seconds < 3:
            raise InvalidTransitionError("project playthrough target is required for script preparation")
        art_binding, source, outline, mapping, cast = self._art._context(session, project_id)
        section_map = SectionMap.model_validate(mapping)
        graph = compile_section_map_graph(section_map)
        allocation = plan_scene_timing_allocation(
            graph=graph, brief=ProjectBrief.model_validate(project.brief)
        )
        section_bindings = [
            ScriptSectionBinding(section_id=section.section_id, episode=index)
            for index, section in enumerate(section_map.sections, start=1)
        ]
        section_caps = [
            ScriptSectionDurationCap(
                section_id=section.section_id,
                duration_cap_milliseconds=allocation.node_duration_budget(section.section_id),
            )
            for section in section_map.sections
        ]
        binding = ScriptBinding(
            **accepted.binding,
            art_revision=accepted.revision,
            art_content_hash=accepted.content_hash,
            target_playthrough_seconds=target_seconds,
            timing_allocation_hash=allocation.allocation_hash,
            section_bindings=section_bindings,
            section_duration_caps=section_caps,
            complete_route_section_ids=[
                [section_map.choice.section_id, outcome.ending_section_id]
                for outcome in section_map.choice.outcomes
            ],
        )
        assert art_binding.source_revision == binding.source_revision
        return binding, source, outline, mapping, cast, accepted.art

    def _stale(self, session: Any, project_id: str, binding: ScriptBinding) -> list[str]:
        try: current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error: return [str(error)]
        fields = ("source_revision", "source_content_hash", "outline_revision", "outline_content_hash", "section_map_revision", "section_map_content_hash", "graph_revision", "graph_content_hash", "cast_revision", "cast_content_hash", "art_revision", "art_content_hash", "target_playthrough_seconds", "timing_allocation_hash", "section_bindings", "section_duration_caps", "complete_route_section_ids")
        labels = {key: key.replace("_content_hash", " content").replace("_revision", " revision").replace("_", " ") for key in fields}
        reasons = [f"{labels[field]} changed" for field in fields if getattr(current, field) != getattr(binding, field)]
        return reasons + (["section context changed"] if current.section_ids != binding.section_ids else [])

    def get_state(self, project_id: str) -> ScriptReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            candidate = session.get(ScriptCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            accepted = session.scalar(select(ScriptRevisionRow).where(ScriptRevisionRow.project_id == project_id, ScriptRevisionRow.revision == head.revision)) if head.revision else None
            binding = accepted.binding if accepted else candidate.binding if candidate else None
            stale = self._stale(session, project_id, ScriptBinding.model_validate(binding)) if binding else []
            return ScriptReviewState(candidate=self._candidate(candidate) if candidate else None, accepted_script=self._accepted(accepted) if accepted else None, status="stale" if stale and accepted else head.status, stale_reasons=stale)

    def prepare_candidate(self, project_id: str, job_id: str) -> tuple[ScriptCandidate, CreativeHandoffRequest]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if session.scalar(select(ScriptCandidateRow.job_id).where(ScriptCandidateRow.project_id == project_id, ScriptCandidateRow.status == "prepared").limit(1)):
                raise InvalidTransitionError("cancel the prepared script specialist publication before changing review state")
            binding, source, outline, mapping, cast, art = self._context(session, project_id)
            upstream_outline = _upstream_script_outline(outline, mapping, cast, binding)
            admission = _script_admission_artifact(binding)
            request = CreativeHandoffRequest(job_id=job_id, project_id=project_id, section_id="pilot-script", stage="script", expected_stage_revision=head.revision, source=source, input_artifacts={"accepted-outline.json": outline, "outline.json": upstream_outline, "section-map.json": mapping, "cast.json": cast, "art.json": art, "script-admission.json": admission}, creative_brief=f"Create one upstream-shaped script.json for the whole current one-choice/two-ending pilot. The author-owned frozen target of {binding.target_playthrough_seconds} seconds is a hard maximum for each complete route, never a required runtime. script-admission.json freezes the exact sectionBindings order and graph-derived section caps; use that mapping unchanged. The opening plus either ending must remain within the frozen route maximum. Do not stretch a section to its cap, do not sum mutually exclusive endings, and do not substitute upstream's three-minute default. accepted-outline.json is preserved F1 evidence; outline.json is trusted code's thin upstream execution projection of only the same stable section summaries and accepted cast identities, because the F1 section representation is not upstream episode-shaped. Do not treat it as a new canonical outline or invent Bible/shot fields. Set top-level lang to en so the unchanged pinned render is reproducible without a renderer flag. Use one episode per section, retain the upstream scenes/action/dialogue flow unchanged, and preserve the actual decision consequence, incoming context, completed actions, speaker identities, and timing. This is an intentionally non-episode pilot. The upstream JSON's required hook/cliff strings are validator structural fields only: for every section, state the actual route-entry/terminal status plainly and do not invent an episodic hook, suspense, or promise of a next episode. Render report.html with the pinned upstream command unchanged; do not inject a wrapper or claim that its structural gate output is product acceptance. Plotloom's review UI labels hook/cliff and duration as product-inapplicable for this pilot. F5 consumes the accepted upstream script JSON plus this section binding; it replaces only overlapping scene/beat authoring and does not produce shots, prompts, media, or TTS.")
            request.assert_secret_free(); now = utc_now()
            row = ScriptCandidateRow(job_id=job_id, project_id=project_id, expected_script_revision=head.revision, binding=binding.model_dump(mode="json", by_alias=True), request=request.model_dump(mode="json", by_alias=True), status="prepared", delivery_id=None, manifest_hash=None, script=None, report_html=None, created_at=now, delivered_at=None)
            session.add(row); head.candidate_job_id, head.status, head.updated_at = job_id, "prepared", now
            return self._candidate(row), request

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> ScriptCandidate:
        request = delivery.request
        if request.stage != "script" or request.project_id != project_id: raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this script proposal")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head, row = self._head(session, project_id), session.get(ScriptCandidateRow, request.job_id)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.request != request.model_dump(mode="json", by_alias=True): raise CreativeHandoffError("delivery_stale", "delivery is not the current prepared script proposal")
            if row.status == "cancelled": raise CreativeHandoffError("delivery_cancelled", "script candidate was cancelled")
            if row.status == "ready":
                if row.manifest_hash != delivery.manifest_hash: raise CreativeHandoffError("delivery_conflict", "different delivery already occupies script candidate")
                return self._candidate(row)
            binding = ScriptBinding.model_validate(row.binding)
            if row.status != "prepared" or row.expected_script_revision != head.revision or self._stale(session, project_id, binding): raise CreativeHandoffError("delivery_stale", "script candidate context is stale")
            _binding, _source, outline, mapping, cast, art = self._context(session, project_id)
            self._validate(delivery.candidate, binding, _upstream_script_outline(outline, mapping, cast, binding), art)
            row.status, row.delivery_id, row.manifest_hash, row.script, row.report_html, row.delivered_at = "ready", delivery.manifest.delivery_id, delivery.manifest_hash, delivery.candidate, delivery.report.decode("utf-8"), utc_now()
            head.status, head.updated_at = "candidate_ready", row.delivered_at
            return self._candidate(row)

    def accept_candidate(self, project_id: str, request: ScriptAcceptRequest) -> ScriptReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head, row = self._head(session, project_id), session.get(ScriptCandidateRow, request.job_id)
            if head.revision != request.expected_script_revision: raise RevisionConflictError("script", request.expected_script_revision, head.revision)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.status != "ready" or row.script is None: raise InvalidTransitionError("script candidate is not ready for explicit acceptance")
            binding, script = ScriptBinding.model_validate(row.binding), request.script or row.script
            if binding != request.binding or self._stale(session, project_id, binding): raise CreativeHandoffError("delivery_stale", "script candidate context changed before acceptance")
            _binding, _source, outline, mapping, cast, art = self._context(session, project_id)
            self._validate(script, binding, _upstream_script_outline(outline, mapping, cast, binding), art)
            now = utc_now(); head.revision += 1; head.candidate_job_id, head.status, head.updated_at, row.status = None, "accepted", now, "accepted"
            self._save(session, project_id, head.revision, row.job_id, binding, script, now)
        return self.get_state(project_id)

    def reopen(self, project_id: str, request: ScriptReopenRequest) -> ScriptReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if head.revision != request.expected_script_revision: raise RevisionConflictError("script", request.expected_script_revision, head.revision)
            if not head.revision: raise InvalidTransitionError("no accepted script exists to reopen")
            if head.candidate_job_id: raise InvalidTransitionError("cancel the current script specialist publication before reopening accepted script")
            head.status, head.updated_at = "reopened", utc_now()
        return self.get_state(project_id)

    def save_section(self, project_id: str, request: ScriptSectionSaveRequest) -> ScriptReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if head.revision != request.expected_script_revision: raise RevisionConflictError("script", request.expected_script_revision, head.revision)
            if head.status != "reopened": raise InvalidTransitionError("reopen accepted script before saving author edits")
            previous = session.scalar(select(ScriptRevisionRow).where(ScriptRevisionRow.project_id == project_id, ScriptRevisionRow.revision == head.revision))
            if previous is None: raise NotFoundError("accepted script revision is missing")
            binding = ScriptBinding.model_validate(previous.binding)
            if binding != request.binding or self._stale(session, project_id, binding): raise CreativeHandoffError("delivery_stale", "accepted script context changed before saving edits")
            script = json.loads(json.dumps(previous.script)); bindings = _section_bindings(script, binding)
            expected_episode = bindings.get(request.section_id)
            if expected_episode is None or request.episode.get("ep") != expected_episode: raise ValueError("section edit must retain its frozen upstream episode binding")
            episodes = script["episodes"]; index = next(i for i, item in enumerate(episodes) if item.get("ep") == expected_episode)
            episodes[index] = request.episode
            _binding, _source, outline, mapping, cast, art = self._context(session, project_id)
            self._validate(script, binding, _upstream_script_outline(outline, mapping, cast, binding), art)
            now = utc_now(); head.revision, head.status, head.updated_at = head.revision + 1, "accepted", now
            self._save(session, project_id, head.revision, previous.candidate_job_id, binding, script, now)
        return self.get_state(project_id)

    def cancel_candidate(self, project_id: str, job_id: str) -> ScriptReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head, row = self._head(session, project_id), session.get(ScriptCandidateRow, job_id)
            if row is None or row.project_id != project_id: raise NotFoundError("project script candidate is unavailable")
            if row.status == "accepted": raise InvalidTransitionError("accepted script candidate cannot be cancelled")
            row.status = "cancelled"
            if head.candidate_job_id == job_id: head.candidate_job_id, head.status, head.updated_at = None, "accepted" if head.revision else "missing", utc_now()
        return self.get_state(project_id)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            row = session.get(ScriptCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status not in {"ready", "accepted"} or row.report_html is None: raise NotFoundError("ready script report is unavailable")
            head = self._head(session, project_id)
            accepted = session.scalar(select(ScriptRevisionRow).where(
                ScriptRevisionRow.project_id == project_id,
                ScriptRevisionRow.revision == head.revision,
                ScriptRevisionRow.candidate_job_id == job_id,
            ))
            if accepted is not None and canonical_json(accepted.script) != canonical_json(row.script):
                return (
                    "<!doctype html><html><body><p><strong>Original specialist report.</strong> "
                    "The accepted script.json was edited after this report was derived; this report does not describe the current accepted revision.</p>"
                    f"<hr>{row.report_html}</body></html>"
                )
            return row.report_html

    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            row = session.get(ScriptCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status == "cancelled": raise NotFoundError("project script candidate is unavailable")
            return CreativeHandoffRequest.model_validate(row.request)

    @staticmethod
    def _save(session: Any, project_id: str, revision: int, candidate_job_id: str, binding: ScriptBinding, script: dict[str, Any], accepted_at: Any) -> None:
        session.add(ScriptRevisionRow(id=new_id(), project_id=project_id, revision=revision, candidate_job_id=candidate_job_id, content_hash=sha256(canonical_json(script)).hexdigest(), binding=binding.model_dump(mode="json", by_alias=True), script=script, accepted_at=accepted_at))

    @staticmethod
    def _validate(script: dict[str, Any], binding: ScriptBinding, outline: dict[str, Any], art: dict[str, Any]) -> None:
        if contains_secret_setting(script) or contains_secret_value(script): raise ValueError("script must not contain credentials")
        _section_bindings(script, binding)
        repository = Path(__file__).resolve().parents[4]; validator = repository / "third_party/shuohao-skills/skills/novel-script/scripts/novel-script.mjs"
        if not validator.is_file(): raise ValueError("pinned upstream novel-script validator is unavailable")
        # The upstream validator retains creative validation ownership. Its episode-only
        # gates are intentionally reported, not rewritten, for this DAG pilot.
        with tempfile.TemporaryDirectory(prefix="plotloom-script-validate-") as directory:
            root = Path(directory); script_path, outline_path, art_path = root / "script.json", root / "outline.json", root / "art.json"
            script_path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8"); outline_path.write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8"); art_path.write_text(json.dumps(art, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(["node", str(validator), "validate", str(script_path), "--outline", str(outline_path), "--art", str(art_path)], capture_output=True, text=True, check=False)
            stats = _upstream_timing_stats(script_path, validator)
        if result.returncode: raise ValueError(f"upstream novel-script validation failed: {(result.stdout or result.stderr).strip()}")
        _validate_timing_caps(script, binding, stats)


def _section_bindings(script: dict[str, Any], binding: ScriptBinding) -> dict[str, int]:
    entries = script.get("sectionBindings")
    if not isinstance(entries, list): raise ValueError("script must contain Plotloom sectionBindings")
    try: bindings = [ScriptSectionBinding.model_validate(item) for item in entries]
    except ValueError as error: raise ValueError("script sectionBindings are invalid") from error
    if bindings != binding.section_bindings: raise ValueError("script sectionBindings must exactly match the frozen section-to-episode mapping")
    episodes = script.get("episodes")
    if not isinstance(episodes, list) or {item.get("ep") for item in episodes if isinstance(item, dict)} != {item.episode for item in bindings} or len(episodes) != len(bindings): raise ValueError("script episodes must match sectionBindings exactly")
    return {item.section_id: item.episode for item in bindings}


def _script_admission_artifact(binding: ScriptBinding) -> dict[str, Any]:
    """Expose trusted F4 limits without creating another creative authority."""

    return {
        "targetPlaythroughSeconds": binding.target_playthrough_seconds,
        "timingAllocationHash": binding.timing_allocation_hash,
        "sectionBindings": [item.model_dump(mode="json", by_alias=True) for item in binding.section_bindings],
        "sectionDurationCaps": [item.model_dump(mode="json", by_alias=True) for item in binding.section_duration_caps],
        "completeRouteSectionIds": binding.complete_route_section_ids,
    }


def _upstream_timing_stats(script_path: Path, validator: Path) -> dict[str, Any]:
    """Use the pinned upstream estimator verbatim for F4 ceiling checks."""

    program = (
        f"import {{ computeStats }} from {json.dumps(validator.as_uri())};"
        "import { readFileSync } from 'node:fs';"
        "console.log(JSON.stringify(computeStats(JSON.parse(readFileSync(process.argv[1], 'utf8')))));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", program, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError("upstream novel-script timing estimator is unavailable")
    try:
        stats = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("upstream novel-script timing estimator returned invalid data") from error
    if not isinstance(stats, dict) or not isinstance(stats.get("episodes"), list):
        raise ValueError("upstream novel-script timing estimator returned incomplete data")
    return stats


def _validate_timing_caps(
    script: dict[str, Any], binding: ScriptBinding, stats: dict[str, Any]
) -> None:
    """Apply the author maximum to actual F1B sections and complete routes."""

    by_episode = {
        item.get("ep"): item
        for item in stats["episodes"]
        if isinstance(item, dict) and isinstance(item.get("ep"), int)
    }
    caps = {
        item.section_id: item.duration_cap_milliseconds / 1_000
        for item in binding.section_duration_caps
    }
    actual: dict[str, float] = {}
    for section in binding.section_bindings:
        episode = by_episode.get(section.episode)
        cap = caps.get(section.section_id)
        if episode is None or cap is None:
            raise ValueError("script timing is missing a frozen section")
        target, estimate = episode.get("target"), episode.get("est")
        if not isinstance(target, (int, float)) or not isinstance(estimate, (int, float)):
            raise ValueError("upstream script timing is incomplete")
        if target > cap + 0.05:
            raise ValueError(f"episode {section.episode} targetSeconds exceeds its frozen section cap")
        if estimate > cap + 0.05:
            raise ValueError(f"episode {section.episode} estimated duration exceeds its frozen section cap")
        actual[section.section_id] = float(estimate)
    for route in binding.complete_route_section_ids:
        duration = sum(actual.get(section_id, float("inf")) for section_id in route)
        if duration > binding.target_playthrough_seconds + 0.05:
            raise ValueError("a complete script route exceeds the author playthrough maximum")


def _upstream_script_outline(
    accepted_outline: dict[str, Any], section_map: dict[str, Any], cast: dict[str, Any], binding: ScriptBinding,
) -> dict[str, Any]:
    """Project F1B's section form is not an upstream script input shape.

    This execution-only projection preserves the accepted evidence separately
    and supplies only the upstream validator's character/episode references.
    It is deliberately not persisted or exposed as a second outline authority.
    """

    sections = section_map.get("sections")
    characters = cast.get("characters")
    if not isinstance(sections, list) or not isinstance(characters, list):
        raise InvalidTransitionError("current section map and cast are required for script preparation")
    projected_characters = [
        {"id": item.get("id"), "name": item.get("name")}
        for item in characters if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if not projected_characters:
        raise InvalidTransitionError("current accepted cast must provide script speaker identities")
    expected = {item.section_id: item.episode for item in binding.section_bindings}
    caps = {item.section_id: item.duration_cap_milliseconds / 1000 for item in binding.section_duration_caps}
    episodes = [
        {"ep": expected[str(item.get("sectionId"))], "synopsis": item.get("summary", ""), "sceneIds": [], "characterIds": [item["id"] for item in projected_characters], "durationCapSeconds": caps[str(item.get("sectionId"))]}
        for item in sections if isinstance(item, dict) and str(item.get("sectionId")) in expected
    ]
    if len(episodes) != 3:
        raise InvalidTransitionError("script preparation requires exactly three stable pilot sections")
    return {"source": accepted_outline.get("source", ""), "params": {"minutesPerEpisode": binding.target_playthrough_seconds / (2 * 60)}, "characters": projected_characters, "episodes": episodes, "beats": []}
