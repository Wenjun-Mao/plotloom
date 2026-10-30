"""Retained intent evidence is readable without prospective language authority."""
from contextlib import closing
from copy import deepcopy

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.persistence.schema import ProductionBridgeIntentJobRow
from tests.native_bridge_runtime_fixtures import create_native_intent_runtime
from tests.test_native_bridge_intent import deliver
from tests.working_input_preservation import preservation_inventory


def test_old_native_intent_does_not_break_installed_player_owner_read(tmp_path, monkeypatch):
    native = create_native_intent_runtime(tmp_path, monkeypatch)
    storage, project, _revision, _digest, service, job, calls = native
    service.send(project, job)
    deliver(native)
    service.check(project, job)
    with closing(storage.projects.open(project)) as store, store.repository._write() as session:
        row = session.get(ProductionBridgeIntentJobRow, job)
        request = deepcopy(row.native_request)
        del request["inputArtifacts"]["language-contract.json"]
        row.native_request = request
    before = preservation_inventory(storage.projects.outputs_root)
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        response = client.get(f"/api/v2/projects/{project}/production-bridge")
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["intentJob"]["status"] == "ready"
        assert result["nativeIntentTask"]["languageCheck"] is None
    assert preservation_inventory(storage.projects.outputs_root) == before
    assert len(calls) == 1
