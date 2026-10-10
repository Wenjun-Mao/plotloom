from __future__ import annotations

from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.runtime import build_runtime_app
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage
from tests.production_bridge_fixtures import _source_shaped_review_board
from tests.production_bridge_intent_fixtures import (
    FakeAdapter,
    FakeResolver,
    _wait_for_job,
)


def test_runtime_http_fake_inference_review_edit_save_then_explicit_install(
    tmp_path: Path,
) -> None:
    adapter = FakeAdapter(held=True)
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text(
        "<main>Fake bridge integration</main>", encoding="utf-8"
    )
    settings = PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static,
        text_auth_mode="none",
    )
    app = build_runtime_app(
        settings,
        text_provider_resolver=FakeResolver(adapter),
        bridge_simulation_label="模拟数据 · 假模型演示",
    )
    with TestClient(app) as client:
        storage = app.state.project_folder_storage
        with closing(
            storage.projects.create(
                FIXED_CHINESE_BRIEF.model_copy(
                    update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
                )
            )
        ) as store:
            _accepted_f4_script(store)
            candidate, request = store.prepare_storyboard_review_candidate(
                "ch_" + "b" * 32
            )
            ready = store.admit_storyboard_review_delivery(
                _deliver_stage(
                    store,
                    request,
                    "storyboard.json",
                    _source_shaped_review_board(),
                    "http-fake",
                )
            )
            store.accept_storyboard_review_candidate(
                StoryboardReviewAcceptRequest(
                    job_id=candidate.job_id,
                    expected_review_revision=0,
                    binding=ready.binding,
                )
            )
            project_id = store.manifest.project_id
        base = f"/api/v2/projects/{project_id}/production-bridge"
        prepared = client.post(
            f"{base}/proposals", json=client.get(base).json()["preparation"]["request"]
        )
        assert prepared.status_code == 200, prepared.text
        assert prepared.json()["simulationLabel"] == "模拟数据 · 假模型演示"
        assert prepared.json()["intentGeneration"] == {"status": "available"}
        first = prepared.json()["proposal"]
        assert first["installable"] is False
        with closing(storage.projects.open(project_id)) as store:
            stored_before = store.production_bridge_state().model_dump(
                mode="json", by_alias=True
            )
        reread = client.get(base)
        assert reread.json()["intentGeneration"] == {"status": "available"}
        assert reread.json()["proposal"] == first
        with closing(storage.projects.open(project_id)) as store:
            stored_after = store.production_bridge_state().model_dump(
                mode="json", by_alias=True
            )
        assert stored_after == stored_before
        assert "intentGeneration" not in stored_after
        assert "intentGeneration" not in first
        refused = client.post(
            f"{base}/accept",
            json={
                "expectedProposalRevision": first["revision"],
                "expectedContentHash": first["contentHash"],
            },
        )
        assert refused.status_code in {400, 409, 422}
        generated = client.post(
            f"{base}/intent-jobs",
            json={
                "expectedProposalRevision": first["revision"],
                "expectedContentHash": first["contentHash"],
            },
        )
        assert generated.status_code == 202, generated.text
        job_id = generated.json()["intentJob"]["id"]
        assert adapter.started.wait(8)
        running = client.get(base)
        assert (
            running.status_code == 200
            and running.json()["intentJob"]["status"] == "dispatched"
        )
        assert running.json()["simulationLabel"] == "模拟数据 · 假模型演示"
        _wait_for_job(app.state.bridge_intent_service, adapter, job_id)
        inferred = client.get(base)
        assert inferred.status_code == 200, inferred.text
        proposal = inferred.json()["proposal"]
        assert inferred.json()["intentJob"]["status"] == "ready"
        assert proposal["intentPackage"]["suggestionOrigin"] == "model_inference.v1"
        updates = [
            {"id": entry["id"], "text": "作者确认并修改：" + entry["text"]}
            for entry in proposal["intentPackage"]["entries"]
        ]
        saved = client.put(
            f"{base}/proposals/intent",
            json={
                "expectedProposalRevision": proposal["revision"],
                "expectedContentHash": proposal["contentHash"],
                "entries": updates,
            },
        )
        assert saved.status_code == 200, saved.text
        revised = saved.json()["proposal"]
        assert revised["intentPackage"]["reviewState"] == "author_saved"
        assert revised["intentPackage"]["suggestionOrigin"] == "model_inference.v1"
        assert revised["intentPackage"]["provenance"]["jobId"] == job_id
        for prior, current in zip(
            proposal["intentPackage"]["entries"], revised["intentPackage"]["entries"]
        ):
            assert current["sourceExcerpt"] == prior["sourceExcerpt"]
            assert current["suggestedText"] == prior["suggestedText"]
            assert current["text"] != current["suggestedText"]
        reloaded = client.get(base).json()["proposal"]
        assert reloaded["intentPackage"] == revised["intentPackage"]
        stale_accept = client.post(
            f"{base}/accept",
            json={
                "expectedProposalRevision": proposal["revision"],
                "expectedContentHash": proposal["contentHash"],
            },
        )
        assert stale_accept.status_code in {400, 409, 422}
        presentation = revised["presentation"]
        reviewed = client.put(
            f"{base}/proposals/presentation",
            json={
                "expectedProposalRevision": revised["revision"],
                "expectedContentHash": revised["contentHash"],
                "sourceHash": presentation["sourceHash"],
                "reviewedComplete": True,
                "entries": [
                    {
                        "id": source["id"],
                        "spans": [
                            {
                                "start": 0,
                                "end": len(source["sourceText"]),
                                "role": "dialogue"
                                if source["kind"] == "dialogue"
                                else "physical",
                                "rendering": ""
                                if source["kind"] == "dialogue"
                                else source["sourceText"],
                            }
                        ],
                    }
                    for source in presentation["sources"]
                ],
            },
        )
        assert reviewed.status_code == 200, reviewed.text
        revised = reviewed.json()["proposal"]
        accepted = client.post(
            f"{base}/accept",
            json={
                "expectedProposalRevision": revised["revision"],
                "expectedContentHash": revised["contentHash"],
            },
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "accepted"
        assert accepted.json()["simulationLabel"] == "模拟数据 · 假模型演示"
