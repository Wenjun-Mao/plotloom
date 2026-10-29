"""New resolution authority remains confined to the exact two native bundles."""
from copy import deepcopy
from dataclasses import replace

import pytest

from plotloom.delegated_qa_end_frames import ORIGINAL_FRAME_END_GRANTS
from plotloom.delegated_qa_video import assert_snapshot
from plotloom.delegated_qa_video_profiles import (
    HIGH_RESOLUTION_PROFILE,
    manifest_profile_within_authority,
)
from plotloom.exceptions import InvalidTransitionError
from tests.test_qa_original_frame_end import snapshot_for


def high_resolution(grant):
    scope, snapshot = snapshot_for(grant)
    snapshot["compilerVersion"] = "plotloom.h3-production-brief.v11"
    snapshot["request"].update(profileId=HIGH_RESOLUTION_PROFILE,
        resolution="1280x704", width=1280, height=704)
    return scope, snapshot


@pytest.mark.parametrize("grant", ORIGINAL_FRAME_END_GRANTS, ids=lambda item:item.scope_id)
def test_current_high_resolution_binds_exact_scope_and_every_existing_material(grant):
    scope, snapshot = high_resolution(grant)
    original = deepcopy(snapshot)
    assert_snapshot(scope, snapshot)
    assert snapshot == original
    snapshot["endFrame"] = {"revision": 0, "assetId": None}
    for material in scope.materials:
        snapshot["shot"]["id"] = material.shot_id
        snapshot["keyframe"].update(assetId=material.asset_id, originalHash=material.original_hash)
        assert_snapshot(scope, snapshot)
    snapshot["keyframe"]["originalHash"] = "f"*64
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)


@pytest.mark.parametrize("version", ["v7", "v8", "v9", "v10"])
def test_old_snapshots_cannot_acquire_high_resolution_authority(version):
    scope, snapshot = high_resolution(ORIGINAL_FRAME_END_GRANTS[0])
    snapshot["compilerVersion"] = "plotloom.h3-production-brief." + version
    snapshot["endFrame"] = {"revision": 0, "assetId": None}
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)


@pytest.mark.parametrize(("key", "value"), [
    ("profileId", "minimax_h3_quality1_landscape_1280x704_v2"),
    ("resolution", "832x480"), ("width", 832), ("height", 720),
    ("quality", 1), ("profileVersion", 3), ("durationSeconds", 15),
    ("frameCount", 360), ("fps", 30), ("fps", 24.0),
    ("audio", False), ("aspectPolicy", "contain_pad"),
])
def test_new_profile_does_not_expand_output_timing_audio_or_crop(key, value):
    scope, snapshot = high_resolution(ORIGINAL_FRAME_END_GRANTS[0])
    snapshot["request"][key] = value
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)


def test_project_scope_digest_nonopening_end_and_mixed_manifests_remain_closed():
    scope, snapshot = high_resolution(ORIGINAL_FRAME_END_GRANTS[0])
    for other in (replace(scope, id="foreign-scope"), replace(scope, project_id="foreign-project"),
                  replace(scope, material_closure="f"*64)):
        with pytest.raises(InvalidTransitionError): assert_snapshot(other, snapshot)
    manifest = {"setup": {"profileId": HIGH_RESOLUTION_PROFILE}, "targets": [{"snapshot": snapshot}]}
    assert manifest_profile_within_authority(scope, manifest)
    manifest["setup"]["profileId"] = scope.profile_id
    assert not manifest_profile_within_authority(scope, manifest)
    manifest["setup"]["profileId"] = HIGH_RESOLUTION_PROFILE
    snapshot["compilerVersion"] = "plotloom.h3-production-brief.v10"
    assert not manifest_profile_within_authority(scope, manifest)
    snapshot["compilerVersion"] = "plotloom.h3-production-brief.v11"
    material = next(m for m in scope.materials if m.shot_id != snapshot["shot"]["id"])
    snapshot["shot"]["id"] = material.shot_id
    for frame in (snapshot["keyframe"], snapshot["endFrame"]):
        frame.update(assetId=material.asset_id, originalHash=material.original_hash)
    with pytest.raises(InvalidTransitionError): assert_snapshot(scope, snapshot)
