"""Real creative admission plus offline queue transport, never automatic adoption."""
import json
import subprocess
from pathlib import Path

import pytest

from plotloom.api.project_folder_specialists import METHODS
from plotloom.creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES
from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
from plotloom.content_language_persistence import check_rows
from tests.specialist_reconciliation_support import ReconciliationRuntime, prepare, ready_delivery, cancel


@pytest.mark.parametrize("stage", METHODS)
@pytest.mark.parametrize("wake_unconfirmed", [False, True])
def test_stage_dispatch_delivery_and_cancelled_observation(tmp_path, monkeypatch, stage, wake_unconfirmed):
    runtime = ReconciliationRuntime(tmp_path, monkeypatch)
    store = runtime.store
    try:
        candidate, request = prepare(store, stage)
        job = candidate.job_id
        exchange = store.creative_handoff_exchange()
        paths = exchange.write_package(request, store.creative_handoff_execution_pin(request))
        original_run = subprocess.run
        output = json.dumps({"protocol": "plotloom.native-queue.v1", "wakeState": "open_unconfirmed"}) if wake_unconfirmed else "Queued"
        calls = []

        def queue(command, **kwargs):
            if command[:2] == ["codex", "queue"]:
                calls.append(command)
                return subprocess.CompletedProcess(command, 0, output)
            return original_run(command, **kwargs)

        monkeypatch.setattr(subprocess, "run", queue)
        url = runtime.url(stage, job)
        with runtime.client(raise_server_exceptions=True) as client:
            assert client.get(url).json()["configured"]
            sent = client.post(url + "/send")
            if wake_unconfirmed:
                assert sent.status_code == 422
                assert sent.json()["code"] == "image_dispatch_wake_unconfirmed"
                assert "任务已入队" in sent.json()["message"]
                assert "请勿重复发送" in sent.json()["message"]
            else:
                assert sent.json()["state"] == "queued"
            assert client.get(url).json()["state"] == "queued"
            assert len(calls) == 1 and calls[0][3] == runtime.settings.text.task_id
            assert str(Path(paths["packagePath"]) / "request.json") in calls[0][-1]
            assert f"{Path(__file__).resolve().parents[1]}/.agents/skills/plotloom-shuohao-specialist/SKILL.md" in calls[0][-1]
            assert "do not infer it from this chat's working directory" in calls[0][-1]
            assert client.post(url + "/send").status_code >= 400
            assert len(calls) == 1
            assert client.post(url + "/check").json()["state"] == "queued"
            delivery = Path(paths["deliveryPath"])
            delivery.mkdir()
            (delivery / CREATIVE_CANDIDATE_FILENAMES[stage]).write_text("{")
            assert client.post(url + "/check").json()["state"] == "queued"
            (delivery / CREATIVE_CANDIDATE_FILENAMES[stage]).unlink()
            delivery.rmdir()
            ready_delivery(store, request)
            checked = client.post(url + "/check")
            assert checked.status_code == 200, checked.text
            assert checked.json()["state"] == "completed"
            current = getattr(store, METHODS[stage][0])().candidate
            assert current.job_id == job and current.status == "ready"
            assert not runtime.registry.view()["busy"]
            with store.repository._read() as session:
                proof_count = len(check_rows(session, store.manifest.project_id))
            cancel(store, stage, job)
            assert client.post(url + "/check").json()["candidateStatus"] == "discarded"
            terminal = getattr(store, METHODS[stage][0])().candidate
            if stage in {"outline", "branches"}:
                assert terminal.job_id == job and terminal.status == "cancelled"
            else:
                assert terminal is None
            with store.repository._read() as session:
                assert session.get(CANDIDATE_ROWS[stage], job).status == "cancelled"
                assert len(check_rows(session, store.manifest.project_id)) == proof_count
            assert len(calls) == 1
    finally:
        store.close()
