"""One exact six-clip Su Tang preview grant; no enrollment or wider review authority."""
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from plotloom.contract_hash import stable_hash
from plotloom.delegated_qa import SCOPES, REVIEWER_PREFIX, binding_attribution, require_scope
from plotloom.delegated_qa_video import assert_snapshot
from plotloom.exceptions import InvalidTransitionError
from tests.test_minute_example_qa_scope import OLD_SCOPE_HASHES as PREEXISTING_SCOPE_HASHES

SCOPE = next(scope for scope in SCOPES if scope.id == "h5-sutang-preview-20261026")
ACTOR = {"kind": "agent_operated_qa", "scopeId": SCOPE.id}
OLD_SCOPE_HASHES = PREEXISTING_SCOPE_HASHES | {
    "minute-playable-example-20261023": "ad5aa30c0876699789c9fa5285b2c627e9dc4741791e612cc6a79fcc29276fc3",
}


def snapshot(material):
    return {
        "shot": {"id": material.shot_id},
        "keyframe": {"assetId": material.asset_id, "originalHash": material.original_hash},
        "request": {"profileId": SCOPE.profile_id, "audio": True, "aspectPolicy": "cover_center_crop"},
        "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
    }


def test_sutang_preview_registry_freezes_exact_current_material_and_preserves_all_nine():
    assert len(SCOPES) == 10
    assert {scope.id: stable_hash(asdict(scope)) for scope in SCOPES if scope.id != SCOPE.id} == OLD_SCOPE_HASHES
    assert stable_hash(asdict(SCOPE)) == "c40db7ef737a3fc3cbfc2565ccfc87b8576b0c00e94060a4f977963b8f46344c"
    assert SCOPE.project_id == "b9bc89b9-c7e3-4d6f-84c0-d2b493d4ccc6"
    assert SCOPE.storyboard_hash == "1b0b29a1df15481c68f304224717df8ac483e11ea9a4fc3d28ef239551122737"
    assert [material.shot_id for material in SCOPE.materials] == [f"SH{i:02d}" for i in range(1, 7)]
    assert len({material.asset_id for material in SCOPE.materials}) == 6
    assert SCOPE.profile_id == "minimax_h3_quality8_portrait_576x1024_v2"
    assert (SCOPE.max_submissions, SCOPE.max_requested_seconds) == (None, None)


@pytest.mark.parametrize("material", SCOPE.materials, ids=lambda material: material.shot_id)
def test_sutang_preview_admits_each_exact_material(material):
    assert require_scope(SCOPE.project_id, ACTOR) is SCOPE
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + SCOPE.id, content_hash=SCOPE.storyboard_hash)
    assert binding_attribution(SCOPE.project_id, approval, {"attribution": ACTOR},
        asset_id=material.asset_id, shot_id=material.shot_id) == ACTOR
    assert_snapshot(SCOPE, snapshot(material))


@pytest.mark.parametrize("change", ["board", "asset", "shot", "project", "scope"])
def test_sutang_preview_refuses_changed_review_identity(change):
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
def test_sutang_preview_refuses_expanded_media_or_provider_scope(change):
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
