"""Prospective example grants preserve the existing exact admission boundaries."""
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from plotloom.contract_hash import stable_hash
from plotloom.delegated_qa import (
    REVIEWER_PREFIX,
    SCOPES,
    binding_attribution,
    require_scope,
)
from plotloom.delegated_qa_contracts import AgentQaAttribution
from plotloom.delegated_qa_video import assert_snapshot
from plotloom.exceptions import InvalidTransitionError

EXAMPLE_SCOPES = tuple(scope for scope in SCOPES if scope.id.startswith("finished-example-"))
PLAYABLE_SCOPES = tuple(scope for scope in SCOPES if scope.id.startswith("playable-example-"))

PREEXISTING_SCOPE_HASHES = {
    "disposable-qa-20261019": "cd85ea471974c84485028f4471912d45877ddcb226067e0f64e72f3ebcd5a080",
    "finished-example-watercolor-20261022": "5e6d9354783bb6d7a4aeb51049ef98e8375737f845d495a9b66749dd4f8e2403",
    "finished-example-cinematic-20261022": "545d3f4fa82bee5aabbae6cca99607f86a1831666bd636c28ab655f4952536d1",
    "finished-example-stylized3d-20261022": "73aa07ad2da7476923b23a44f8947a235ead49998a50e12a7088b78ef88f549a",
    "creator-completion-native-20261022": "aec7a5acc8ed3ea81eca3a3e3a01a321a51d9ea29332452aa19c00b96a6ab1a1",
}


def test_finished_example_registry_remains_the_three_original_projects():
    assert {scope.id: scope.project_id for scope in EXAMPLE_SCOPES} == {
        "finished-example-watercolor-20261022": "ad20c897-e263-402d-9333-82de890a6038",
        "finished-example-cinematic-20261022": "d7deb82f-4801-4c9f-bfa8-9195c3b36489",
        "finished-example-stylized3d-20261022": "21dd0cbd-3ba9-4cfa-927a-88a877b047ea",
    }


def test_playable_example_registry_freezes_exact_new_projects_and_preserves_old_five():
    expected = {
        "playable-example-watercolor-20261022": (
            "7304da14-c3aa-40aa-9b5b-236d6979ac25",
            "db1e06c758cd35b6fc5b31c64e247e2e8dcd81e3410e28607bf3e721f1098858",
            (
                ("SH01", "e6768a75-cbc3-468b-b9cc-a9af541004ff", "bf597b2edc2014e1f1abf4f2d66e9babba36921c2dc9ed978f19f0fced9064be"),
                ("SH02", "90ab0914-27ac-461e-9e50-ad5dbf9685fc", "f67b2c4f02397415c7bca38f145bf2d55be45d671f8c7686c8526f1a3c9f4081"),
                ("SH03", "1ba4e87a-9a55-479a-9769-9978b3d2ac7e", "ba5af56db0b1c639414109bd02cd91e52c4029f916dae74014e084825cb4e315"),
            ),
        ),
        "playable-example-cinematic-20261022": (
            "7690e55d-3f08-4056-8f7b-8455814c4928",
            "d7f332d31144e20fa3623794360ab76187c418997ca866ab96776552ea419536",
            (
                ("SH01", "bc7a9965-db5b-4fc9-ab9c-5903f41fcc27", "17edc858aa790890becd87f2eaec55efbd1985e50de758b0ffe9ec47982a022e"),
                ("SH02", "9482a310-e1c6-4de7-9717-2f78948e0985", "7ebfb532b5c2b82090b0f6042198c534454d270a1c59654288f83a1008a670e8"),
                ("SH03", "d651393d-3a0e-444e-abcb-b5805569ddf7", "1ff62ad7f5889057509963c6dbd8c33a702667f9b79d9ef04648870792c27a06"),
            ),
        ),
        "playable-example-stylized3d-20261022": (
            "02a9c60d-9b37-46fd-9446-806cb0aa8a1f",
            "1a44ab0d29d1aec108dd1899e774e75f28a099e59d01a3ba7fb9a5d99be8c848",
            (
                ("SH01", "f1a8a840-3886-41f7-a7e6-a32977d7a0da", "ce9cfcbf6686b565aeeb0a58f525181065fab76c15befa1cb37fc3abd10c1afa"),
                ("SH02", "8a3a5750-77b5-4af3-8a60-028e94bc5782", "d31e5dbf98631e9b9c8eef830d83c598f67dbf30ee5646782112141be456a2c4"),
                ("SH03", "525a22ea-8baf-4283-9f1c-f66b45d7484c", "06b4c30185600b3cd29bca17c812113400067f8272e6c7cd423885890ba2e9fb"),
            ),
        ),
    }
    actual = {
        scope.id: (
            scope.project_id,
            scope.storyboard_hash,
            tuple((item.shot_id, item.asset_id, item.original_hash) for item in scope.materials),
        )
        for scope in PLAYABLE_SCOPES
    }
    assert actual == expected
    assert len(PLAYABLE_SCOPES) == 3
    assert all(scope.profile_id == "minimax_h3_quality8_portrait_576x1024_v2"
        and (scope.max_submissions, scope.max_requested_seconds) == (None, None) for scope in PLAYABLE_SCOPES)
    prior = {scope.id: stable_hash(asdict(scope)) for scope in SCOPES
        if not scope.id.startswith("playable-example-") and scope.id not in {"minute-playable-example-20261023", "h5-sutang-preview-20261026"}}
    assert prior == PREEXISTING_SCOPE_HASHES
    assert len(SCOPES) == 10


@pytest.mark.parametrize("scope", EXAMPLE_SCOPES, ids=lambda scope: scope.id)
def test_finished_example_grant_admits_only_its_exact_material(scope):
    actor = AgentQaAttribution(scope_id=scope.id).model_dump(mode="json", by_alias=True)
    assert require_scope(scope.project_id, actor) is scope
    assert [item.shot_id for item in scope.materials] == ["SH01", "SH02"]
    assert scope.profile_id == "minimax_h3_quality8_portrait_576x1024_v2"
    assert (scope.max_submissions, scope.max_requested_seconds) == (None, None)
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + scope.id, content_hash=scope.storyboard_hash)
    for material in scope.materials:
        assert binding_attribution(scope.project_id, approval, {"attribution": actor},
            asset_id=material.asset_id, shot_id=material.shot_id) == actor
        assert_snapshot(scope, {
            "shot": {"id": material.shot_id},
            "keyframe": {"assetId": material.asset_id, "originalHash": material.original_hash},
            "request": {"profileId": scope.profile_id, "audio": True, "aspectPolicy": "cover_center_crop"},
            "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
        })


@pytest.mark.parametrize("scope", EXAMPLE_SCOPES, ids=lambda scope: scope.id)
@pytest.mark.parametrize("change", ["board", "asset", "shot", "project", "original_hash"])
def test_finished_example_grant_refuses_expanded_scope(scope, change):
    actor = AgentQaAttribution(scope_id=scope.id).model_dump(mode="json", by_alias=True)
    material = scope.materials[0]
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + scope.id,
        content_hash="0" * 64 if change == "board" else scope.storyboard_hash)
    if change == "original_hash":
        with pytest.raises(InvalidTransitionError, match="exact QA material"):
            assert_snapshot(scope, {
                "shot": {"id": material.shot_id},
                "keyframe": {"assetId": material.asset_id, "originalHash": "0" * 64},
                "request": {"profileId": scope.profile_id, "audio": True, "aspectPolicy": "cover_center_crop"},
                "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
            })
        return
    with pytest.raises(InvalidTransitionError):
        binding_attribution("ungranted-project" if change == "project" else scope.project_id,
            approval, {"attribution": actor},
            asset_id="ungranted-asset" if change == "asset" else material.asset_id,
            shot_id="SH03" if change == "shot" else material.shot_id)


@pytest.mark.parametrize("scope", PLAYABLE_SCOPES, ids=lambda scope: scope.id)
def test_playable_example_grant_admits_all_three_exact_materials(scope):
    actor = AgentQaAttribution(scope_id=scope.id).model_dump(mode="json", by_alias=True)
    assert require_scope(scope.project_id, actor) is scope
    assert [item.shot_id for item in scope.materials] == ["SH01", "SH02", "SH03"]
    assert scope.profile_id == "minimax_h3_quality8_portrait_576x1024_v2"
    assert (scope.max_submissions, scope.max_requested_seconds) == (None, None)
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + scope.id, content_hash=scope.storyboard_hash)
    for material in scope.materials:
        assert binding_attribution(scope.project_id, approval, {"attribution": actor},
            asset_id=material.asset_id, shot_id=material.shot_id) == actor
        assert_snapshot(scope, {
            "shot": {"id": material.shot_id},
            "keyframe": {"assetId": material.asset_id, "originalHash": material.original_hash},
            "request": {"profileId": scope.profile_id, "audio": True, "aspectPolicy": "cover_center_crop"},
            "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
        })


@pytest.mark.parametrize("scope", PLAYABLE_SCOPES, ids=lambda scope: scope.id)
@pytest.mark.parametrize("change", ["board", "asset", "shot", "project", "original_hash"])
def test_playable_example_grant_refuses_material_outside_its_exact_scope(scope, change):
    actor = AgentQaAttribution(scope_id=scope.id).model_dump(mode="json", by_alias=True)
    material = scope.materials[0]
    approval = SimpleNamespace(reviewer=REVIEWER_PREFIX + scope.id,
        content_hash="0" * 64 if change == "board" else scope.storyboard_hash)
    if change == "original_hash":
        with pytest.raises(InvalidTransitionError, match="exact QA material"):
            assert_snapshot(scope, {
                "shot": {"id": material.shot_id},
                "keyframe": {"assetId": material.asset_id, "originalHash": "0" * 64},
                "request": {"profileId": scope.profile_id, "audio": True, "aspectPolicy": "cover_center_crop"},
                "provider": {"adapterId": "minimax_h3_gateway", "costPolicy": "local_capacity_v1"},
            })
        return
    with pytest.raises(InvalidTransitionError):
        binding_attribution("ungranted-project" if change == "project" else scope.project_id,
            approval, {"attribution": actor},
            asset_id="ungranted-asset" if change == "asset" else material.asset_id,
            shot_id="SH04" if change == "shot" else material.shot_id)
