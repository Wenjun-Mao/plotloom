"""Prospective example grants preserve the existing exact admission boundaries."""
from types import SimpleNamespace

import pytest

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


def test_finished_example_registry_is_exactly_the_three_authorized_projects():
    assert {scope.id: scope.project_id for scope in EXAMPLE_SCOPES} == {
        "finished-example-watercolor-20261022": "ad20c897-e263-402d-9333-82de890a6038",
        "finished-example-cinematic-20261022": "d7deb82f-4801-4c9f-bfa8-9195c3b36489",
        "finished-example-stylized3d-20261022": "21dd0cbd-3ba9-4cfa-927a-88a877b047ea",
    }
    assert len(SCOPES) == 4


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
