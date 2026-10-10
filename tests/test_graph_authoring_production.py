"""Current source graph → exact F4/F5 subset → first production installation."""

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.source_outline_contracts import SectionMap
from plotloom.source_structures import complete_routes
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.test_graph_authoring_contract import authored_map
from tests.test_project_storage_source_outline import _storage


@pytest.mark.parametrize("include_controls", [False, True])
def test_three_routes_inserted_step_and_join_install_exact_footage_subset(
    tmp_path, include_controls
):
    storage = _storage(tmp_path)
    store = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(
            update={
                "node_budget": 12,
                "decision_points_per_path": 1,
                "ending_count": 1,
                "max_out_degree": 3,
                "desired_join_count": 1,
                "target_playthrough_seconds": 180,
            }
        )
    )

    def structure(owner):
        mapping = authored_map(owner)
        if include_controls:
            data = mapping.model_dump(mode="json", by_alias=True)
            for section in data["sections"]:
                section["footageMode"] = "footage"
            mapping = SectionMap.model_validate(data)
        return mapping

    try:
        proposal = _prepare_installable_bridge(store, structure_factory=structure)
        mapping = store.source_outline_state().accepted_section_map.mapping
        expected = [
            section.section_id
            for section in mapping.sections
            if section.footage_mode == "footage"
        ]
        controls = [] if include_controls else ["choose", "merge"]
        script = store.script_state().accepted_script
        assert script.binding.section_ids == [
            section.section_id for section in mapping.sections
        ]
        assert script.binding.route_only_section_ids == controls
        assert [item.section_id for item in script.binding.section_bindings] == expected
        assert len(script.binding.route_budget_hash) == 64
        assert len(script.script["episodes"]) == len(expected)
        assert all(episode["scenes"] for episode in script.script["episodes"])
        assert [scene["sectionId"] for scene in proposal.scenes] == expected
        assert len(proposal.cuts) == len(expected) * 9
        assert all(cut["sectionId"] in expected for cut in proposal.cuts)
        accepted = store.accept_production_bridge(
            ProductionBridgeAcceptRequest(
                expected_proposal_revision=proposal.revision,
                expected_content_hash=proposal.content_hash,
            )
        )
        assert accepted.installation.status == "current"
        graph = store.authoring.get_stage_payload(
            store.manifest.project_id, StageName.STORY_GRAPH
        )
        plan = store.authoring.get_stage_payload(
            store.manifest.project_id, StageName.SCENE_BEATS
        )
        board = store.authoring.get_stage_payload(
            store.manifest.project_id, StageName.STORYBOARD
        )
        assert [scene.story_node_id for scene in plan.scenes] == expected
        assert len(board.shots) == len(expected) * 9
        routes = complete_routes(graph)
        assert len(routes) == 3
        assert all("choose" in route and "merge" in route for route in routes)
        assert next(
            edge for edge in graph.edges if edge.id == "branch-input"
        ).state_effects == {
            "retainedFact": "original traversal",
        }
        assert (
            accepted.installation.runtime_choice["choices"][0]["sectionId"] == "choose"
        )
        assert [
            outcome["outcomeId"]
            for outcome in accepted.installation.runtime_choice["choices"][0][
                "outcomes"
            ]
        ] == [
            "option-123",
            "option-222",
            "option-333",
        ]
    finally:
        store.close()
