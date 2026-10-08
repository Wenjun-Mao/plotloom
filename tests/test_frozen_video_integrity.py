"""Immutable evidence admission is independent of lifecycle and live canon."""

from copy import deepcopy

import pytest

from plotloom.persistence.codec import stable_hash
from plotloom.persistence.project.media_video_integrity import frozen_video_request_is_valid
from plotloom.persistence.project.media_video_segments import VideoSegmentPersistence
from plotloom.persistence.schema import VideoJobRow, VideoSegmentRow


def _job() -> VideoJobRow:
    row = VideoJobRow(
        id="take", project_id="project", idempotency_key="frozen-test",
        state="ingested", requested_seconds=8, output_uri="original.mp4", output_hash="a" * 64,
        snapshot={
            "shot": {"id": "shot", "durationUnits": 5_000},
            "sourceTiming": {"kind": "canonical", "shotId": "shot", "storyboardRevision": 1, "durationUnits": 5_000},
            "approvalId": "approval", "storyboardEntityRevisionId": "board-r1",
            "keyframe": {"bindingId": "binding", "assetId": "still", "originalHash": "b" * 64, "selectionRevision": 1},
            "identityLineage": [], "samePersonReviewId": None,
            "provider": {"adapterId": "minimax_h3_gateway", "adapterVersion": "6", "provider": "minimax_h3_gateway",
                         "model": "minimax_h3_test_profile", "capabilityVersion": 7, "costPolicy": "local_capacity_v1"},
            "request": {"durationSeconds": 8, "resolution": "576x1024", "audio": True,
                        "profileId": "minimax_h3_test_profile", "profileVersion": 2, "width": 576, "height": 1024,
                        "fps": 24, "frameCount": 192, "quality": 1, "seed": 31,
                        "aspectPolicy": "reject_mismatch", "allowLetterbox": False, "allowCenterCrop": False},
            "endFrame": {"revision": 0, "assetId": None}, "playbackIntent": "segment_required",
        },
    )
    _rehash(row)
    return row


def _rehash(row: VideoJobRow) -> None:
    row.snapshot_hash = stable_hash(row.snapshot)
    row.request_hash = stable_hash({"snapshot": row.snapshot, "idempotencyKey": row.idempotency_key})


def _segment(job: VideoJobRow) -> VideoSegmentRow:
    source = deepcopy(job.snapshot["sourceTiming"])
    row = VideoSegmentRow(
        id="proposal", project_id="project", video_job_id=job.id, shot_id="shot",
        source_binding=source, source_binding_hash=stable_hash(source), original_hash=job.output_hash,
        in_frame=0, out_frame=120, authored_duration_units=5_000,
        source_probe={"frameCount": 192, "fps": "24/1"},
        derivative_probe={"frameCount": 120, "fps": "24/1"},
        derivative_uri="proposal.mp4", derivative_hash="c" * 64,
    )
    _rehash_segment(row)
    return row


def _rehash_segment(row: VideoSegmentRow) -> None:
    row.proposal_hash = stable_hash(VideoSegmentPersistence._immutable(row))


def test_frozen_evidence_does_not_require_a_catalog_session_or_current_approval() -> None:
    job = _job()
    assert frozen_video_request_is_valid(job)
    assert VideoSegmentPersistence._valid_metadata(_segment(job), job)
    # A self-consistent bridge source is another current source contract, not an adapter.
    cut = {"shotId": "shot", "seconds": 5}
    job.snapshot["sourceTiming"] = {
        "kind": "f5_bridge", "durationUnits": 5_000, "cut": cut, "cutHash": stable_hash(cut),
        "admissionId": "admission", "proposalContentHash": "d" * 64,
        "proposalRevision": 1, "installedStageRevisions": {"storyboard": 1},
    }
    _rehash(job)
    assert frozen_video_request_is_valid(job)
    assert VideoSegmentPersistence._valid_metadata(_segment(job), job)


@pytest.mark.parametrize("snapshot", [None, [], "broken", {"shot": []}])
def test_nonobject_frozen_evidence_fails_closed_even_with_matching_hashes(snapshot: object) -> None:
    job = _job()
    job.snapshot = snapshot
    _rehash(job)
    assert not frozen_video_request_is_valid(job)


@pytest.mark.parametrize("section,key,value", [
    ("shot", "durationUnits", None), ("shot", "durationUnits", "5000"),
    ("sourceTiming", "durationUnits", True), ("sourceTiming", "shotId", "foreign"),
    ("provider", "adapterId", []), ("provider", "adapterId", "unknown_adapter"),
    ("provider", "adapterId", "atlas_wan"), ("provider", "costPolicy", None),
    ("provider", "capabilityVersion", True), ("provider", "adapterVersion", "not valid"),
    ("request", "audio", "true"), ("request", "audio", False), ("request", "resolution", "other"),
    ("request", "profileVersion", True), ("request", "profileId", None),
    ("request", "quality", 9), ("request", "width", 577),
    ("request", "fps", 30), ("request", "frameCount", 119),
    ("request", "frameCount", True), ("request", "seed", True),
    ("request", "seed", -1), ("request", "allowLetterbox", "false"),
    ("request", "aspectPolicy", "contain_pad"), ("keyframe", "selectionRevision", True),
])
def test_rehashed_malformed_fields_cannot_borrow_valid_snapshot_hashes(section: str, key: str, value: object) -> None:
    job = _job()
    job.snapshot[section][key] = value
    _rehash(job)
    assert not frozen_video_request_is_valid(job)


def test_equal_invalid_durations_and_disguised_provider_cannot_skip_h3_checks() -> None:
    for duration in [None, "5000", True]:
        job = _job()
        job.snapshot["shot"]["durationUnits"] = duration
        job.snapshot["sourceTiming"]["durationUnits"] = duration
        _rehash(job)
        assert not frozen_video_request_is_valid(job)
    job = _job()
    job.snapshot["provider"] = {"adapterId": "atlas_wan", "adapterVersion": "1", "provider": "atlascloud",
                                "model": "alibaba/wan-3.0/image-to-video", "capabilityVersion": 1,
                                "costPolicy": "wan_paid_pilot_v1"}
    _rehash(job)
    assert not frozen_video_request_is_valid(job)


@pytest.mark.parametrize("field", ["allowCenterCrop", "allowLetterbox", "aspectPolicy", "profileVersion", "audio"])
def test_missing_current_contract_fields_cannot_be_replayed(field: str) -> None:
    job = _job()
    del job.snapshot["request"][field]
    _rehash(job)
    assert not frozen_video_request_is_valid(job)


@pytest.mark.parametrize("field,value", [
    ("project_id", "foreign"), ("video_job_id", "foreign"), ("shot_id", "foreign"),
    ("in_frame", True), ("in_frame", -1), ("out_frame", "120"), ("out_frame", 240),
    ("authored_duration_units", True), ("source_probe", []), ("derivative_probe", None),
    ("derivative_uri", ""), ("derivative_hash", ""), ("original_hash", "d" * 64),
])
def test_rehashed_proposal_shapes_and_ownership_fail_closed(field: str, value: object) -> None:
    job = _job()
    segment = _segment(job)
    setattr(segment, field, value)
    _rehash_segment(segment)
    assert not VideoSegmentPersistence._valid_metadata(segment, job)


def test_hash_tampering_and_probe_window_bounds_are_not_preview_eligible() -> None:
    job = _job()
    segment = _segment(job)
    job.request_hash = "0" * 64
    assert not VideoSegmentPersistence._valid_metadata(segment, job)
    _rehash(job)
    for probe in [{"frameCount": True, "fps": "24/1"}, {"frameCount": 119, "fps": "24/1"},
                  {"frameCount": 192, "fps": "30/1"}]:
        segment.source_probe = probe
        _rehash_segment(segment)
        assert not VideoSegmentPersistence._valid_metadata(segment, job)
