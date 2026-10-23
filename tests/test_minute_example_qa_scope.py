"""One exact minute-example grant; no enrollment or wider review authority."""
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from plotloom.contract_hash import stable_hash
from plotloom.delegated_qa import SCOPES, REVIEWER_PREFIX, binding_attribution, require_scope
from plotloom.delegated_qa_video import assert_snapshot
from plotloom.exceptions import InvalidTransitionError
from tests.test_finished_example_qa_scopes import PREEXISTING_SCOPE_HASHES

SCOPE = next(scope for scope in SCOPES if scope.id == "minute-playable-example-20261023")
ACTOR = {"kind": "agent_operated_qa", "scopeId": SCOPE.id}
OLD_SCOPE_HASHES = PREEXISTING_SCOPE_HASHES | {
    "playable-example-watercolor-20261022": "89f4db85a6876f5dacf6ae4be05afa6adb5050cb4e1a569fa3124fe25dcc6186",
    "playable-example-cinematic-20261022": "810243f9966c93a51d79e943ea9ee2dd053112d9d4150b96ac75412b77358103",
    "playable-example-stylized3d-20261022": "bc54c1787cd93b516837c86afdc18d18aa9424f82e18712877002d01a737d7b3",
}


def snapshot(material):
    return {
        "shot": {"id": material.shot_id},
        "keyframe": {"assetId": material.asset_id, "originalHash": material.original_hash},
        "request": {"profileId": SCOPE.profile_id, "audio": True, "aspectPolicy": "cover_center_crop"},
        "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
    }


def test_minute_example_registry_freezes_exact_current_material_and_preserves_all_eight():
    assert len(SCOPES) == 9
    assert {scope.id: stable_hash(asdict(scope)) for scope in SCOPES if scope.id != SCOPE.id} == OLD_SCOPE_HASHES
    assert stable_hash(asdict(SCOPE)) == "ad5aa30c0876699789c9fa5285b2c627e9dc4741791e612cc6a79fcc29276fc3"
    assert SCOPE.project_id == "df6bcbc9-c2a9-4274-a8e3-5db3735bf95f"
    assert SCOPE.storyboard_hash == "d3acc99f43e3a3c28fbb794637c0a40341fd24ca50b37af4a5668ebcf02b8531"
    assert [material.shot_id for material in SCOPE.materials] == [f"SH{i:02d}" for i in range(1, 10)]
    assert len({material.asset_id for material in SCOPE.materials}) == 9
    assert SCOPE.profile_id == "minimax_h3_quality8_portrait_576x1024_v2"
    assert (SCOPE.max_submissions, SCOPE.max_requested_seconds) == (None, None)


@pytest.mark.parametrize("material", SCOPE.materials, ids=lambda material: material.shot_id)
def test_minute_example_admits_each_exact_material(material):
    assert require_scope(SCOPE.project_id, ACTOR) is SCOPE
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + SCOPE.id, content_hash=SCOPE.storyboard_hash)
    assert binding_attribution(SCOPE.project_id, approval, {"attribution": ACTOR},
        asset_id=material.asset_id, shot_id=material.shot_id) == ACTOR
    assert_snapshot(SCOPE, snapshot(material))


@pytest.mark.parametrize("change", ["board", "asset", "shot", "project", "scope"])
def test_minute_example_refuses_changed_review_identity(change):
    material = SCOPE.materials[0]
    actor = ACTOR | ({"scopeId": "ungranted"} if change == "scope" else {})
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + actor["scopeId"],
        content_hash="0" * 64 if change == "board" else SCOPE.storyboard_hash)
    with pytest.raises(InvalidTransitionError):
        binding_attribution("ungranted-project" if change == "project" else SCOPE.project_id,
            approval, {"attribution": actor},
            asset_id="ungranted-asset" if change == "asset" else material.asset_id,
            shot_id="SH10" if change == "shot" else material.shot_id)


@pytest.mark.parametrize("change", ["asset", "shot", "original", "profile", "audio", "crop", "provider", "end_frame"])
def test_minute_example_refuses_expanded_media_or_provider_scope(change):
    candidate = deepcopy(snapshot(SCOPE.materials[0]))
    if change == "asset": candidate["keyframe"]["assetId"] = "ungranted-asset"
    if change == "shot": candidate["shot"]["id"] = "SH10"
    if change == "original": candidate["keyframe"]["originalHash"] = "0" * 64
    if change == "profile": candidate["request"]["profileId"] = "another-profile"
    if change == "audio": candidate["request"]["audio"] = False
    if change == "crop": candidate["request"]["aspectPolicy"] = "contain_pad"
    if change == "provider": candidate["provider"]["adapterId"] = "another-provider"
    if change == "end_frame": candidate["endFrame"] = {"revision": 1, "assetId": "ungranted-frame"}
    with pytest.raises(InvalidTransitionError, match="exact QA material"):
        assert_snapshot(SCOPE, candidate)
