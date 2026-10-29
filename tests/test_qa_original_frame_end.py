"""Prospective ending guidance cannot widen retained project/material grants."""
from copy import deepcopy
from dataclasses import replace

import pytest

from plotloom.delegated_qa import SCOPES
from plotloom.delegated_qa_end_frames import ORIGINAL_FRAME_END_GRANTS
from plotloom.delegated_qa_video import assert_snapshot
from plotloom.exceptions import InvalidTransitionError


def snapshot_for(grant):
    scope = next(item for item in SCOPES if item.id == grant.scope_id)
    first = {"assetId": grant.asset_id, "originalHash": grant.original_hash,
        "mimeType": "image/png", "width": 1280, "height": 720}
    source = {"kind": "f5_bridge", "cut": {"shotId": grant.shot_id, "seconds": 8}}
    snapshot = {"compilerVersion": "plotloom.h3-production-brief.v10",
        "shot": {"id": grant.shot_id}, "keyframe": first,
        "approvalId": "synthetic-current-approval", "storyboardRevision": 2, "sourceTiming": source,
        "request": {"profileId": scope.profile_id, "audio": True, "aspectPolicy": "cover_center_crop",
            "durationSeconds": 8, "frameCount": 192, "fps": 24, "profileVersion": 2,
            "quality": 8, "width": 832, "height": 480},
        "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
        "endFrame": first | {"revision": 1, "aspectPolicy": "cover_center_crop",
            "approvalId": "synthetic-current-approval", "storyboardRevision": 2,
            "sourceTiming": deepcopy(source),
            "provenance": [{"id": "synthetic-native-image-provenance", "declaration": {"method": "agent_image_job"}}]}}
    return scope, snapshot


@pytest.mark.parametrize("grant", ORIGINAL_FRAME_END_GRANTS, ids=lambda g:g.scope_id)
def test_only_exact_current_original_opening_image_may_guide_ending(grant):
    scope, snapshot = snapshot_for(grant)
    original = deepcopy(snapshot)
    assert_snapshot(scope, snapshot)
    assert snapshot == original
    for version in ("plotloom.h3-production-brief.v7", "plotloom.h3-production-brief.v8", "plotloom.h3-production-brief.v9"):
        snapshot["compilerVersion"] = version
        with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)
    snapshot["endFrame"] = {"revision": 0, "assetId": None}
    assert_snapshot(scope, snapshot)


@pytest.mark.parametrize(("section", "key", "value"), [
    ("endFrame", "assetId", "foreign-asset"), ("endFrame", "originalHash", "f"*64),
    ("endFrame", "revision", 0), ("endFrame", "revision", True),
    ("endFrame", "mimeType", "image/jpeg"), ("endFrame", "width", 640),
    ("endFrame", "height", 720.0), ("endFrame", "aspectPolicy", "contain_pad"),
    ("endFrame", "approvalId", "other-approval"), ("endFrame", "storyboardRevision", 3),
    ("endFrame", "sourceTiming", {"kind": "canonical"}),
    ("endFrame", "provenance", []), ("endFrame", "provenance", [{"id": "x", "declaration": {}}]),
    ("endFrame", "provenance", [{"declaration": {"method": "agent_image_job"}}]),
    ("request", "durationSeconds", 15), ("request", "frameCount", 360),
    ("request", "fps", 30), ("request", "quality", 1), ("request", "width", 1280),
    ("request", "profileVersion", 3), ("request", "audio", False),
    ("provider", "adapterId", "other-provider"),
    ("keyframe", "assetId", "other-first-image"), ("keyframe", "originalHash", "f"*64),
    ("shot", "id", "other-shot"),
])
def test_endpoint_grant_rejects_mismatched_or_expanded_request(section, key, value):
    scope, snapshot = snapshot_for(ORIGINAL_FRAME_END_GRANTS[0])
    snapshot[section][key] = value
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)


def test_scope_identity_empty_source_and_nonopening_materials_remain_closed():
    scope, snapshot = snapshot_for(ORIGINAL_FRAME_END_GRANTS[0])
    for altered in (replace(scope, id="unknown-scope"), replace(scope, project_id="foreign-project")):
        with pytest.raises(InvalidTransitionError): assert_snapshot(altered, snapshot)
    snapshot["sourceTiming"] = snapshot["endFrame"]["sourceTiming"] = {}
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)
    scope, snapshot = snapshot_for(ORIGINAL_FRAME_END_GRANTS[0])
    other = next(item for item in scope.materials if item.shot_id != snapshot["shot"]["id"])
    snapshot["shot"]["id"] = other.shot_id
    for frame in (snapshot["keyframe"], snapshot["endFrame"]):
        frame.update(assetId=other.asset_id, originalHash=other.original_hash)
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)
