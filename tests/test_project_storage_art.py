"""F3A regression: art is source/map/graph/cast bound and text-first."""

from __future__ import annotations

from tests.graph_draft_fixtures import graph_map_save_request, graph_draft_revision

import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest, ArtBinding, ArtReopenRequest, ArtSaveRequest
from plotloom.script_contracts import ScriptAcceptRequest, ScriptReopenRequest, ScriptSectionSaveRequest
from plotloom.cast_contracts import CastAcceptRequest, CastConsumerMapping
from plotloom.conformance import FIXED_CHINESE_BRIEF
from tests.cast_style_fixtures import style_fixture
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.source_structures import planned_structure
from plotloom.outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from plotloom.exceptions import NotFoundError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.project_storage.operational_state import ProjectBusyError
from plotloom.project_storage.operational_state import close_blockers
from plotloom.source_outline_contracts import (
    BranchOutcome, OutlineAcceptRequest, SectionChoice, SectionMap,
    SectionMapGraphInstallRequest, SourceMaterial,
    StorySection,
)


def _binding(revision: int = 1) -> ArtBinding:
    return ArtBinding(source_revision=revision, source_content_hash="a" * 64, outline_revision=1, outline_content_hash="b" * 64, section_map_revision=1, section_map_content_hash="c" * 64, graph_revision=1, graph_content_hash="d" * 64, cast_revision=1, cast_content_hash="e" * 64, section_ids=["opening", "ending-a", "ending-b"])


def _context(revision: int = 1) -> tuple[ArtBinding, dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    return _binding(revision), {"title": "Tide Light", "text": "Lin chooses the beacon or dock."}, {"source": "Tide Light", "episodes": []}, {"sections": [{"sectionId": "opening"}, {"sectionId": "ending-a"}, {"sectionId": "ending-b"}]}, {"source": "Tide Light", "summary": "Shared cast", "characters": [{"id": "C01", "name": "Lin"}]}


def _deliver(store: object, request: CreativeHandoffRequest) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    pin = store.creative_handoff_execution_pin(request)  # type: ignore[attr-defined]
    paths = exchange.write_package(request, pin)
    package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"]); delivery.mkdir()
    render = "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth"
    art = canonical_json({"source": "Tide Light", "style": "realistic", "scenes": [{"id": "S01", "name": "航标室", "primary": True, "summary": "choice pressure", "anchors": [{"name": "铜灯", "desc": "old brass"}, {"name": "窗", "desc": "salted glass"}, {"name": "桌", "desc": "worn wood"}], "lighting": [{"state": "dawn", "prompt": "cold dawn through a window"}], "image": {"prompt": render + ", empty beacon room", "negativePrompt": "people, human figures", "sheet": render, "tags": []}}], "props": [], "sectionUsage": [{"sectionId": section["sectionId"], "sceneIds": ["S01"], "propIds": []} for section in request.input_artifacts["section-map.json"]["sections"]]})
    report = b"<!doctype html><html><body>art report</body></html>"
    (delivery / "art.json").write_bytes(art); (delivery / "report.html").write_bytes(report)
    manifest = {"schemaVersion": 1, "jobId": request.job_id, "requestHash": package["requestHash"], "deliveryId": "art-fixture", "stage": "art", "candidate": {"filename": "art.json", "sha256": sha256(art).hexdigest()}, "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()}, "executorProvenance": {"codeRevision": "abcdef0", "skillVersion": "fixture", "skillHash": package["executionPin"]["specialistSkillHash"], "upstreamRevision": package["executionPin"]["upstreamRevision"], "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"}, "limitations": ["no images"]}
    (delivery / "completion.json").write_text(json.dumps(manifest))
    result = exchange.read_delivery(request, pin); assert result is not None
    return result


def _deliver_stage(store: object, request: CreativeHandoffRequest, filename: str, candidate: dict[str, object], delivery_id: str) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    pin = store.creative_handoff_execution_pin(request)  # type: ignore[attr-defined]
    paths = exchange.write_package(request, pin)
    package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"]); delivery.mkdir()
    content, report = canonical_json(candidate), b"<!doctype html><html><body>fixture report</body></html>"
    (delivery / filename).write_bytes(content); (delivery / "report.html").write_bytes(report)
    (delivery / "completion.json").write_text(json.dumps({"schemaVersion": 1, "jobId": request.job_id, "requestHash": package["requestHash"], "deliveryId": delivery_id, "stage": request.stage, "candidate": {"filename": filename, "sha256": sha256(content).hexdigest()}, "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()}, "executorProvenance": {"codeRevision": "abcdef0", "skillVersion": "fixture", "skillHash": package["executionPin"]["specialistSkillHash"], "upstreamRevision": package["executionPin"]["upstreamRevision"], "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"}, "limitations": ["fixture"]}))
    result = exchange.read_delivery(request, pin); assert result is not None
    return result


def _prepare_art_context(store: object, structure_factory=None) -> ArtBinding:
    project = store.project()
    if structure_factory is None:
        store.update_brief(project.brief.model_copy(update={"decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0}), expected_revision=project.revision)
    source = SourceMaterial(kind="synopsis", title="Tide Light", text="Lin chooses the beacon or dock.", attribution="fixture", rights_declaration="fixture", adaptation_intent="fixture")
    store.save_source_material(expected_source_revision=0, material=source)  # type: ignore[attr-defined]
    outline_request = CreativeHandoffRequest(job_id="ch_" + "o" * 32, project_id=store.manifest.project_id, section_id="story", stage="outline", expected_stage_revision=0, source=source.model_dump(mode="json", by_alias=True), input_artifacts={OUTLINE_SETTINGS_FILENAME: outline_settings(store.project().brief), "story-topology.json": planned_structure(store.manifest.project_id, store.project().brief).model_dump(mode="json", by_alias=True)}, creative_brief="fixture")  # type: ignore[attr-defined]
    store.prepare_outline_candidate(outline_request)  # type: ignore[attr-defined]
    store.admit_outline_delivery(_deliver_stage(store, outline_request, "outline.json", {"source": "Tide Light", "episodes": []}, "outline-fixture"))  # type: ignore[attr-defined]
    state = store.accept_outline_candidate(OutlineAcceptRequest(job_id=outline_request.job_id, expected_source_revision=1, expected_outline_revision=0))  # type: ignore[attr-defined]
    assert state.source and state.accepted_outline
    mapping = SectionMap(
        seed_topology=planned_structure(store.manifest.project_id, store.project().brief),
        topology_origin="author",
        topology={"startNodeId": "opening",
            "nodes": [{"id": "opening", "kind": "start"}, {"id": "choose", "kind": "decision"}, {"id": "ending-a", "kind": "ending"}, {"id": "ending-b", "kind": "ending"}],
            "edges": [{"id": key, "sourceNodeId": source_id, "targetNodeId": target, "kind": kind, "stateEffects": {}, "entityStateEffects": []} for key, source_id, target, kind in [("to-choice", "opening", "choose", "continuation"), ("beacon", "choose", "ending-a", "choice"), ("dock", "choose", "ending-b", "choice")]], "joins": []},
        sections=[StorySection(section_id="opening", title="Opening", summary="Lin chooses.", footage_mode="footage"), StorySection(section_id="choose", title="Choose", summary="Lin chooses a route.", footage_mode="route_only"), StorySection(section_id="ending-a", title="Beacon", summary="Beacon.", ending=True, footage_mode="footage"), StorySection(section_id="ending-b", title="Dock", summary="Dock.", ending=True, footage_mode="footage")],
        choices=[SectionChoice(choice_id="choose", section_id="choose", prompt="Where?", outcomes=[BranchOutcome(outcome_id="beacon", label="Beacon", consequence="Beacon.", ending_section_id="ending-a"), BranchOutcome(outcome_id="dock", label="Dock", consequence="Dock.", ending_section_id="ending-b")])],
        join_reconciliations={},
    )
    if structure_factory is not None:
        mapping = structure_factory(store)
    state = store.save_section_map(graph_map_save_request(store, expected_section_map_revision=0, expected_source_revision=1, expected_outline_revision=1, expected_outline_content_hash=state.accepted_outline.content_hash, mapping=mapping))  # type: ignore[attr-defined]
    assert state.accepted_section_map
    store.install_section_map_graph(SectionMapGraphInstallRequest(expected_source_revision=1, expected_source_content_hash=state.source.content_hash, expected_outline_revision=1, expected_outline_content_hash=state.accepted_outline.content_hash, expected_section_map_revision=1, expected_section_map_content_hash=state.accepted_section_map.content_hash, expected_graph_revision=0, expected_graph_draft_revision=graph_draft_revision(store)))  # type: ignore[attr-defined]
    _candidate, cast_request = store.prepare_cast_candidate("ch_" + "c" * 32, render_style="realistic")  # type: ignore[attr-defined]
    cast = style_fixture({"source": "Tide Light", "summary": "Lin chooses.", "characters": [{"id": "lin", "name": "Lin", "reviewNotes": {"sourceNotes": "Rain coat is proposed", "performanceGuidance": ""}, "persona": {"personality": ["Careful"], "motivation": "Choose", "appearance": "Rain coat", "arc": "Acts"}, "voice": {"timbre": "Calm"}}]}, cast_request.input_artifacts["cast-style-contract.json"])
    ready_cast = store.admit_cast_delivery(_deliver_stage(store, cast_request, "cast.json", cast, "cast-fixture"))  # type: ignore[attr-defined]
    store.accept_cast_candidate(CastAcceptRequest(job_id=cast_request.job_id, expected_cast_revision=0, binding=ready_cast.binding, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")]))  # type: ignore[attr-defined]
    candidate, _request = store.prepare_art_candidate("ch_" + "z" * 32, render_style="realistic")  # type: ignore[attr-defined]
    store.cancel_art_candidate(candidate.job_id)  # type: ignore[attr-defined]
    return candidate.binding


def test_art_accept_reopen_cancel_and_currentness(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        binding = _prepare_art_context(store)
        # _prepare_art_context opens and cancels no art handoff; its binding is
        # from the actual accepted source/map/graph/cast revisions.
        candidate, request = store.prepare_art_candidate("ch_" + "a" * 32, render_style="realistic")
        assert request.input_artifacts.keys() == {"outline.json", "section-map.json", "cast.json", "art-style-contract.json"}
        assert "F3B" in request.creative_brief
        assert "art_publication_active" in close_blockers(store)
        client = TestClient(create_project_folder_authoring_app(storage))
        recovered = client.get(f"/api/v2/projects/{store.manifest.project_id}/art/candidates/{candidate.job_id}/handoff")
        assert recovered.status_code == 200
        assert recovered.json()["jobId"] == candidate.job_id
        assert request.job_id in recovered.json()["assignment"]
        ready = store.admit_art_delivery(_deliver(store, request))
        assert ready.art and ready.art["scenes"][0]["id"] == "S01"
        accepted = store.accept_art_candidate(ArtAcceptRequest(job_id=request.job_id, expected_art_revision=0, binding=binding, art=ready.art))
        assert accepted.accepted_art and accepted.accepted_art.revision == 1
        store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        edited = dict(ready.art or {}); edited["scenes"] = [dict(edited["scenes"][0], summary="edited text only")]
        saved = store.save_reopened_art(ArtSaveRequest(expected_art_revision=1, binding=binding, art=edited))
        assert saved.accepted_art and saved.accepted_art.revision == 2
        assert "does not describe the current accepted revision" in store.art_candidate_report(request.job_id)
        prepared, _ = store.prepare_art_candidate("ch_" + "b" * 32, render_style="realistic")
        store.cancel_art_candidate(prepared.job_id)
        with pytest.raises(NotFoundError, match="unavailable"):
            store.art_candidate_request(prepared.job_id)
        assert store.art_state().status == "accepted"
    finally:
        store.close()


def test_art_routes_are_user_reachable(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF); project_id = store.manifest.project_id
    store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    response = client.get(f"/api/v2/projects/{project_id}/art")
    assert response.status_code == 200
    assert response.json() == {"candidate": None, "acceptedArt": None, "status": "missing", "staleReasons": []}


def _reference_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), (42, 72, 84)).save(output, format="PNG")
    return output.getvalue()


def _write_art_reference_delivery(delivery_path: Path, proposal: dict[str, object]) -> None:
    request = proposal["request"]
    assert isinstance(request, dict)
    request_hash = proposal["requestHash"]
    assert isinstance(request_hash, str)
    content = _reference_png()
    provenance = {"codeRevision": "a" * 40, "skillVersion": "plotloom-image-specialist.v3", "skillHash": "b" * 64}
    delivery_path.mkdir(exist_ok=True)
    (delivery_path / "outputs").mkdir()
    (delivery_path / "outputs" / "study.png").write_bytes(content)
    (delivery_path / "executor-pin.json").write_text(json.dumps({"jobId": proposal["id"], "requestHash": request_hash, "executionContract": "codex_specialist.v2", **provenance}))
    (delivery_path / "completion.json").write_text(json.dumps({
        "schemaVersion": 2, "jobId": proposal["id"], "requestHash": request_hash, "deliveryId": "art-study-001",
        "actualPrompt": "Cinematic realism environment study, no people and no hands.",
        "outputs": [{"filename": "study.png", "sha256": sha256(content).hexdigest(), "role": "art_reference"}],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "art-reference-fixture", "available": True},
        "executorProvenance": provenance, "limitations": ["fixture bytes only"],
    }))


def test_art_reference_study_browser_lifecycle_persists_and_stales(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate("ch_" + "r" * 32, render_style="realistic")
        ready = store.admit_art_delivery(_deliver(store, request))
        accepted = store.accept_art_candidate(ArtAcceptRequest(job_id=candidate.job_id, expected_art_revision=0, binding=binding, art=ready.art))
        assert accepted.accepted_art
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    prepared = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals", json={"subjectType": "scene", "subjectId": "S01", "renderDirection": "Cinematic realism, no people."})
    assert prepared.status_code == 201, prepared.text
    proposal = prepared.json()["proposal"]
    copied = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/copy")
    assert copied.status_code == 200, copied.text
    assert "Cinematic realism" in proposal["request"]["frozenSnapshot"]["renderDirection"]
    _write_art_reference_delivery(Path(copied.json()["deliveryPath"]), proposal)
    delivered = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/refresh")
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["state"] == "accepted"
    assert delivered.json()["candidates"][0]["role"] == "art_reference"
    reopened = storage.projects.open(project_id)
    reopened.close()
    visible = client.get(f"/api/v2/projects/{project_id}/art-reference-proposals")
    assert visible.status_code == 200
    assert visible.json()["proposals"][0]["current"] is True
    # Accepted-art edits keep historic evidence but visibly invalidate its study.
    edit_store = storage.projects.open(project_id)
    try:
        edit_store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        edited = dict(edit_store.art_state().accepted_art.art)  # type: ignore[union-attr]
        edited["scenes"] = [dict(edited["scenes"][0], summary="changed accepted art")]
        edit_store.save_reopened_art(ArtSaveRequest(expected_art_revision=1, binding=binding, art=edited))
    finally:
        edit_store.close()
    stale = client.get(f"/api/v2/projects/{project_id}/art-reference-proposals")
    assert stale.json()["proposals"][0]["current"] is False
    later = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals", json={"subjectType": "scene", "subjectId": "S01", "renderDirection": "Cinematic realism, no people."})
    assert later.status_code == 201, later.text
    active = later.json()["proposal"]
    copied_late = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{active['id']}/copy")
    assert copied_late.status_code == 200, copied_late.text
    cancellation = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{active['id']}/cancel", json={"reason": "Operator ended the package before delivery."})
    assert cancellation.status_code == 200
    _write_art_reference_delivery(Path(copied_late.json()["deliveryPath"]), active)
    late = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{active['id']}/refresh")
    assert late.status_code == 200, late.text
    assert late.json()["state"] == "inapplicable"
    assert late.json()["candidates"] == []


def test_art_reference_decisions_are_explicit_cas_bound_historical_and_stale(tmp_path: Path) -> None:
    """F3B selection is a local persistence contract, not a generation claim.

    The retained test-only delivery helper supplies isolated mocked bytes. It
    exercises the decision admission boundary without presenting fixture
    provenance as real ImageGen evidence or invoking a provider.
    """

    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate("ch_" + "d" * 32, render_style="realistic")
        ready = store.admit_art_delivery(_deliver(store, request))
        accepted = store.accept_art_candidate(ArtAcceptRequest(
            job_id=candidate.job_id, expected_art_revision=0, binding=binding, art=ready.art,
        ))
        assert accepted.accepted_art and accepted.accepted_art.revision == 1
    finally:
        store.close()

    client = TestClient(create_project_folder_authoring_app(storage))

    def deliver_study(direction: str) -> dict[str, object]:
        prepared = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals", json={
            "subjectType": "scene", "subjectId": "S01", "renderDirection": direction,
        })
        assert prepared.status_code == 201, prepared.text
        proposal = prepared.json()["proposal"]
        copied = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/copy")
        assert copied.status_code == 200, copied.text
        _write_art_reference_delivery(Path(copied.json()["deliveryPath"]), proposal)
        delivered = client.post(f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/refresh")
        assert delivered.status_code == 200, delivered.text
        assert delivered.json()["state"] == "accepted"
        candidate = delivered.json()["candidates"][0]
        return {"proposal": proposal, "assetId": candidate["assetId"], "assetHash": candidate["asset"]["originalHash"]}

    first = deliver_study("Fixture study one; no people.")
    second = deliver_study("Fixture study two; no people.")
    assert first["assetId"] != second["assetId"]
    initially = client.get(f"/api/v2/projects/{project_id}/art-reference-decisions")
    assert initially.status_code == 200
    assert initially.json() == {"states": [], "decisions": []}

    chosen = client.post(f"/api/v2/projects/{project_id}/art-reference-decisions", json={
        "subjectType": "scene", "subjectId": "S01", "assetId": first["assetId"], "expectedReferenceRevision": 0,
    })
    assert chosen.status_code == 201, chosen.text
    assert chosen.json()["stateRevision"] == 1
    assert chosen.json()["current"] is True
    assert chosen.json()["acceptedArtRevision"] == 1
    assert chosen.json()["assetHash"] == first["assetHash"]

    stale_cas = client.post(f"/api/v2/projects/{project_id}/art-reference-decisions", json={
        "subjectType": "scene", "subjectId": "S01", "assetId": second["assetId"], "expectedReferenceRevision": 0,
    })
    assert stale_cas.status_code == 409
    wrong_subject = client.post(f"/api/v2/projects/{project_id}/art-reference-decisions", json={
        "subjectType": "prop", "subjectId": "P01", "assetId": second["assetId"], "expectedReferenceRevision": 0,
    })
    assert wrong_subject.status_code == 409  # P01 is not an accepted prop subject.

    replacement = client.post(f"/api/v2/projects/{project_id}/art-reference-decisions", json={
        "subjectType": "scene", "subjectId": "S01", "assetId": second["assetId"], "expectedReferenceRevision": 1,
    })
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["stateRevision"] == 2
    visible = client.get(f"/api/v2/projects/{project_id}/art-reference-decisions").json()
    assert visible["states"] == [{
        "subjectType": "scene", "subjectId": "S01", "revision": 2,
        "activeDecisionId": replacement.json()["id"], "current": True,
    }]
    assert [item["assetId"] for item in visible["decisions"]] == [second["assetId"], first["assetId"]]
    assert [item["current"] for item in visible["decisions"]] == [True, False]

    # A normal reopen preserves the state head and append-only history.
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert client.get(f"/api/v2/projects/{project_id}/art-reference-decisions").json()["states"][0]["revision"] == 2

    # Reopening and editing accepted art invalidates, but never deletes or
    # redirects, the old subject decision.
    edited_store = storage.projects.open(project_id)
    try:
        edited_store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        edited = dict(edited_store.art_state().accepted_art.art)  # type: ignore[union-attr]
        edited["scenes"] = [dict(edited["scenes"][0], summary="reference context changed")]
        edited_store.save_reopened_art(ArtSaveRequest(expected_art_revision=1, binding=binding, art=edited))
    finally:
        edited_store.close()
    stale = client.get(f"/api/v2/projects/{project_id}/art-reference-decisions").json()
    assert stale["states"][0]["current"] is False
    assert [item["current"] for item in stale["decisions"]] == [False, False]
    assert len(stale["decisions"]) == 2


def _pilot_script() -> dict[str, object]:
    """A valid tiny three-section F4 fixture, not a second graph representation."""

    def episode(number: int) -> dict[str, object]:
        return {
            "ep": number, "targetSeconds": 25, "hook": f"Section {number} begins in motion", "cliff": f"Section {number} leaves a consequence open", "hookBeat": [1, 1], "beatsClaimed": [],
            "scenes": [{"sceneId": "S01", "lighting": "dawn", "characters": [], "props": [], "flow": [{"action": f"Lin crosses the beacon room, action {index}."} for index in range(10)]}],
        }

    return {"source": "Tide Light", "sectionBindings": [{"sectionId": "opening", "episode": 1}, {"sectionId": "ending-a", "episode": 2}, {"sectionId": "ending-b", "episode": 3}], "episodes": [episode(1), episode(2), episode(3)]}


def test_f4_script_accepts_whole_pilot_preserves_scoped_edits_and_rejects_late_delivery(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate("ch_" + "q" * 32, render_style="realistic")
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=art_candidate.job_id, expected_art_revision=0, binding=binding, art=art_ready.art))
        candidate, request = store.prepare_script_candidate("ch_" + "w" * 32)
        assert "script_publication_active" in close_blockers(store)
        ready = store.admit_script_delivery(_deliver_stage(store, request, "script.json", _pilot_script(), "script-fixture"))
        accepted = store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0, binding=ready.binding, script=ready.script))
        assert accepted.accepted_script and accepted.accepted_script.revision == 1
        original_ending = accepted.accepted_script.script["episodes"][2]
        store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
        opening = dict(accepted.accepted_script.script["episodes"][0]); opening["cliff"] = "Opening edit keeps its own consequence"
        saved = store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=1, binding=accepted.accepted_script.binding, section_id="opening", episode=opening))
        assert saved.accepted_script and saved.accepted_script.script["episodes"][2] == original_ending
        pending, pending_request = store.prepare_script_candidate("ch_" + "v" * 32)
        store.cancel_script_candidate(pending.job_id)
        with pytest.raises(Exception, match="current prepared|unavailable|cancelled"):
            store.admit_script_delivery(_deliver_stage(store, pending_request, "script.json", _pilot_script(), "late-script"))
    finally:
        store.close()
    restarted = storage.projects.open(project_id)
    try:
        assert restarted.script_state().accepted_script and restarted.script_state().accepted_script.revision == 2
    finally:
        restarted.close()
    final_store = storage.projects.open(project_id)
    try:
        assert "art_reference_publication_active" not in close_blockers(final_store)
    finally:
        final_store.close()


def test_f4_script_admission_freezes_exact_mapping_route_budget_and_target_currentness(tmp_path: Path) -> None:
    """F4 timing constrains routes, not an equal split or three-episode total."""

    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180}))
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate("ch_" + "t" * 32, render_style="realistic")
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=art_candidate.job_id, expected_art_revision=0, binding=binding, art=art_ready.art))
        candidate, request = store.prepare_script_candidate("ch_" + "x" * 32)
        assert len(candidate.binding.route_budget_hash) == 64
        assert "sectionDurationCaps" not in request.input_artifacts["script-admission.json"]
        assert request.input_artifacts["script-admission.json"]["routeBudgetHash"] == candidate.binding.route_budget_hash
        assert candidate.binding.complete_route_section_ids == [["opening", "choose", "ending-a"], ["opening", "choose", "ending-b"]]
        assert request.input_artifacts["script-admission.json"]["targetPlaythroughSeconds"] == 180
        assert "aggregate duration across mutually exclusive endings as product-inapplicable" in request.creative_brief
        assert "frozen complete-route maximum remains applicable" in request.creative_brief

        swapped = _pilot_script()
        swapped["sectionBindings"] = [
            {"sectionId": "opening", "episode": 2},
            {"sectionId": "ending-a", "episode": 1},
            {"sectionId": "ending-b", "episode": 3},
        ]
        with pytest.raises(ValueError, match="exactly match the frozen"):
            store.admit_script_delivery(_deliver_stage(store, request, "script.json", swapped, "swapped-script"))
    finally:
        store.close()


def test_f4_script_target_change_stales_prepared_delivery(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180}))
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate("ch_" + "n" * 32, render_style="realistic")
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=art_candidate.job_id, expected_art_revision=0, binding=binding, art=art_ready.art))
        _candidate, request = store.prepare_script_candidate("ch_" + "m" * 32)
        current = store.project()
        store.update_brief(current.brief.model_copy(update={"target_playthrough_seconds": 181}), expected_revision=current.revision)
        with pytest.raises(Exception, match="stale"):
            store.admit_script_delivery(_deliver_stage(store, request, "script.json", _pilot_script(), "stale-target"))
    finally:
        store.close()


def test_f4_script_target_change_stales_ready_candidate_acceptance(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180}))
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate("ch_" + "g" * 32, render_style="realistic")
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=art_candidate.job_id, expected_art_revision=0, binding=binding, art=art_ready.art))
        candidate, script_request = store.prepare_script_candidate("ch_" + "h" * 32)
        ready = store.admit_script_delivery(_deliver_stage(store, script_request, "script.json", _pilot_script(), "ready-before-target-change"))
        current = store.project()
        store.update_brief(current.brief.model_copy(update={"target_playthrough_seconds": 181}), expected_revision=current.revision)
        with pytest.raises(Exception, match="changed before acceptance"):
            store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0, binding=ready.binding, script=ready.script))
    finally:
        store.close()


def test_f4_prepared_script_blocks_snapshot_until_cancel_and_late_delivery_stays_refused(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate("ch_" + "p" * 32, render_style="realistic")
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=art_candidate.job_id, expected_art_revision=0, binding=binding, art=art_ready.art))
        candidate, request = store.prepare_script_candidate("ch_" + "y" * 32)
    finally:
        store.close()

    with pytest.raises(ProjectBusyError, match="script_publication_active"):
        storage.recovery.create_snapshot(project_id)
    opened = storage.projects.open(project_id)
    try:
        opened.cancel_script_candidate(candidate.job_id)
        with pytest.raises(Exception, match="current prepared|unavailable|cancelled"):
            opened.admit_script_delivery(_deliver_stage(opened, request, "script.json", _pilot_script(), "late-script"))
    finally:
        opened.close()
    assert storage.recovery.create_snapshot(project_id).status == "complete"


def _accepted_f4_script(store: object, structure_factory=None) -> None:
    binding = _prepare_art_context(store, structure_factory)
    art_candidate, art_request = store.prepare_art_candidate("ch_" + "k" * 32, render_style="realistic")  # type: ignore[attr-defined]
    art_ready = store.admit_art_delivery(_deliver(store, art_request))  # type: ignore[attr-defined]
    store.accept_art_candidate(ArtAcceptRequest(job_id=art_candidate.job_id, expected_art_revision=0, binding=binding, art=art_ready.art))  # type: ignore[attr-defined]
    candidate, request = store.prepare_script_candidate("ch_" + "l" * 32)  # type: ignore[attr-defined]
    script = _pilot_script()
    if structure_factory is not None:
        from copy import deepcopy
        script["sectionBindings"] = [item.model_dump(mode="json", by_alias=True) for item in candidate.binding.section_bindings]
        template = script["episodes"][0]
        script["episodes"] = [dict(deepcopy(template), ep=item.episode) for item in candidate.binding.section_bindings]
    ready = store.admit_script_delivery(_deliver_stage(store, request, "script.json", script, "script-for-storyboard"))  # type: ignore[attr-defined]
    store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0, binding=ready.binding, script=ready.script))  # type: ignore[attr-defined]


def test_format_10_folder_is_refused_with_reset_required_guidance(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, manifest_path = store.manifest.project_id, store.home / "project.json"
    store.close()
    manifest = json.loads(manifest_path.read_text())
    manifest["formatVersion"] = 10
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ProjectStorageCorruptionError, match="format 10 or older is unsupported by F5A; reset required"):
        storage.projects.open(project_id)
