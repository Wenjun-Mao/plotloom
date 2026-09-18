"""F3A regression: art is source/map/graph/cast bound and text-first."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest, ArtBinding, ArtReopenRequest, ArtSaveRequest
from plotloom.cast_contracts import CastAcceptRequest, CastConsumerMapping
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.exceptions import NotFoundError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.operational_state import close_blockers
from plotloom.source_outline_contracts import (
    BranchOutcome, OutlineAcceptRequest, SectionChoice, SectionMap,
    SectionMapGraphInstallRequest, SectionMapSaveRequest, SourceMaterial,
    StorySection,
)


def _binding(revision: int = 1) -> ArtBinding:
    return ArtBinding(source_revision=revision, source_content_hash="a" * 64, outline_revision=1, outline_content_hash="b" * 64, section_map_revision=1, section_map_content_hash="c" * 64, graph_revision=1, graph_content_hash="d" * 64, cast_revision=1, cast_content_hash="e" * 64, section_ids=["opening", "ending-a", "ending-b"])


def _context(revision: int = 1) -> tuple[ArtBinding, dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    return _binding(revision), {"title": "Tide Light", "text": "Lin chooses the beacon or dock."}, {"source": "Tide Light", "episodes": []}, {"sections": [{"sectionId": "opening"}, {"sectionId": "ending-a"}, {"sectionId": "ending-b"}]}, {"source": "Tide Light", "summary": "Shared cast", "characters": [{"id": "C01", "name": "Lin"}]}


def _deliver(store: object, request: CreativeHandoffRequest) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    paths = exchange.write_package(request)
    package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"]); delivery.mkdir()
    render = "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth"
    art = canonical_json({"source": "Tide Light", "style": "realistic", "scenes": [{"id": "S01", "name": "航标室", "primary": True, "summary": "choice pressure", "anchors": [{"name": "铜灯", "desc": "old brass"}, {"name": "窗", "desc": "salted glass"}, {"name": "桌", "desc": "worn wood"}], "lighting": [{"state": "dawn", "prompt": "cold dawn through a window"}], "image": {"prompt": "empty beacon room", "negativePrompt": "people, human figures", "sheet": render, "tags": []}}], "props": [], "sectionUsage": [{"sectionId": "opening", "sceneIds": ["S01"], "propIds": []}, {"sectionId": "ending-a", "sceneIds": ["S01"], "propIds": []}, {"sectionId": "ending-b", "sceneIds": ["S01"], "propIds": []}]})
    report = b"<!doctype html><html><body>art report</body></html>"
    (delivery / "art.json").write_bytes(art); (delivery / "report.html").write_bytes(report)
    manifest = {"schemaVersion": 1, "jobId": request.job_id, "requestHash": package["requestHash"], "deliveryId": "art-fixture", "stage": "art", "candidate": {"filename": "art.json", "sha256": sha256(art).hexdigest()}, "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()}, "executorProvenance": {"codeRevision": "abcdef0", "skillVersion": "fixture", "skillHash": package["executionPin"]["specialistSkillHash"], "upstreamRevision": package["executionPin"]["upstreamRevision"], "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"}, "limitations": ["no images"]}
    (delivery / "completion.json").write_text(json.dumps(manifest))
    result = exchange.read_delivery(request); assert result is not None
    return result


def _deliver_stage(store: object, request: CreativeHandoffRequest, filename: str, candidate: dict[str, object], delivery_id: str) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    paths = exchange.write_package(request)
    package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"]); delivery.mkdir()
    content, report = canonical_json(candidate), b"<!doctype html><html><body>fixture report</body></html>"
    (delivery / filename).write_bytes(content); (delivery / "report.html").write_bytes(report)
    (delivery / "completion.json").write_text(json.dumps({"schemaVersion": 1, "jobId": request.job_id, "requestHash": package["requestHash"], "deliveryId": delivery_id, "stage": request.stage, "candidate": {"filename": filename, "sha256": sha256(content).hexdigest()}, "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()}, "executorProvenance": {"codeRevision": "abcdef0", "skillVersion": "fixture", "skillHash": package["executionPin"]["specialistSkillHash"], "upstreamRevision": package["executionPin"]["upstreamRevision"], "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"}, "limitations": ["fixture"]}))
    result = exchange.read_delivery(request); assert result is not None
    return result


def _prepare_art_context(store: object) -> ArtBinding:
    source = SourceMaterial(kind="synopsis", title="Tide Light", text="Lin chooses the beacon or dock.", attribution="fixture", rights_declaration="fixture", adaptation_intent="fixture")
    store.save_source_material(expected_source_revision=0, material=source)  # type: ignore[attr-defined]
    outline_request = CreativeHandoffRequest(job_id="ch_" + "o" * 32, project_id=store.manifest.project_id, section_id="story", stage="outline", expected_stage_revision=0, source=source.model_dump(mode="json", by_alias=True), input_artifacts={}, creative_brief="fixture")  # type: ignore[attr-defined]
    store.prepare_outline_candidate(outline_request)  # type: ignore[attr-defined]
    store.admit_outline_delivery(_deliver_stage(store, outline_request, "outline.json", {"source": "Tide Light", "episodes": []}, "outline-fixture"))  # type: ignore[attr-defined]
    state = store.accept_outline_candidate(OutlineAcceptRequest(job_id=outline_request.job_id, expected_source_revision=1, expected_outline_revision=0))  # type: ignore[attr-defined]
    assert state.source and state.accepted_outline
    mapping = SectionMap(sections=[StorySection(section_id="opening", title="Opening", summary="Lin chooses."), StorySection(section_id="ending-a", title="Beacon", summary="Beacon.", ending=True), StorySection(section_id="ending-b", title="Dock", summary="Dock.", ending=True)], choice=SectionChoice(choice_id="choose", section_id="opening", prompt="Where?", outcomes=[BranchOutcome(outcome_id="beacon", label="Beacon", consequence="Beacon.", ending_section_id="ending-a"), BranchOutcome(outcome_id="dock", label="Dock", consequence="Dock.", ending_section_id="ending-b")]))
    state = store.save_section_map(SectionMapSaveRequest(expected_section_map_revision=0, expected_source_revision=1, expected_outline_revision=1, expected_outline_content_hash=state.accepted_outline.content_hash, mapping=mapping))  # type: ignore[attr-defined]
    assert state.accepted_section_map
    store.install_section_map_graph(SectionMapGraphInstallRequest(expected_source_revision=1, expected_source_content_hash=state.source.content_hash, expected_outline_revision=1, expected_outline_content_hash=state.accepted_outline.content_hash, expected_section_map_revision=1, expected_section_map_content_hash=state.accepted_section_map.content_hash, expected_graph_revision=0))  # type: ignore[attr-defined]
    _candidate, cast_request = store.prepare_cast_candidate("ch_" + "c" * 32)  # type: ignore[attr-defined]
    ready_cast = store.admit_cast_delivery(_deliver_stage(store, cast_request, "cast.json", {"source": "Tide Light", "summary": "Lin chooses.", "characters": [{"id": "lin", "name": "Lin", "persona": {"motivation": "Choose", "appearance": "Rain coat", "arc": "Acts"}, "voice": {"timbre": "Calm"}}]}, "cast-fixture"))  # type: ignore[attr-defined]
    store.accept_cast_candidate(CastAcceptRequest(job_id=cast_request.job_id, expected_cast_revision=0, binding=ready_cast.binding, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")]))  # type: ignore[attr-defined]
    candidate, _request = store.prepare_art_candidate("ch_" + "z" * 32)  # type: ignore[attr-defined]
    store.cancel_art_candidate(candidate.job_id)  # type: ignore[attr-defined]
    return candidate.binding


def test_art_accept_reopen_cancel_and_currentness(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        binding = _prepare_art_context(store)
        # _prepare_art_context opens and cancels no art handoff; its binding is
        # from the actual accepted source/map/graph/cast revisions.
        candidate, request = store.prepare_art_candidate("ch_" + "a" * 32)
        assert request.input_artifacts.keys() == {"outline.json", "section-map.json", "cast.json"}
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
        prepared, _ = store.prepare_art_candidate("ch_" + "b" * 32)
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
