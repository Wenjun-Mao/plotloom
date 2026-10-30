"""One isolated direct-API original for disposal, without batch segment creation."""
import argparse
import json
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from frontend.e2e.video_backends.minimax_h3.offline_gateway import OfflineH3GatewayFake
from plotloom.api import create_project_folder_authoring_app
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from tests.video_prompt_fixtures import reviewed_h3_body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--application", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--body-json", required=True)
    args = parser.parse_args()
    storage = ProjectFolderStorage(outputs_root=args.outputs.resolve(strict=True),
        application_data_root=args.application.resolve())
    app = create_project_folder_authoring_app(storage,
        video_provider=OfflineH3GatewayFake(), video_adapter=MiniMaxH3GatewayAdapter())
    # This namespace was explicitly restored by this test. Acknowledge its
    # retained unfinished synthetic work before requesting a fresh offline take.
    with closing(storage.projects.open(args.project)) as store:
        control = store.recovery_control()
    assert control is not None and control.state == "recovery_required"
    acknowledged = storage.recovery.acknowledge_recovery(args.project)
    assert acknowledged.state == "acknowledged"
    assert acknowledged.operations == control.operations
    # Established direct storage/API fixture: no lifespan means no batch controller.
    # All preparation, fidelity, authorization, submission and probe guards remain.
    client = TestClient(app)
    body = json.loads(args.body_json)
    body.pop("reviewedDirections", None)
    body["idempotencyKey"] = f"fixture-direct-disposal-{uuid4()}"
    body = reviewed_h3_body(client, args.project, body)
    root = f"/api/v2/projects/{args.project}"
    prepared = client.post(root + "/video-jobs", json=body)
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    submitted = client.post(root + f"/video-jobs/{job['id']}/submit")
    assert submitted.status_code == 200 and submitted.json()["state"] == "submitted", submitted.text
    ingested = client.post(root + f"/video-jobs/{job['id']}/reconcile")
    assert ingested.status_code == 200, ingested.text
    value = ingested.json()
    assert value["state"] == "ingested" and not value["selected"], value
    batch = client.get(root + "/video-batch").json()
    cancelled = client.post(root + "/video-batch/control", json={"batchId": batch["id"],
        "expectedControlRevision": batch["controlRevision"], "action": "cancel"})
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled", cancelled.text
    retained = client.get(root + "/video-jobs").json()["jobs"]
    assert next(item for item in retained if item["id"] == job["id"])["segments"] == []
    print(json.dumps({"id": job["id"], "segments": [], "batchId": batch["id"],
        "transport": "offline_h3_fixture", "liveProviderDispatch": False}))


if __name__ == "__main__":
    main()
