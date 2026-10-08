"""Capability describes wired runtime services, not persisted inference evidence."""
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from plotloom.api.project_folder_production_bridge import (
    register_project_folder_production_bridge_routes,
)
from plotloom.production_bridge_contracts import ProductionBridgeState


@pytest.mark.parametrize("service_wired,admission_wired", [(False, False), (True, False), (False, True), (True, True)])
def test_runtime_capability_enriches_every_bridge_response_without_changing_stored_state(service_wired, admission_wired):
    state = ProductionBridgeState(status="missing", installation=None, preparation={"status": "unavailable", "reason": "no accepted source"})
    before = state.model_dump()
    store, service, admission = Mock(), Mock(), Mock()
    for method in ["production_bridge_state", "prepare_production_bridge", "update_production_bridge_intent_package", "update_production_bridge_presentation", "accept_production_bridge"]:
        getattr(store, method).return_value = state
    store.repository.production_bridge_intent.load_job.return_value = {"profile": {}}

    @contextmanager
    def opened(_project_id):
        yield store

    app = FastAPI()
    register_project_folder_production_bridge_routes(app, opened, intent_service=service if service_wired else None, text_admission=admission if admission_wired else None)
    available = service_wired and admission_wired
    expected = {"status": "available"} if available else {"status": "unavailable", "reason": "not_configured"}
    base = "/api/v2/projects/project/production-bridge"
    version = {"expectedProposalRevision": 1, "expectedContentHash": "a" * 64}
    empty_head = {"revision": 0, "entityRevisionId": None, "contentHash": None, "status": "missing"}
    prepare = {"expectedProposalRevision": 0, "expectedProposalContentHash": None,
               "expectedSourceInputsHash": "a" * 64,
               "replacementTarget": {"installedAdmissionId": None, **{key: empty_head for key in ("bible", "graph", "sceneBeats", "storyboard")}}}
    with TestClient(app) as client:
        for method, suffix, body in [
            ("GET", "", None), ("POST", "/proposals", prepare),
            ("PUT", "/proposals/intent", {**version, "entries": [{"id": "entry", "text": "Author intent"}]}),
            ("PUT", "/proposals/presentation", {**version, "sourceHash": "b" * 64, "reviewedComplete": True, "entries": []}),
            ("POST", "/accept", version),
        ]:
            result = client.request(method, base + suffix, json=body)
            assert result.status_code == 200, result.text
            assert result.json()["intentGeneration"] == expected
        before_calls = store.mock_calls.copy()
        for suffix, body in [("/intent-jobs", version), ("/intent-jobs/job/resume", None), ("/intent-jobs/job/cancel", None)]:
            result = client.post(base + suffix, json=body)
            if available:
                assert result.status_code in {200, 202}, result.text
                assert result.json()["intentGeneration"] == expected
            else:
                assert result.status_code == 503
                assert result.json()["code"] == "bridge_intent_not_configured"
                assert result.json()["reason"] == "not_configured"
                assert "逐项填写作者意图" in result.json()["message"]
                assert store.mock_calls == before_calls
                service.create.assert_not_called(); service.submit.assert_not_called(); service.cancel.assert_not_called()
                admission.provider_snapshot.assert_not_called()
    assert state.model_dump() == before
    assert "intent_generation" not in before


def test_available_capability_does_not_mask_configured_profile_failure():
    state = ProductionBridgeState(status="missing", installation=None, preparation={"status": "unavailable", "reason": "no accepted source"})
    service, admission = Mock(), Mock()
    admission.provider_snapshot.side_effect = HTTPException(
        status_code=422, detail={"code": "profile_not_ready"}
    )

    @contextmanager
    def opened(_project_id):
        store = Mock()
        store.production_bridge_state.return_value = state
        yield store

    app = FastAPI()
    register_project_folder_production_bridge_routes(
        app, opened, intent_service=service, text_admission=admission
    )
    base = "/api/v2/projects/project/production-bridge"
    with TestClient(app) as client:
        assert client.get(base).json()["intentGeneration"] == {"status": "available"}
        refusal = client.post(base + "/intent-jobs", json={
            "expectedProposalRevision": 1, "expectedContentHash": "a" * 64,
        })
        assert refusal.status_code == 422
        assert refusal.json() == {"detail": {"code": "profile_not_ready"}}
    service.create.assert_not_called()
    admission.text_submission_session_key.assert_not_called()
