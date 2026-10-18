"""42 unique shots and five reference sets through real evidence owners."""
from contextlib import closing
import json
import os
import cProfile
from time import perf_counter
from fastapi.testclient import TestClient
from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_handoff_contracts import BulkHumanHandoffRequest
from plotloom.persistence.project.autopilot_handoff import review_material, record_handoff
from plotloom.project_storage.video_service import ProjectVideoService
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_batch_contracts import BatchSetup
from plotloom.video_batch_service import VideoBatchService
from tests.autopilot_image_fixtures import run_pack
from tests.bulk_material_pack_fixtures import realistic_pack_environment
from tests.test_bulk_material_handoff import bulk_observation
from tests.video_batch_fixtures import draft_for
from tests.video_storage_fixtures import FakeH3


def test_realistic_42_shot_source_complete_draft_and_read_work(tmp_path, monkeypatch, capsys):
    storage, registry, material_service, view, _calls, _text = realistic_pack_environment(tmp_path, monkeypatch)
    timings = {}
    try:
        run_pack(storage, material_service, view)
        client = TestClient(create_project_folder_authoring_app(storage))
        for label in ("awaiting-first", "awaiting-repeat"):
            start = perf_counter()
            response = client.get(f"/api/v2/projects/{view.project_id}/autopilot/review")
            assert response.status_code == 200, response.text
            timings[label] = perf_counter() - start
        start = perf_counter()
        if os.environ.get("PLOTLOOM_QUALIFICATION_PROFILE"):
            from plotloom.api import project_folder_autopilot
            original_handoff = project_folder_autopilot.record_handoff
            def profiled_handoff(store, request):
                profile = cProfile.Profile()
                try: return profile.runcall(original_handoff, store, request)
                finally: profile.dump_stats(os.environ["PLOTLOOM_QUALIFICATION_PROFILE"])
            monkeypatch.setattr(project_folder_autopilot, "record_handoff", profiled_handoff)
        response = client.post(f"/api/v2/projects/{view.project_id}/autopilot/handoff", json=bulk_observation(response.json()))
        assert response.status_code == 200, response.text
        timings["confirmation-commit-response"] = perf_counter() - start
        with closing(storage.projects.open(view.project_id)) as store:
            assert len(review_material(store)["bundle"]["frames"]) == 42
        provider = FakeH3()
        video = ProjectVideoService(storage.application, provider, MiniMaxH3GatewayAdapter())
        service = VideoBatchService(storage, registry, video)
        batch = service.setup(view.project_id, BatchSetup(profileId="minimax_h3_quality8_landscape_832x480_v2", aspectPolicy="cover_center_crop"))
        assert not batch["manifest"]["blockers"], batch["manifest"]["blockers"]
        assert len(batch["manifest"]["scopeShotIds"]) == len(batch["manifest"]["targets"]) == 42
        assert batch["manifest"]["requestedSeconds"] == 210
        host = registry._codex_exec_test_host
        original_candidate = host.candidate_factory
        host.candidate_factory = lambda store, request: draft_for(batch).model_dump(mode="json", by_alias=True) if request.stage == "video-directions" else original_candidate(store, request)
        before = len(host.calls)
        service.draft(view.project_id, batch["revision"])
        for _ in range(4):
            service.step(view.project_id)
            batch = service.current(view.project_id)
            if batch["state"] in {"ready", "blocked"}: break
        assert batch["state"] == "ready", batch["execution"].get("error")
        assert len(host.calls) == before + 1 and not provider.submits
        assert all(target["compiledPrompt"] and "reviewedEnglish" not in target["directions"] for target in batch["manifest"]["targets"])
        from plotloom.project_storage.creative_evidence_inventory import creative_evidence_paths
        with closing(storage.projects.open(view.project_id)) as store:
            assert creative_evidence_paths(store.home, store.database_path)
        start = perf_counter()
        evidence = client.get(f"/api/v2/projects/{view.project_id}/autopilot/delivery-evidence")
        assert evidence.status_code == 200, evidence.text
        timings["handoff-consolidated-metadata"] = perf_counter() - start
        assert len(evidence.json()["images"]) == 42
        (tmp_path / "metrics.json").write_text(json.dumps(timings, sort_keys=True))
        with capsys.disabled():
            print("BATCH_42_METRICS " + json.dumps(timings, sort_keys=True), flush=True)
    finally:
        material_service.close()
