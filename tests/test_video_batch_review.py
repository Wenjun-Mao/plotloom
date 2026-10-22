"""Real decoded synthetic media through atomic whole-pack human confirmation."""
from contextlib import closing
import shutil
import subprocess
import pytest
from sqlalchemy import select
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import VideoBatchReceiptRow, VideoSegmentRow, VideoReviewRow
from plotloom.video_batch_contracts import BatchConfirmation
from plotloom.video_ingestion import probe_video
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch


@pytest.fixture(scope="module")
def native_batch_take(tmp_path_factory):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg required for native segment verification")
    path = tmp_path_factory.mktemp("batch-synthetic") / "take.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=576x1024:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5.1666666667",
        "-frames:v", "124", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
        "-movflags", "+faststart", "-y", str(path)], check=True, timeout=60)
    return path.read_bytes()


def complete_batch(tmp_path, take):
    storage, client, service, provider, project_id, view = batch_environment(tmp_path)
    provider._outputs = [take]
    service.video._probe = probe_video
    start_batch(service, project_id, ready_batch(service, project_id, view))
    for _ in range(40):
        service.step(project_id)
        current = service.current(project_id)
        if current["state"] in {"awaiting_review", "blocked"}:
            break
    assert current["state"] == "awaiting_review", current["execution"].get("error")
    with closing(storage.projects.open(project_id)) as store:
        jobs = service.video.jobs(store)
        assert not store.repository.video_batches.needs_step(project_id)
        assert len(jobs) == len(provider.submits) == 6
        assert all(job["state"] == "ingested" and not job["selected"] and job["segments"] for job in jobs)
    return storage, client, service, project_id, current


def confirmation(view, review):
    return BatchConfirmation(expectedRevision=view["revision"], reviewHash=review["reviewHash"], basis="whole-pack-video-native-audio.v1")


def test_one_confirmation_selects_every_proposal_and_reconciles_lost_ack(tmp_path, native_batch_take):
    storage, client, service, project_id, current = complete_batch(tmp_path, native_batch_take)
    review = service.review(project_id)
    assert review["ready"] and review["readyCount"] == 6
    body = confirmation(current, review)
    receipt = service.confirm(project_id, body)
    assert receipt["attribution"] == {"kind": "unnamed_creator"} and not receipt["note"]
    assert service.confirm(project_id, body) == receipt
    with closing(storage.projects.open(project_id)) as store:
        jobs = service.video.jobs(store)
        assert all(job["selected"] and job["playbackSegment"] for job in jobs)
        with store.repository._read() as session:
            retained = session.scalars(select(VideoBatchReceiptRow)).all()
            assert len(retained) == 1
            assert all(segment.confirmation_receipt_id == receipt["id"] for segment in session.scalars(select(VideoSegmentRow)))
        playback = client.get(f"/api/v2/projects/{project_id}/video-jobs/{jobs[0]['id']}/playback")
        assert playback.status_code == 200 and playback.content


def test_late_target_rejection_rolls_back_the_entire_selection_transaction(tmp_path, native_batch_take, monkeypatch):
    storage, _client, service, project_id, current = complete_batch(tmp_path, native_batch_take)
    review = service.review(project_id)
    from plotloom.persistence.project.media_video_segments import VideoSegmentPersistence
    original = VideoSegmentPersistence.select
    calls = []
    def select_with_late_failure(self, *args, **kwargs):
        calls.append(args[1])
        if len(calls) == 6:
            raise InvalidTransitionError("last target changed while confirming")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(VideoSegmentPersistence, "select", select_with_late_failure)
    with pytest.raises(InvalidTransitionError, match="last target"):
        service.confirm(project_id, confirmation(current, review))
    with closing(storage.projects.open(project_id)) as store:
        assert not any(job["selected"] for job in service.video.jobs(store))
        with store.repository._read() as session:
            assert not session.scalars(select(VideoBatchReceiptRow)).all()
            assert not session.scalars(select(VideoReviewRow)).all()
    assert len(calls) == 6


def test_latest_reject_blocks_whole_pack_and_cannot_fall_back(tmp_path, native_batch_take):
    storage, _client, service, project_id, current = complete_batch(tmp_path, native_batch_take)
    review = service.review(project_id)
    final = review["proposals"][-1]
    with closing(storage.projects.open(project_id)) as store:
        service.video.review(store, final["jobId"], reviewer="Fixture creator", decision="reject", note="Fixture audio is unacceptable.", expected_selection_revision=0)
    changed = service.review(project_id)
    assert not changed["ready"]
    with pytest.raises(InvalidTransitionError): service.confirm(project_id, confirmation(current, review))
    with closing(storage.projects.open(project_id)) as store:
        assert not any(job["selected"] for job in service.video.jobs(store))


def test_manual_native_window_rebinds_batch_and_invalidates_old_confirmation(tmp_path, native_batch_take):
    from plotloom.project_storage.project_video import ProjectVideoRepository
    storage, _client, service, project_id, current = complete_batch(tmp_path, native_batch_take)
    old_review = service.review(project_id)
    target = old_review["proposals"][0]
    with closing(storage.projects.open(project_id)) as store:
        proposal = ProjectVideoRepository(store, storage.application).prepare_video_segment(
            project_id, target["jobId"], in_frame=2, out_frame=122, expected_selection_revision=0)
    changed = service.current(project_id)
    review = service.review(project_id)
    assert changed["revision"] > current["revision"] and review["ready"]
    assert review["proposals"][0]["segmentId"] == proposal["id"]
    assert review["reviewHash"] != old_review["reviewHash"]
    with pytest.raises(InvalidTransitionError):
        service.confirm(project_id, confirmation(changed, old_review))
    service.confirm(project_id, confirmation(changed, review))


def test_reopening_rejected_alternative_preserves_batch_selected_content(tmp_path, native_batch_take):
    from tests.video_prompt_fixtures import reviewed_h3_body
    storage, client, service, project_id, current = complete_batch(tmp_path, native_batch_take)
    review = service.review(project_id)
    receipt = service.confirm(project_id, confirmation(current, review))
    target = current["manifest"]["targets"][0]
    args = target["args"]
    base = f"/api/v2/projects/{project_id}"
    body = {"approvalId": args["approval_id"], "shotId": args["shot_id"], "storyboardRevision": args["storyboard_revision"],
        "expectedSelectionRevision": args["expected_selection_revision"], "idempotencyKey": "retained-alternative", "seed": 99,
        "requestedDurationSeconds": args["requested_seconds"], "aspectPolicy": "reject_mismatch"}
    response = client.post(f"{base}/video-jobs", json=reviewed_h3_body(client, project_id, body))
    assert response.status_code == 201, response.text
    other = response.json()["id"]
    assert client.post(f"{base}/video-jobs/{other}/submit").status_code == 200
    assert client.post(f"{base}/video-jobs/{other}/reconcile").json()["state"] == "ingested"
    rejected = client.post(f"{base}/video-jobs/{other}/review", json={"decision":"reject", "reviewer":"Creator", "note":"Retain alternative", "expectedSelectionRevision":1})
    assert rejected.status_code == 201, rejected.text
    reopened = client.post(f"{base}/video-jobs/{other}/review/reopen", json={"reviewer":"Creator", "reason":"Inspect retained alternative", "expectedSelectionRevision":1})
    assert reopened.status_code == 201, reopened.text
    jobs = client.get(f"{base}/video-jobs").json()["jobs"]
    original = next(job for job in jobs if job["id"] == receipt["selections"][0]["jobId"])
    assert original["selected"] and original["playbackSegment"]["id"] == receipt["selections"][0]["segmentId"]
    assert client.get(f"{base}/video-jobs/{original['id']}/playback").status_code == 200


def test_progress_reads_execution_facts_without_revalidating_the_gallery(tmp_path, native_batch_take, monkeypatch):
    _storage, _client, service, project_id, _current = complete_batch(tmp_path, native_batch_take)
    monkeypatch.setattr(service.video, "jobs", lambda *_: pytest.fail("progress rebuilt full media eligibility"))
    current = service.current(project_id)
    assert current["state"] == "awaiting_review"
    assert current["progress"] == {"total": 6, "ready": 6, "failed": 0, "blocked": 0}
