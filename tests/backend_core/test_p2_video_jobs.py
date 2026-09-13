from __future__ import annotations

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_app
from plotloom.artifacts import MemoryArtifactStore
from plotloom.canonical_schema import CharacterV2
from plotloom.domain import STAGE_ORDER, StageName
from plotloom.persistence import SQLiteRepository
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_ingestion import VideoIngestionError, assert_public_https_url
from plotloom.video_jobs import VideoJobService
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_provider import WanDispatchDiagnostic, WanDispatchError

from .conftest import all_stage_payloads


class FakeWan:
    def __init__(self) -> None:
        self.submits: list[dict] = []

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type == "image/png"
        return "https://upload.example/keyframe"

    def submit(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
        _ = idempotency_key
        self.submits.append(payload)
        return {"data": {"id": "prediction-1"}}

    def poll(self, prediction_id: str) -> dict:
        assert prediction_id == "prediction-1"
        return {"data": {"status": "completed", "outputs": ["https://cdn.example/clip.mp4"]}}

    def download(self, url: str) -> bytes:
        assert url == "https://cdn.example/clip.mp4"
        return b"offline-playable-fixture"


class FakeH3Gateway:
    """The exact public H3 envelope, without a ComfyUI or network dependency."""

    def __init__(self, *, outcome_unknown: bool = False) -> None:
        self.outcome_unknown = outcome_unknown
        self.submits: list[dict] = []
        self.idempotency_keys: list[str | None] = []
        self.preflight_calls = 0
        self.profile_id: str | None = None

    def preflight(self) -> None:
        self.preflight_calls += 1

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type == "image/png"
        return "asset_0123456789abcdef0123456789abcdef"

    def submit(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
        self.submits.append(payload)
        self.idempotency_keys.append(idempotency_key)
        self.profile_id = payload["profileId"]
        return {
            "id": "h3_0123456789abcdef0123456789abcdef", "status": "submitted",
            "profileId": payload["profileId"], "aspectPolicy": payload["aspectPolicy"],
            "error": None, "outputReady": False,
        }

    def poll(self, prediction_id: str) -> dict:
        assert prediction_id == "h3_0123456789abcdef0123456789abcdef"
        return {
            "id": prediction_id, "status": "outcome_unknown" if self.outcome_unknown else "succeeded",
            "profileId": self.profile_id, "aspectPolicy": "cover_center_crop",
            "error": None, "outputReady": not self.outcome_unknown,
        }

    def download(self, reference: str) -> bytes:
        assert reference == "h3_0123456789abcdef0123456789abcdef"
        return b"offline-h3-playable-fixture"


def png(*, width: int = 12, height: int = 8) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), (20, 30, 40)).save(output, format="PNG")
    return output.getvalue()


def approved_keyframe(
    client: TestClient,
    repository: SQLiteRepository,
    project_id: str,
    *,
    image: bytes | None = None,
) -> tuple[str, int, str, int]:
    review = client.get(f"/api/v2/projects/{project_id}/storyboard-review").json()
    approval = client.post(f"/api/v2/projects/{project_id}/storyboard-approval", json={
        "expectedRevision": review["head"]["revision"], "contentHash": review["head"]["contentHash"],
        "decision": "approve", "reviewer": "P2 fake-browser fixture", "gateSetVersion": review["gateEvaluation"]["gateSetVersion"],
        "note": "Explicit test approval",
    }).json()["decision"]
    asset = client.post(
        f"/api/v2/projects/{project_id}/managed-assets",
        files={"image": ("fixture.png", image or png(), "image/png")},
        data={"origin": "P2 test fixture", "rights": "unknown"},
    ).json()
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
        # Adapter V2 must not retroactively change the persisted V1 Atlas
        # shape: old snapshots and their hashes remain historical evidence.
        assert job["snapshot"]["snapshotVersion"] == 1
        assert job["snapshot"]["compilerVersion"] == "p2-wan-v1"
        assert job["snapshot"]["provider"] == {
            "provider": "atlascloud", "model": "alibaba/wan-3.0/image-to-video",
            "capabilityVersion": 1, "imageField": "image",
        }
        assert job["snapshot"]["request"] == {
            "durationSeconds": 5, "resolution": "720p", "audio": True,
        }
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
        # A later review of another attempt for the same Shot controls the
        # selection projection; historical selects stay evidence, not truth.
        second_body = {**body, "idempotencyKey": "p2-browser-fake-second-attempt"}
        second = client.post(f"/api/v2/projects/{project.id}/video-jobs", json=second_body).json()
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{second['id']}/submit")
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{second['id']}/reconcile")
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{second['id']}/review", json={"reviewer": "P2 browser fixture", "decision": "reject", "note": "Latest same-shot review rejects this candidate."}).status_code == 201
        assert not any(item["selected"] for item in client.get(f"/api/v2/projects/{project.id}/video-jobs").json()["jobs"])
        # A second click cannot replay a paid POST after the durable boundary.
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 409
        assert len(provider.submits) == 2


def test_h3_fastapi_path_freezes_gateway_contract_and_never_charges_wan_budget(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    artifacts, provider = MemoryArtifactStore(), FakeH3Gateway()
    service = VideoJobService(
        repository,
        artifacts,
        provider,
        adapter=MiniMaxH3GatewayAdapter(),
        probe=lambda _: ObservedVideo(5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124),
    )
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(
            client, repository, project.id, image=png(width=576, height=1024)
        )
        body = {
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "h3-browser-idempotency",
            "aspectPolicy": "reject_mismatch", "seed": 81,
        }
        prepared = client.post(f"/api/v2/projects/{project.id}/video-jobs", json=body)
        assert prepared.status_code == 201, prepared.text
        job = prepared.json()
        assert job["snapshot"]["snapshotVersion"] == 3
        assert job["snapshot"]["compilerVersion"] == "p2-video-adapters-v2"
        assert job["snapshot"]["provider"] == {
            "adapterId": "minimax_h3_gateway", "adapterVersion": "2",
            "provider": "minimax_h3_gateway", "model": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
            "capabilityVersion": 2, "costPolicy": "local_capacity_v1",
        }
        assert job["snapshot"]["request"] == {
            "durationSeconds": 5, "resolution": "576x1024", "audio": True,
            "aspectPolicy": "reject_mismatch", "allowLetterbox": False, "seed": 81,
            "profileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1", "profileVersion": 1,
            "width": 576, "height": 1024,
        }
        assert client.get("/api/v2/video-pilot-budget").json()["reservedSeconds"] == 0
        assert client.get("/api/v2/video-backend").json()["adapterId"] == "minimax_h3_gateway"
        submitted = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit")
        assert submitted.status_code == 200 and submitted.json()["state"] == "submitted"
        assert provider.preflight_calls == 1
        assert provider.submits == [{
            "assetId": "asset_0123456789abcdef0123456789abcdef",
            "prompt": service._prompt(job["snapshot"]),
            "profileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
            "aspectPolicy": "reject_mismatch", "seed": 81,
        }]
        assert provider.idempotency_keys == [job["id"]]
        ingested = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/reconcile")
        assert ingested.status_code == 200 and ingested.json()["state"] == "ingested"


def test_h3_refuses_a_mismatched_keyframe_before_creating_a_job_or_submitting(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    artifacts, provider = MemoryArtifactStore(), FakeH3Gateway()
    service = VideoJobService(
        repository,
        artifacts,
        provider,
        adapter=MiniMaxH3GatewayAdapter(),
        probe=lambda _: ObservedVideo(5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124),
    )
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        # The fixture's default still is landscape, while the default H3 profile
        # is portrait. Admission must fail before a job, capacity reservation,
        # upload, or gateway POST exists.
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        rejected = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "h3-mismatch-preflight",
            "aspectPolicy": "reject_mismatch", "seed": 810,
        })
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "keyframe_aspect_mismatch"
        assert rejected.json()["source"] == {"width": 12, "height": 8}
        assert rejected.json()["target"] == {"width": 576, "height": 1024}
        assert client.get(f"/api/v2/projects/{project.id}/video-jobs").json()["jobs"] == []
        assert client.get("/api/v2/video-pilot-budget").json()["reservedSeconds"] == 0
        assert provider.submits == [] and provider.preflight_calls == 0

        # Letterboxing is a narrow, explicit alternative: it preserves the
        # mismatched source on a black profile canvas while retaining the exact
        # profile, selected-keyframe, and output-contract checks.
        letterboxed = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "h3-letterbox-preflight",
            "aspectPolicy": "contain_pad", "allowLetterbox": True, "seed": 811,
        })
        assert letterboxed.status_code == 201, letterboxed.text
        assert letterboxed.json()["snapshot"]["request"] == {
            "durationSeconds": 5, "resolution": "576x1024", "audio": True,
            "aspectPolicy": "contain_pad", "allowLetterbox": True, "seed": 811,
            "profileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1", "profileVersion": 1,
            "width": 576, "height": 1024,
        }
        assert client.post(
            f"/api/v2/projects/{project.id}/video-jobs/{letterboxed.json()['id']}/submit"
        ).status_code == 200
        assert provider.submits[0]["aspectPolicy"] == "contain_pad"


def test_h3_known_gateway_outcome_unknown_is_never_replayed(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    artifacts, provider = MemoryArtifactStore(), FakeH3Gateway(outcome_unknown=True)
    service = VideoJobService(
        repository,
        artifacts,
        provider,
        adapter=MiniMaxH3GatewayAdapter(),
        probe=lambda _: ObservedVideo(5.167, 864, 480, "h264", "aac", frame_rate=24, frame_count=124),
    )
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(
            client, repository, project.id, image=png(width=576, height=1024)
        )
        job = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "h3-outcome-unknown",
            "aspectPolicy": "reject_mismatch", "seed": 82,
        }).json()
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit")
        unknown = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/reconcile")
        assert unknown.status_code == 200 and unknown.json()["state"] == "outcome_unknown"
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 409
        assert len(provider.submits) == 1


def test_h3_rejects_a_playable_output_that_violates_the_frozen_profile(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    artifacts, provider = MemoryArtifactStore(), FakeH3Gateway()
    service = VideoJobService(
        repository,
        artifacts,
        provider,
        adapter=MiniMaxH3GatewayAdapter(),
        # This is browser-playable H.264/AAC but not the frozen 576x1024,
        # 124-frame H3 output, so it cannot be published as that profile.
        probe=lambda _: ObservedVideo(5.167, 1280, 720, "h264", "aac", frame_rate=24, frame_count=124),
    )
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(
            client, repository, project.id, image=png(width=576, height=1024)
        )
        job = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "h3-profile-mismatch",
            "aspectPolicy": "reject_mismatch", "seed": 83,
        }).json()
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 200
        rejected = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/reconcile")
        assert rejected.status_code == 200
        assert rejected.json()["state"] == "retrieve_needed"
        assert rejected.json()["error"] == "h3_output_profile_mismatch"


def test_h3_stale_identity_lineage_cannot_cross_the_submit_boundary(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    character = CharacterV2(
        id="h3_character", name="Mara", role="archivist", description="A controlled archivist.",
        visual_anchors=["dark braid"], sound_anchors=["quiet breath"], allowed_states=["steady"],
        continuity_rules=["hands remain below the close frame"], goal="protect the record",
        traits=["measured"], voice_anchors=["low controlled voice"],
    )
    bible.characters = [character]
    beats.scenes[0].character_ids = [character.id]
    storyboard.shots[0].character_ids = [character.id]
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    artifacts, provider = MemoryArtifactStore(), FakeH3Gateway()
    service = VideoJobService(
        repository,
        artifacts,
        provider,
        adapter=MiniMaxH3GatewayAdapter(),
        probe=lambda _: ObservedVideo(5.167, 864, 480, "h264", "aac", frame_rate=24, frame_count=124),
    )
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(
            client, repository, project.id, image=png(width=576, height=1024)
        )
        keyframe = client.get(f"/api/v2/projects/{project.id}/managed-assets").json()["assets"][0]
        character_id = character.id
        initial = client.post(f"/api/v2/projects/{project.id}/character-references", json={
            "characterId": character_id, "primaryAssetId": keyframe["id"], "complementaryAssetIds": [],
            "expectedReferenceRevision": 0, "reviewer": "H3 fixture reviewer", "notes": "Initial reference.",
        })
        assert initial.status_code == 201, initial.text
        prepared = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "h3-stale-lineage",
            "aspectPolicy": "reject_mismatch", "seed": 84,
        })
        assert prepared.status_code == 201, prepared.text
        replacement = client.post(f"/api/v2/projects/{project.id}/character-references", json={
            "characterId": character_id, "primaryAssetId": keyframe["id"], "complementaryAssetIds": [],
            "expectedReferenceRevision": initial.json()["referenceRevision"], "reviewer": "H3 fixture reviewer",
            "notes": "Replacement makes the frozen candidate stale.",
        })
        assert replacement.status_code == 201, replacement.text
        job_id = prepared.json()["id"]
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job_id}/submit").status_code == 409
        assert provider.submits == []


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
        def submit(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
            _ = idempotency_key
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


def test_p2_upload_diagnostic_keeps_unknown_outcome_and_budget_without_provider_text(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)

    class RejectedUploadWan(FakeWan):
        def upload(self, image: bytes, *, mime_type: str) -> str:
            raise WanDispatchError(WanDispatchDiagnostic("upload", "http_rejected", 401))

    artifacts, provider = MemoryArtifactStore(), RejectedUploadWan()
    service = VideoJobService(repository, artifacts, provider, probe=lambda _: ObservedVideo(5, 1280, 720, "h264", "aac"))
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        job = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "diagnostic-upload-key",
        }).json()
        submitted = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").json()
        assert submitted["state"] == "outcome_unknown"
        assert submitted["error"] == "dispatch_upload_http_rejected_status_401"
        assert "secret" not in submitted["error"]
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 409
        assert not provider.submits
        assert client.get("/api/v2/video-pilot-budget").json()["reservedSeconds"] == 5


def test_p2_submit_response_diagnostic_never_treats_a_post_as_replayable(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)

    class MalformedSubmitWan(FakeWan):
        def submit(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
            _ = idempotency_key
            self.submits.append(payload)
            return {"data": {"detail": "provider response with a signed-url=secret"}}

    artifacts, provider = MemoryArtifactStore(), MalformedSubmitWan()
    service = VideoJobService(repository, artifacts, provider, probe=lambda _: ObservedVideo(5, 1280, 720, "h264", "aac"))
    with TestClient(create_app(repository, artifact_store=artifacts, video_job_service=service)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        job = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "diagnostic-submit-response-key",
        }).json()
        submitted = client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").json()
        assert submitted["state"] == "outcome_unknown"
        assert submitted["error"] == "dispatch_submit_response_parse_invalid_envelope"
        assert "secret" not in submitted["error"]
        assert len(provider.submits) == 1
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{job['id']}/submit").status_code == 409
        assert client.get("/api/v2/video-pilot-budget").json()["reservedSeconds"] == 5


def test_p2_download_boundary_rejects_private_and_probe_failures() -> None:
    for url in ("https://127.0.0.1/clip.mp4", "https://[::1]/clip.mp4", "https://localhost/clip.mp4"):
        try:
            assert_public_https_url(url)
        except VideoIngestionError:
            pass
        else:
            raise AssertionError(f"private candidate URL admitted: {url}")


def test_p2_imported_keyframe_freezes_visible_character_reference_lineage(repository, brief) -> None:
    """A retained still needs a real reference decision, not an empty identity snapshot."""

    project = repository.create_project(brief)
    bible, graph, beats, storyboard = all_stage_payloads()
    captain = CharacterV2(
        id="captain", name="Mara", role="archivist", description="A controlled municipal archivist.",
        visual_anchors=["dark braid"], sound_anchors=["quiet breath"], allowed_states=["steady"],
        continuity_rules=["hands remain below the close frame"], goal="protect the record",
        traits=["measured"], voice_anchors=["low controlled voice"],
    )
    bible.characters = [captain]
    beats.scenes[0].character_ids = [captain.id]
    storyboard.shots[0].character_ids = [captain.id]
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    with TestClient(create_app(repository)) as client:
        approval_id, revision, shot_id, selection_revision = approved_keyframe(client, repository, project.id)
        keyframe = client.get(f"/api/v2/projects/{project.id}/managed-assets").json()["assets"][0]
        reference = client.post(f"/api/v2/projects/{project.id}/character-references", json={
            "characterId": captain.id, "primaryAssetId": keyframe["id"], "complementaryAssetIds": [],
            "expectedReferenceRevision": 0, "reviewer": "P2 fixture reviewer",
            "notes": "Explicit retained-keyframe identity review.",
        })
        assert reference.status_code == 201, reference.text
        prepared = client.post(f"/api/v2/projects/{project.id}/video-jobs", json={
            "approvalId": approval_id, "shotId": shot_id, "storyboardRevision": revision,
            "expectedSelectionRevision": selection_revision, "idempotencyKey": "imported-reference-lineage",
        })
        assert prepared.status_code == 201, prepared.text
        frozen = prepared.json()["snapshot"]["identityLineage"]
        assert frozen == [{
            "characterId": captain.id, "referenceDecisionId": reference.json()["id"],
            "referenceRevision": 1, "characterContextHash": reference.json()["characterContextHash"],
            "assets": reference.json()["assetHashes"],
        }]
        replacement = client.post(f"/api/v2/projects/{project.id}/character-references", json={
            "characterId": captain.id, "primaryAssetId": keyframe["id"], "complementaryAssetIds": [],
            "expectedReferenceRevision": 1, "reviewer": "P2 fixture reviewer",
            "notes": "A later decision intentionally makes the prepared clip stale.",
        })
        assert replacement.status_code == 201, replacement.text
        assert client.get(f"/api/v2/projects/{project.id}/video-jobs").json()["jobs"][0]["current"] is False


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
        provider.poll = lambda _id: {}  # type: ignore[method-assign]
        malformed = make("malformed-poll-key")
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{malformed['id']}/submit")
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{malformed['id']}/reconcile").json()["state"] == "retrieve_needed"
        # Restore a completion response: cancel retains the known ID and polls,
        # but must never retrieve or publish it.
        provider.poll = lambda _id: {"data": {"status": "completed", "outputs": ["https://cdn.example/clip.mp4"]}}  # type: ignore[method-assign]
        cancelled = make("cancelled-known-id")
        client.post(f"/api/v2/projects/{project.id}/video-jobs/{cancelled['id']}/submit")
        cancelled_view = client.post(f"/api/v2/projects/{project.id}/video-jobs/{cancelled['id']}/cancel").json()
        assert cancelled_view["state"] == "submitted" and cancelled_view["cancelRequestedAt"]
        assert client.post(f"/api/v2/projects/{project.id}/video-jobs/{cancelled['id']}/reconcile").json()["state"] == "submitted"
        assert provider.downloads == 0
