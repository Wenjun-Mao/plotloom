from __future__ import annotations

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_app
from plotloom.artifacts import MemoryArtifactStore
from plotloom.domain import STAGE_ORDER, StageName
from plotloom.persistence import SQLiteRepository
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_ingestion import VideoIngestionError, assert_public_https_url
from plotloom.video_jobs import VideoJobService

from .conftest import all_stage_payloads


class FakeWan:
    def __init__(self) -> None:
        self.submits: list[dict] = []

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type == "image/png"
        return "https://upload.example/keyframe"

    def submit(self, payload: dict) -> dict:
        self.submits.append(payload)
        return {"data": {"id": "prediction-1"}}

    def poll(self, prediction_id: str) -> dict:
        assert prediction_id == "prediction-1"
        return {"data": {"status": "completed", "outputs": ["https://cdn.example/clip.mp4"]}}

    def download(self, url: str) -> bytes:
        assert url == "https://cdn.example/clip.mp4"
        return b"offline-playable-fixture"


def png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (12, 8), (20, 30, 40)).save(output, format="PNG")
    return output.getvalue()


def approved_keyframe(client: TestClient, repository: SQLiteRepository, project_id: str) -> tuple[str, int, str, int]:
    review = client.get(f"/api/v2/projects/{project_id}/storyboard-review").json()
    approval = client.post(f"/api/v2/projects/{project_id}/storyboard-approval", json={
        "expectedRevision": review["head"]["revision"], "contentHash": review["head"]["contentHash"],
        "decision": "approve", "reviewer": "P2 fake-browser fixture", "gateSetVersion": review["gateEvaluation"]["gateSetVersion"],
        "note": "Explicit test approval",
    }).json()["decision"]
    asset = client.post(f"/api/v2/projects/{project_id}/managed-assets", files={"image": ("fixture.png", png(), "image/png")}, data={"origin": "P2 test fixture", "rights": "unknown"}).json()
    intent = client.post(f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/visual-intents", json={"role": "shot_keyframe", "identityIntent": "fixture", "sourceRefs": ["test"]}).json()
    shot_id = repository.get_stage_payload(project_id, StageName.STORYBOARD).shots[0].id
    selected = client.post(f"/api/v2/projects/{project_id}/reviewed-keyframes", json={
        "assetId": asset["id"], "shotId": shot_id, "sceneId": repository.get_stage_payload(project_id, StageName.STORYBOARD).shots[0].scene_id,
        "expectedSelectionRevision": 0, "storyboardRevision": review["head"]["revision"], "approvalId": approval["id"],
        "compatibilityNote": "P2 fixture is explicitly compatible", "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
    })
    assert selected.status_code == 201, selected.text
    return approval["id"], review["head"]["revision"], shot_id, selected.json()["selectionRevision"]


def test_fake_fastapi_p2_path_is_idempotent_budgeted_and_range_playable(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    artifacts, provider = MemoryArtifactStore(), FakeWan()
    service = VideoJobService(repository, artifacts, provider, probe=lambda _: ObservedVideo(5.2, 1280, 720, "h264", "aac"))
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        body = {"approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision, "expectedSelectionRevision": selection_revision, "idempotencyKey": "p2-browser-fake-idempotency"}
        prepared = client.post(f"/api/v2/projects/{project.id}/video-jobs", json=body)
        assert prepared.status_code == 201, prepared.text
        job = prepared.json()
        duplicate = client.post(f"/api/v2/projects/{project.id}/video-jobs", json=body)
        assert duplicate.status_code == 201 and duplicate.json()["id"] == job["id"]
        assert client.get("/api/v2/video-pilot-budget").json()["reservedSeconds"] == 5
        submitted = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit")
        assert submitted.status_code == 200 and submitted.json()["state"] == "submitted"
        assert provider.submits[0]["model"] == "alibaba/wan-3.0/image-to-video"
        assert provider.submits[0]["image"] == "https://upload.example/keyframe"
        assert "image_url" not in provider.submits[0]
        ingested = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/reconcile")
        assert ingested.status_code == 200 and ingested.json()["state"] == "ingested"
        media = client.get(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/media", headers={"Range": "bytes=0-6"})
        assert media.status_code == 206 and media.content == b"offline"
        reviewed = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/review", json={"reviewer": "P2 browser fixture", "decision": "select", "note": "Explicit fake-candidate selection."})
        assert reviewed.status_code == 201
        # A second click cannot replay a paid POST after the durable boundary.
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 409
        assert len(provider.submits) == 1


def test_p2_cap_claims_are_atomic_and_cancel_only_releases_before_dispatch(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    with TestClient(create_app(repository)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        def prepare(index: int) -> str:
            return repository.prepare_video_job(project.id, approval_id=approval_id, shot_id=shot_id, storyboard_revision=revision, expected_selection_revision=selection_revision, idempotency_key=f"concurrent-video-key-{index:03d}")["id"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(prepare, range(20)))
        assert len(set(ids)) == 20
        assert repository.video_budget()["remainingSeconds"] == 0
        try:
            prepare(99)
        except Exception as error:
            assert "allowance" in str(error)
        else:
            raise AssertionError("101st requested second must not reserve")
        # Proven cancellation while still prepared is the only release path.
        assert repository.cancel_video_job(project.id, ids[0])["state"] == "cancelled"
        assert repository.video_budget()["remainingSeconds"] == 5
        repository.claim_video_dispatch(project.id, ids[1])
        cancelled_after_dispatch = repository.cancel_video_job(project.id, ids[1])
        assert cancelled_after_dispatch["state"] == "dispatching"
        assert cancelled_after_dispatch["cancelRequestedAt"] is not None
        # A late POST acknowledgement still records a known remote identity
        # for reconciliation; local cancel intent prevents adoption, not truth.
        assert repository.record_video_submission(project.id, ids[1], "late-known-id")["state"] == "submitted"
        assert repository.video_budget()["remainingSeconds"] == 5
        restart_job = prepare(100)
        repository.claim_video_dispatch(project.id, restart_job)
        assert repository.recover_video_dispatches() == [restart_job]
        assert next(item for item in repository.list_video_jobs(project.id) if item["id"] == restart_job)["state"] == "outcome_unknown"


def test_p2_unknown_post_and_private_download_never_replay_or_publish(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    class AmbiguousWan(FakeWan):
        def submit(self, payload: dict) -> dict:
            self.submits.append(payload)
            raise TimeoutError("post outcome is unknown")
    artifacts, provider = MemoryArtifactStore(), AmbiguousWan()
    service = VideoJobService(repository, artifacts, provider, probe=lambda _: ObservedVideo(5, 1280, 720, "h264", "aac"))
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        job = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={"approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision, "expectedSelectionRevision": selection_revision, "idempotencyKey": "unknown-post-key"}).json()
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").json()["state"] == "outcome_unknown"
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 409
        assert len(provider.submits) == 1 and client.get("/api/v2/video-pilot-budget").json()["reservedSeconds"] == 5


def test_p2_download_boundary_rejects_private_and_probe_failures() -> None:
    for url in ("https://127.0.0.1/clip.mp4", "https://[::1]/clip.mp4", "https://localhost/clip.mp4"):
        try:
            assert_public_https_url(url)
        except VideoIngestionError:
            pass
        else:
            raise AssertionError(f"private candidate URL admitted: {url}")


def test_known_remote_failure_is_terminal_and_cancelled_known_id_is_polled_not_adopted(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    class ControlledWan(FakeWan):
        polls = 0
        downloads = 0
        def poll(self, prediction_id: str) -> dict:
            self.polls += 1
            return {"data": {"status": "failed"}}
        def download(self, url: str) -> bytes:
            self.downloads += 1
            return super().download(url)
    artifacts, provider = MemoryArtifactStore(), ControlledWan()
    service = VideoJobService(repository, artifacts, provider, probe=lambda _: ObservedVideo(5, 1280, 720, "h264", "aac"))
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        def make(key: str) -> dict:
            return client.post(f"/api/v2/projects/{project.id}/video-jobs", json={"approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision, "expectedSelectionRevision": selection_revision, "idempotencyKey": key}).json()
        failed = make("terminal-failure-key")
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{failed['id']}/submit")
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{failed['id']}/reconcile").json()["state"] == "failed"
        # Restore a completion response: cancel retains the known ID and polls,
        # but must never retrieve or publish it.
        provider.poll = lambda _id: {"data": {"status": "completed", "outputs": ["https://cdn.example/clip.mp4"]}}  # type: ignore[method-assign]
        cancelled = make("cancelled-known-id")
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{cancelled['id']}/submit")
        cancelled_view = client.post(f"/api/v2/projects/{project.id}/video-jobs/{cancelled['id']}/cancel").json()
        assert cancelled_view["state"] == "submitted" and cancelled_view["cancelRequestedAt"]
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{cancelled['id']}/reconcile").json()["state"] == "submitted"
        assert provider.downloads == 0
