"""Brief-owned Source structures and explicit retained-outline recovery."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from plotloom.branch_suggestions import BranchSuggestion, bind_branches
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.source_outline_contracts import (
    OutlineAcceptRequest,
    OutlineReopenRequest,
    OutlineReturnRequest,
    SectionMapGraphInstallRequest,
    compile_section_map_graph,
    validate_section_map_graph,
)
from plotloom.source_structures import complete_routes
from tests.creative_delivery_fixtures import _deliver_stage
from tests.graph_draft_fixtures import graph_draft_revision, graph_map_save_request
from tests.source_outline_fixtures import (
    _deliver,
    _material,
    _request,
    _storage,
)


def proposal(topology):
    return {
        "nodes": [
            {
                "id": node["id"],
                "title": f"Story {index}",
                "summary": f"Action in {node['kind']} {index}.",
            }
            for index, node in enumerate(topology["nodes"])
        ],
        "choices": [
            {
                "nodeId": node["id"],
                "question": "What does the protagonist do?",
                "options": [
                    {
                        "id": edge["id"],
                        "label": f"Action {index}",
                        "consequence": f"The protagonist takes action {index}.",
                    }
                    for index, edge in enumerate(topology["edges"])
                    if edge["sourceNodeId"] == node["id"]
                ],
            }
            for node in topology["nodes"]
            if node["kind"] == "decision"
        ],
        "joins": [
            {
                "id": join["id"],
                "reconciliation": "The characters acknowledge the different earlier actions before continuing together.",
            }
            for join in topology["joins"]
        ],
        "clarifications": ["Proposed wording for explicit author review."],
    }


@pytest.fixture
def store(tmp_path):
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    material = _material()
    store.save_source_material(expected_source_revision=0, material=material)
    request = _request(store.manifest.project_id, material)
    store.prepare_outline_candidate(request)
    store.admit_outline_delivery(_deliver(store, request))
    store.accept_outline_candidate(
        OutlineAcceptRequest(
            job_id=request.job_id,
            expected_source_revision=1,
            expected_outline_revision=0,
        )
    )
    yield store
    store.close()


def prepare(store):
    store.prepare_branch_candidate()
    return store.branch_candidate_request(store.branch_state().candidate.job_id)


def save_map(store, mapping):
    state = store.source_outline_state()
    return store.save_section_map(
        graph_map_save_request(
            store,
            expected_section_map_revision=state.accepted_section_map.revision
            if state.accepted_section_map
            else 0,
            expected_source_revision=state.source.revision,
            expected_outline_revision=state.accepted_outline.revision,
            expected_outline_content_hash=state.accepted_outline.content_hash,
            mapping=mapping,
        )
    )


def test_existing_outline_gets_complete_general_draft_without_mutating_canon(store):
    before = store.source_outline_state()
    request = prepare(store)
    topology = request.source["topology"]
    store.admit_branch_delivery(
        _deliver_stage(
            store, request, "branches.json", proposal(topology), "branches-ready"
        )
    )
    draft = store.branch_draft(request.job_id)
    assert draft.topology_origin == "planner"
    assert len(draft.sections) == 9
    assert sorted(len(choice.outcomes) for choice in draft.choices) == [2, 3]
    assert store.source_outline_state() == before
    graph = compile_section_map_graph(draft)
    validate_section_map_graph(graph, store.project().brief)
    routes = complete_routes(graph)
    assert len({route[-1] for route in routes}) == 3
    assert all(
        sum(
            any(
                edge.source_node_id == node and edge.kind.value == "choice"
                for edge in graph.edges
            )
            for node in route
        )
        == 2
        for route in routes
    )
    assert any(sum(route[-1] == other[-1] for other in routes) > 1 for route in routes)
    saved = save_map(store, draft)
    assert saved.accepted_section_map.mapping == draft
    assert saved.graph_admission is None
    assert saved.accepted_outline == before.accepted_outline
    with pytest.raises(CreativeHandoffError):
        store.branch_draft(request.job_id)
    source, outline, mapping = (
        saved.source,
        saved.accepted_outline,
        saved.accepted_section_map,
    )
    installed = store.install_section_map_graph(
        SectionMapGraphInstallRequest(
            expected_source_revision=source.revision,
            expected_source_content_hash=source.content_hash,
            expected_outline_revision=outline.revision,
            expected_outline_content_hash=outline.content_hash,
            expected_section_map_revision=mapping.revision,
            expected_section_map_content_hash=mapping.content_hash,
            expected_graph_revision=0,
            expected_graph_draft_revision=graph_draft_revision(store),
        )
    )
    assert installed.graph_admission.status == "current"
    candidate, cast = store.prepare_cast_candidate(
        "ch_" + "c" * 32, render_style="realistic"
    )
    assert len(candidate.binding.section_ids) == 9
    assert cast.input_artifacts["section-map.json"]["seedTopology"] == topology


def test_branch_candidate_report_is_stage_bound_read_only_and_available_only_when_ready(
    store,
):
    request = prepare(store)
    prepared = store.branch_state().candidate
    assert prepared.report_available is False
    with pytest.raises(NotFoundError):
        store.branch_candidate_report(request.job_id)

    delivery = _deliver_stage(
        store,
        request,
        "branches.json",
        proposal(request.source["topology"]),
        "branch-report",
    )
    original_report = delivery.report.decode("utf-8")
    store.admit_branch_delivery(delivery)
    before_outline = store.source_outline_state()
    before_candidate = store.branch_state().candidate
    assert before_candidate.status == "ready"
    assert before_candidate.report_available is True
    assert store.branch_candidate_report(request.job_id) == original_report
    assert store.source_outline_state() == before_outline
    assert store.branch_state().candidate == before_candidate

    # Both stages share one candidate table, so each reader must enforce its
    # own request discriminator before returning report HTML.
    with pytest.raises(NotFoundError):
        store.outline_candidate_report(request.job_id)


@pytest.mark.parametrize("change", ["source", "brief", "map", "revision"])
def test_changed_basis_rejects_delivery_and_adoption(store, change):
    request = prepare(store)
    content = proposal(request.source["topology"])
    delivery = _deliver_stage(
        store, request, "branches.json", content, "stale-branches"
    )
    if change == "source":
        store.cancel_branch_candidate(request.job_id)
        store.save_source_material(
            expected_source_revision=1,
            material=_material().model_copy(update={"text": "Different source."}),
        )
    elif change == "brief":
        project = store.project()
        store.update_brief(
            project.brief.model_copy(update={"genre": "Mystery"}),
            expected_revision=project.revision,
        )
    elif change == "map":
        mapping = bind_branches(
            BranchSuggestion.model_validate(content), request.source["topology"]
        )
        before = store.source_outline_state()
        with pytest.raises(InvalidTransitionError, match="active project work"):
            save_map(store, mapping)
        assert store.source_outline_state() == before
        assert store.branch_state().candidate.status == "prepared"
        store.cancel_branch_candidate(request.job_id)
        save_map(store, mapping)
    else:
        store.cancel_branch_candidate(request.job_id)
        store.reopen_outline(OutlineReopenRequest(expected_outline_revision=1))
    with pytest.raises((CreativeHandoffError, InvalidTransitionError)):
        store.admit_branch_delivery(delivery)
    assert store.source_outline_state().accepted_outline.revision == 1
    with pytest.raises((CreativeHandoffError, InvalidTransitionError)):
        store.branch_draft(request.job_id)


def test_ready_branch_can_be_cancelled_after_outline_reopen_without_changing_story(
    store,
):
    request = prepare(store)
    store.admit_branch_delivery(
        _deliver_stage(
            store,
            request,
            "branches.json",
            proposal(request.source["topology"]),
            "cancel-reopened",
        )
    )
    store.reopen_outline(OutlineReopenRequest(expected_outline_revision=1))
    before = store.source_outline_state()
    assert store.branch_state().stale_reasons
    with pytest.raises(InvalidTransitionError):
        store.branch_draft(request.job_id)
    store.cancel_branch_candidate(request.job_id)
    assert store.branch_state().candidate.status == "cancelled"
    assert store.source_outline_state() == before


@pytest.mark.parametrize("damage", ["question", "option", "node", "join"])
def test_malformed_suggestion_does_not_admit_or_discard_the_reservation(store, damage):
    request = prepare(store)
    invalid = proposal(request.source["topology"])
    if damage == "question":
        invalid["choices"][0]["question"] = "   "
    elif damage == "option":
        invalid["choices"][0]["options"][0]["id"] = "foreign-option"
    elif damage == "node":
        invalid["nodes"].pop()
    else:
        invalid["joins"][0]["reconciliation"] = "   "
    with pytest.raises(CreativeHandoffError) as error:
        store.admit_branch_delivery(
            _deliver_stage(store, request, "branches.json", invalid, "invalid-branches")
        )
    assert error.value.code == "delivery_candidate_invalid"
    assert store.branch_state().candidate.status == "prepared"
    assert store.source_outline_state().accepted_section_map is None


def test_infeasible_brief_refuses_preparation_without_changing_settings(store):
    project = store.project()
    brief = project.brief.model_copy(update={"node_budget": 3})
    store.update_brief(brief, expected_revision=project.revision)
    with pytest.raises(InvalidTransitionError):
        store.prepare_branch_candidate()
    state = store.branch_state()
    assert state.candidate is None and state.infeasible_reason
    assert store.project().brief == brief


def test_required_option_count_above_receiving_capacity_is_rejected_before_preparation(
    store,
):
    project = store.project()
    brief = project.brief.model_copy(
        update={
            "decision_points_per_path": 1,
            "ending_count": 7,
            "node_budget": 9,
            "max_out_degree": 7,
            "desired_join_count": 0,
        }
    )
    store.update_brief(brief, expected_revision=project.revision)
    with pytest.raises(InvalidTransitionError, match="6"):
        store.prepare_branch_candidate()
    assert store.branch_state().candidate is None
    assert store.project().brief == brief


def test_capacity_search_finds_a_larger_feasible_shape_without_rewriting_author_settings(
    store,
):
    project = store.project()
    brief = project.brief.model_copy(
        update={
            "decision_points_per_path": 2,
            "ending_count": 7,
            "node_budget": 20,
            "max_out_degree": 7,
            "desired_join_count": 1,
        }
    )
    store.update_brief(brief, expected_revision=project.revision)
    request = prepare(store)
    topology = request.source["topology"]
    assert topology["structuralParameters"]["maxOutDegree"] == 7
    assert len(topology["nodes"]) == 16
    assert all(len(choice["options"]) <= 6 for choice in proposal(topology)["choices"])
    store.admit_branch_delivery(
        _deliver_stage(
            store, request, "branches.json", proposal(topology), "within-capacity"
        )
    )
    assert (
        store.branch_draft(request.job_id).seed_topology.structural_parameters[
            "maxOutDegree"
        ]
        == 7
    )
    assert store.project().brief == brief


@pytest.mark.parametrize("command", ["validate", "render"])
def test_branch_cli_binds_prose_to_the_frozen_package_before_output(
    store, tmp_path, command
):
    request = prepare(store)
    paths = store.creative_handoff_exchange().verified_package_paths(
        request, store.creative_handoff_execution_pin(request)
    )
    candidate = tmp_path / "branches.json"
    content = proposal(request.source["topology"])
    candidate.write_text(json.dumps(content), encoding="utf-8")
    arguments = [
        sys.executable,
        "scripts/branch_suggestion.py",
        command,
        str(candidate),
        "--request",
        str(Path(paths["packagePath"]) / "request.json"),
    ]
    valid = subprocess.run(arguments, capture_output=True, text=True, check=False)
    assert valid.returncode == 0, valid.stderr
    assert (
        "valid advisory" if command == "validate" else "播放时显示的问题"
    ) in valid.stdout
    content["choices"][0]["options"][0]["id"] = "foreign-option"
    candidate.write_text(json.dumps(content), encoding="utf-8")
    invalid = subprocess.run(arguments, capture_output=True, text=True, check=False)
    assert invalid.returncode != 0
    assert not invalid.stdout


def test_explicit_return_retains_identity_and_refuses_changed_source_or_candidate(
    store,
):
    before = store.source_outline_state()
    store.reopen_outline(OutlineReopenRequest(expected_outline_revision=1))
    request = _request(store.manifest.project_id, before.source.material, 1, "b")
    store.prepare_outline_candidate(request)
    return_request = OutlineReturnRequest(
        expected_outline_revision=1,
        expected_source_revision=1,
        expected_outline_content_hash=before.accepted_outline.content_hash,
        expected_candidate_job_id=request.job_id,
    )
    with pytest.raises(InvalidTransitionError, match="变化"):
        store.return_to_accepted_outline(
            return_request.model_copy(update={"expected_candidate_job_id": None})
        )
    restored = store.return_to_accepted_outline(return_request)
    assert restored.outline_status == "accepted"
    assert restored.accepted_outline == before.accepted_outline
    assert restored.candidate is None
    assert store.outline_candidate_report(
        before.accepted_outline.candidate_job_id
    ).startswith("<!doctype")
    store.save_source_material(
        expected_source_revision=1,
        material=before.source.material.model_copy(update={"text": "已改变的来源。"}),
    )
    with pytest.raises(InvalidTransitionError, match="不适用"):
        store.return_to_accepted_outline(
            return_request.model_copy(
                update={
                    "expected_source_revision": 2,
                    "expected_candidate_job_id": None,
                }
            )
        )
