"""An OS-open failure cannot undo an exported, queued art assignment."""

import json
import subprocess
from uuid import uuid4

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest
from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.art_delivery_fixtures import _deliver, _write_art_reference_delivery
from tests.creative_delivery_fixtures import _prepare_art_context


def test_exported_art_survives_wake_warning_and_still_admits_delivery(
    tmp_path, monkeypatch
):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate(
            "ch_" + "r" * 32, render_style="realistic"
        )
        ready = store.admit_art_delivery(_deliver(store, request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=ready.art,
            )
        )
    finally:
        store.close()
    dispatcher = NativeCodexImageDispatcher(str(uuid4()), tmp_path / "dispatch")
    client = TestClient(
        create_project_folder_authoring_app(storage, image_dispatcher=dispatcher)
    )
    url = f"/api/v2/projects/{project_id}/art-reference-proposals"
    prepared = client.post(
        url,
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "renderDirection": "Cinematic realism, no people.",
        },
    )
    assert prepared.status_code == 201, prepared.text
    proposal = prepared.json()["proposal"]
    attempts = []
    original_run = subprocess.run

    def queue(command, **_kwargs):
        if command[1] != "queue":
            return original_run(command, **_kwargs)
        attempts.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "protocol": "plotloom.native-queue.v1",
                    "wakeState": "open_unconfirmed",
                }
            ),
        )

    monkeypatch.setattr(subprocess, "run", queue)
    sent = client.post(f"{url}/{proposal['id']}/send")
    assert sent.status_code == 422, sent.text
    assert sent.json()["code"] == "image_dispatch_wake_unconfirmed"
    assert "请勿重复发送" in sent.json()["message"]
    assert client.get(url).json()["proposals"][0]["state"] == "exported"
    assert (
        json.loads(
            (dispatcher.state_root / proposal["id"] / "receipt.json").read_text()
        )["state"]
        == "queued"
    )
    assert (dispatcher.state_root / "inflight.json").is_file()
    assert client.post(f"{url}/{proposal['id']}/send").status_code >= 400
    assert len(attempts) == 1
    package = next((tmp_path / "outputs").rglob(f"jobs/{proposal['id']}/package"))
    _write_art_reference_delivery(package.parent / "delivery", proposal)
    assert client.post(f"{url}/{proposal['id']}/refresh").json()["state"] == "accepted"
    assert not (dispatcher.state_root / "inflight.json").exists()
