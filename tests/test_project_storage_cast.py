"""F2A regression: cast candidate acceptance is source/outline/map bound."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.cast_contracts import (
    CastAcceptRequest,
    CastBinding,
    CastCancelReopenRequest,
    CastConsumerMapping,
    CastReopenRequest,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.domain import utc_now
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.operational_state import close_blockers
from plotloom.project_storage.recovery import ProjectRecoveryService
from plotloom.source_outline_contracts import (
    AcceptedOutlineRevision, AcceptedSectionMapRevision, SectionChoice, SectionMap,
    SourceMapGraphAdmission, SourceMaterial, SourceOutlineReviewState, SourceRevision,
    StorySection, BranchOutcome,
)


def _context(revision: int = 1) -> SourceOutlineReviewState:
    material = SourceMaterial(kind="synopsis", title="Tide Light", text="Lin chooses power.", attribution="fixture", rights_declaration="fixture", adaptation_intent="branch")
    source_hash = f"{revision:x}" * 64
    outline_hash = "b" * 64
    map_hash = "c" * 64
    mapping = SectionMap(
        sections=[StorySection(section_id="opening", title="Opening", summary="Lin hears the storm"), StorySection(section_id="beacon", title="Beacon", summary="The beacon stays lit", ending=True), StorySection(section_id="dock", title="Dock", summary="The dock stays lit", ending=True)],
        choice=SectionChoice(choice_id="power", section_id="opening", prompt="Where?", outcomes=[BranchOutcome(outcome_id="beacon-path", label="Beacon", consequence="Dock dark", ending_section_id="beacon"), BranchOutcome(outcome_id="dock-path", label="Dock", consequence="Beacon dark", ending_section_id="dock")]),
    )
    return SourceOutlineReviewState(source=SourceRevision(revision=revision, content_hash=source_hash[:64], material=material, created_at=utc_now()), candidate=None, accepted_outline=AcceptedOutlineRevision(revision=1, source_revision=revision, candidate_job_id="ch_" + "a" * 32, content_hash=outline_hash, outline={"source": "Tide Light"}, accepted_at=utc_now()), outline_status="accepted", accepted_section_map=AcceptedSectionMapRevision(revision=1, source_revision=revision, outline_revision=1, outline_content_hash=outline_hash, content_hash=map_hash, mapping=mapping, accepted_at=utc_now()), section_map_status="current", section_map_stale_reasons=[], graph_admission=None)


def _deliver(store: object, request: CreativeHandoffRequest) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    paths = exchange.write_package(request); package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"]); delivery.mkdir()
    cast = canonical_json({"source": "Tide Light", "summary": "Lin chooses power.", "characters": [{"id": "lin", "name": "Lin", "persona": {"motivation": "Protect people", "appearance": "Windburned", "arc": "Chooses"}, "voice": {"timbre": "Calm"}}]})
    report = b"<!doctype html><html><body>cast report</body></html>"
    (delivery / "cast.json").write_bytes(cast); (delivery / "report.html").write_bytes(report)
    manifest = {"schemaVersion": 1, "jobId": request.job_id, "requestHash": package["requestHash"], "deliveryId": "cast-fixture", "stage": "characters", "candidate": {"filename": "cast.json", "sha256": sha256(cast).hexdigest()}, "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()}, "executorProvenance": {"codeRevision": "abcdef0", "skillVersion": "fixture", "skillHash": package["executionPin"]["specialistSkillHash"], "upstreamRevision": package["executionPin"]["upstreamRevision"], "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"}, "limitations": ["fixture"]}
    (delivery / "completion.json").write_text(json.dumps(manifest)); result = exchange.read_delivery(request); assert result is not None
    return result


def test_cast_acceptance_preserves_authored_edit_and_rejects_stale_context(tmp_path: Path) -> None:
    store = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application").projects.create(FIXED_CHINESE_BRIEF)
    context = _context()

    def bound_context(_session: object, _project_id: str) -> tuple[CastBinding, dict[str, object], dict[str, object], dict[str, object]]:
        assert context.source and context.accepted_outline and context.accepted_section_map
        binding = CastBinding(source_revision=context.source.revision, source_content_hash=context.source.content_hash, outline_revision=context.accepted_outline.revision, outline_content_hash=context.accepted_outline.content_hash, section_map_revision=context.accepted_section_map.revision, section_map_content_hash=context.accepted_section_map.content_hash, graph_revision=1, graph_content_hash="d" * 64, section_ids=["opening", "beacon", "dock"])
        return binding, context.source.material.model_dump(mode="json", by_alias=True), context.accepted_outline.outline, context.accepted_section_map.mapping.model_dump(mode="json", by_alias=True)

    store.repository.cast._context = bound_context  # type: ignore[method-assign]
    try:
        binding, *_ = bound_context(None, store.manifest.project_id)
        _candidate, request = store.prepare_cast_candidate("ch_" + "b" * 32)
        assert "characters[].id values" in request.creative_brief
        package_paths = store.creative_handoff_exchange().write_package(request)
        frozen_instructions = (
            Path(package_paths["packagePath"]) / "COPY_ASSIGNMENT.txt"
        ).read_text()
        assert "characters[].id must be unique and nonblank" in frozen_instructions
        ready = store.admit_cast_delivery(_deliver(store, request))
        edited = dict(ready.cast or {}); edited["characters"] = [dict(edited["characters"][0], persona={"motivation": "Save both crews", "appearance": "Windburned", "arc": "Chooses"})]
        accepted = store.accept_cast_candidate(CastAcceptRequest(job_id=request.job_id, expected_cast_revision=0, binding=binding, cast=edited, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")]))
        assert accepted.accepted_cast is not None and accepted.accepted_cast.cast["characters"][0]["persona"]["motivation"] == "Save both crews"
        with store.repository._read() as session:  # type: ignore[attr-defined]
            identity = store.repository.cast.identity_context_in_session(  # type: ignore[attr-defined]
                session, store.manifest.project_id, "lin"
            )
        assert identity == {
            "revision": 1,
            "contentHash": accepted.accepted_cast.content_hash,
            "castCharacterId": "lin",
            "appearance": "Windburned",
            "image": None,
        }
        store.reopen_cast(CastReopenRequest(expected_cast_revision=1))
        with store.repository._read() as session:  # type: ignore[attr-defined]
            assert store.repository.cast.identity_context_in_session(  # type: ignore[attr-defined]
                session, store.manifest.project_id, "lin"
            ) is None
        replacement, _replacement_request = store.prepare_cast_candidate("ch_" + "c" * 32)
        recovered = store.cancel_cast_candidate(replacement.job_id)
        assert recovered.status == "accepted"
        next_candidate, _next_request = store.prepare_cast_candidate("ch_" + "d" * 32)
        store.cancel_cast_candidate(next_candidate.job_id)
        context = _context(2)
        assert store.cast_state().status == "stale"
        assert store.cast_state().status == "stale"
    finally:
        store.close()


def test_cancel_reopened_cast_restores_only_current_accepted_authority(tmp_path: Path) -> None:
    store = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application").projects.create(FIXED_CHINESE_BRIEF)
    context = _context()

    def bound_context(_session: object, _project_id: str) -> tuple[CastBinding, dict[str, object], dict[str, object], dict[str, object]]:
        assert context.source and context.accepted_outline and context.accepted_section_map
        binding = CastBinding(source_revision=context.source.revision, source_content_hash=context.source.content_hash, outline_revision=context.accepted_outline.revision, outline_content_hash=context.accepted_outline.content_hash, section_map_revision=context.accepted_section_map.revision, section_map_content_hash=context.accepted_section_map.content_hash, graph_revision=1, graph_content_hash="d" * 64, section_ids=["opening", "beacon", "dock"])
        return binding, context.source.material.model_dump(mode="json", by_alias=True), context.accepted_outline.outline, context.accepted_section_map.mapping.model_dump(mode="json", by_alias=True)

    store.repository.cast._context = bound_context  # type: ignore[method-assign]
    try:
        binding, *_ = bound_context(None, store.manifest.project_id)
        _candidate, request = store.prepare_cast_candidate("ch_" + "k" * 32)
        store.admit_cast_delivery(_deliver(store, request))
        accepted = store.accept_cast_candidate(CastAcceptRequest(job_id=request.job_id, expected_cast_revision=0, binding=binding, cast=None, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")]))
        original_hash = accepted.accepted_cast.content_hash if accepted.accepted_cast else ""

        store.reopen_cast(CastReopenRequest(expected_cast_revision=1))
        restored = store.cancel_reopened_cast(CastCancelReopenRequest(expected_cast_revision=1))
        assert restored.status == "accepted"
        assert restored.accepted_cast is not None
        assert restored.accepted_cast.revision == 1
        assert restored.accepted_cast.content_hash == original_hash
        with store.repository._read() as session:  # type: ignore[attr-defined]
            assert store.repository.cast.identity_context_in_session(session, store.manifest.project_id, "lin") is not None  # type: ignore[attr-defined]

        store.reopen_cast(CastReopenRequest(expected_cast_revision=1))
        context = _context(2)
        with pytest.raises(CreativeHandoffError, match="cannot be restored"):
            store.cancel_reopened_cast(CastCancelReopenRequest(expected_cast_revision=1))
        # The failed cancellation cannot turn a stale accepted revision back on.
        assert store.cast_state().status == "stale"
        with store.repository._read() as session:  # type: ignore[attr-defined]
            assert store.repository.cast.identity_context_in_session(session, store.manifest.project_id, "lin") is None  # type: ignore[attr-defined]
    finally:
        store.close()


def test_cast_reference_proposal_freezes_accepted_subject_without_story_bible(tmp_path: Path) -> None:
    """F2B has cast authority only; adding a Bible to make this pass is forbidden."""
    store = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application").projects.create(FIXED_CHINESE_BRIEF)
    context = _context()

    def bound_context(_session: object, _project_id: str) -> tuple[CastBinding, dict[str, object], dict[str, object], dict[str, object]]:
        assert context.source and context.accepted_outline and context.accepted_section_map
        binding = CastBinding(source_revision=context.source.revision, source_content_hash=context.source.content_hash, outline_revision=context.accepted_outline.revision, outline_content_hash=context.accepted_outline.content_hash, section_map_revision=context.accepted_section_map.revision, section_map_content_hash=context.accepted_section_map.content_hash, graph_revision=1, graph_content_hash="d" * 64, section_ids=["opening", "beacon", "dock"])
        return binding, context.source.material.model_dump(mode="json", by_alias=True), context.accepted_outline.outline, context.accepted_section_map.mapping.model_dump(mode="json", by_alias=True)

    store.repository.cast._context = bound_context  # type: ignore[method-assign]
    try:
        binding, *_ = bound_context(None, store.manifest.project_id)
        _candidate, request = store.prepare_cast_candidate("ch_" + "e" * 32)
        store.admit_cast_delivery(_deliver(store, request))
        accepted = store.accept_cast_candidate(CastAcceptRequest(job_id=request.job_id, expected_cast_revision=0, binding=binding, cast=None, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")]))
        proposal = store.media.prepare_character_reference_proposal(
            store.manifest.project_id,
            character_id="lin",
            cast_revision=accepted.accepted_cast.revision,
            visual_direction="Three-quarter portrait, standing at a rain-dark beacon window.",
            parent_candidate_asset_id=None,
        )["proposal"]
        frozen = proposal["request"]["frozenSnapshot"]
        assert frozen["castRevision"] == 1
        assert frozen["acceptedCast"]["contentHash"] == accepted.accepted_cast.content_hash
        assert frozen["characterContext"]["authority"] == "cast"
        assert frozen["characterContext"]["appearance"] == "Windburned"
        cancelled = store.media.cancel_character_reference_proposal(
            store.manifest.project_id,
            proposal["id"],
            "Operator stopped this exploratory handoff before delivery.",
        )
        assert cancelled["state"] == "cancelled"
        assert cancelled["current"] is False
        assert cancelled["cancellationReason"] == "Operator stopped this exploratory handoff before delivery."
        # Cancellation is terminal even though a late receipt may later be
        # retained as inapplicable evidence; it cannot strand close/recovery.
        assert "character_reference_publication_active" not in close_blockers(store)
        assert "character_reference_publication_active" not in ProjectRecoveryService._specialist_blockers(store)
        with pytest.raises(InvalidTransitionError, match="no longer current"):
            store.media.character_reference_proposal_package_sources(
                store.manifest.project_id, proposal["id"]
            )
        store.reopen_cast(CastReopenRequest(expected_cast_revision=1))
        assert proposal["current"] is True
        assert store.media.character_reference_proposal_delivery_context(store.manifest.project_id, proposal["id"])["current"] is False
    finally:
        store.close()


def test_imported_appearance_is_cast_bound_and_requires_explicit_selection(tmp_path: Path) -> None:
    """A managed import gains no identity authority until the creator selects it."""

    store = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application").projects.create(FIXED_CHINESE_BRIEF)
    context = _context()

    def bound_context(_session: object, _project_id: str) -> tuple[CastBinding, dict[str, object], dict[str, object], dict[str, object]]:
        assert context.source and context.accepted_outline and context.accepted_section_map
        binding = CastBinding(source_revision=context.source.revision, source_content_hash=context.source.content_hash, outline_revision=context.accepted_outline.revision, outline_content_hash=context.accepted_outline.content_hash, section_map_revision=context.accepted_section_map.revision, section_map_content_hash=context.accepted_section_map.content_hash, graph_revision=1, graph_content_hash="d" * 64, section_ids=["opening", "beacon", "dock"])
        return binding, context.source.material.model_dump(mode="json", by_alias=True), context.accepted_outline.outline, context.accepted_section_map.mapping.model_dump(mode="json", by_alias=True)

    store.repository.cast._context = bound_context  # type: ignore[method-assign]
    try:
        binding, *_ = bound_context(None, store.manifest.project_id)
        _candidate, request = store.prepare_cast_candidate("ch_" + "i" * 32)
        store.admit_cast_delivery(_deliver(store, request))
        accepted = store.accept_cast_candidate(CastAcceptRequest(job_id=request.job_id, expected_cast_revision=0, binding=binding, cast=None, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")]))
        content = b"retained imported appearance"
        uri = store.artifacts.put(content)
        asset = store.media.record_managed_import(
            store.manifest.project_id, original_hash=sha256(content).hexdigest(), display_hash=sha256(content).hexdigest(),
            mime_type="image/png", byte_size=len(content), width=1, height=1,
            declaration={"origin": "storage fixture", "rights": "known"}, publish=lambda: (uri, uri),
        )
        appearance = store.media.attach_imported_character_appearance(
            store.manifest.project_id, character_id="lin", asset_id=asset["id"], label="Beacon coat reference",
            expected_cast_revision=accepted.accepted_cast.revision,
        )
        assert appearance["current"] is True
        assert appearance["label"] == "Beacon coat reference"
        assert store.media.list_imported_character_appearances(store.manifest.project_id)[0]["assetId"] == asset["id"]
        assert store.media.list_character_reference_decisions(store.manifest.project_id)["decisions"] == []

        selected = store.media.create_character_reference_decision(
            store.manifest.project_id, character_id="lin", primary_asset_id=asset["id"], complementary_asset_ids=[],
            expected_reference_revision=0, reviewer=None, notes=None, authority="cast",
        )
        assert selected["primaryAssetId"] == asset["id"]
        store.reopen_cast(CastReopenRequest(expected_cast_revision=1))
        assert store.media.list_imported_character_appearances(store.manifest.project_id)[0]["current"] is False
    finally:
        store.close()
