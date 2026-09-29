"""All creative stages use pinned handoffs, never automatic acceptance."""
import subprocess
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_specialists import METHODS, register_specialist_routes
from plotloom.creative_handoff_contracts import CreativeHandoffError
from tests.test_specialist_settings import configured


@pytest.mark.parametrize("stage", METHODS)
def test_stage_dispatch_delivery_and_cancelled_observation(tmp_path, monkeypatch, stage):
    registry, settings = configured(tmp_path)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: calls.append(command) or subprocess.CompletedProcess(command, 0))
    job = "ch_" + "a" * 32
    candidate = SimpleNamespace(job_id=job, status="prepared")
    state = SimpleNamespace(candidate=candidate)
    delivered = []
    admitted = []
    request = object()

    class Exchange:
        def verified_package_paths(self, value, pin):
            assert value is request and pin == "pinned"
            return {"packagePath": "/frozen/package", "deliveryPath": "/frozen/delivery"}

        def read_delivery(self, value, pin):
            assert value is request and pin == "pinned"
            if delivered == ["partial"]:
                raise CreativeHandoffError("delivery_partial", "writing")
            return delivered[0] if delivered else None

    def admit(value):
        admitted.append(value)
        candidate.status = "ready"
        return candidate

    store = SimpleNamespace(creative_handoff_exchange=Exchange, creative_handoff_execution_pin=lambda value: "pinned")
    setattr(store, METHODS[stage][0], lambda: state)
    setattr(store, METHODS[stage][1], lambda requested: request if requested == job else pytest.fail("wrong identity"))
    setattr(store, METHODS[stage][2], admit)

    @contextmanager
    def opened(project):
        assert project == "project"
        yield store

    app = FastAPI()
    register_specialist_routes(app, opened, registry)
    url = f"/api/v2/projects/project/specialist-tasks/{stage}/{job}"
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get(url).json()["configured"]
        assert client.post(url + "/send").json()["state"] == "queued"
        assert len(calls) == 1 and calls[0][3] == settings.text.task_id
        assert "/frozen/package/request.json" in calls[0][-1]
        assert client.post(url + "/send").status_code >= 400
        assert len(calls) == 1
        assert client.post(url + "/check").json()["state"] == "queued"
        delivered.append("partial")
        assert client.post(url + "/check").json()["state"] == "queued"
        delivered[:] = [object()]
        assert client.post(url + "/check").json()["state"] == "completed"
        assert len(admitted) == 1 and candidate.status == "ready"
        assert not registry.view()["busy"]
        # Historical observation must never re-admit cancelled/replaced work.
        state.candidate = None
        assert client.post(url + "/check").json()["candidateStatus"] == "discarded"
        assert len(admitted) == 1
