"""Unequal author timing remains route-safe through F4, F5 and installation."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from plotloom.art_contracts import ArtAcceptRequest
from plotloom.authored_route_timing import (
    longest_authored_route_units,
    route_budget_hash,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.persistence.project.script import _validate_timing_caps
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.script_contracts import ScriptAcceptRequest, ScriptBinding
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from plotloom.validation_issues import DomainValidationError
from plotloom.validation_scene import _validate_v2_scene_timing_allocation
from tests.art_delivery_fixtures import _deliver
from tests.creative_delivery_fixtures import (
    _deliver_stage,
    _pilot_script,
    _prepare_art_context,
)
from tests.generation.test_scene_timing_allocation import _layered_graph
from tests.production_bridge_fixtures import (
    _review_fixture_presentation,
    _source_shaped_review_board,
)


def test_longest_route_counts_joins_once_and_accepts_uneven_scenes():
    graph = _layered_graph()
    graph = graph.model_copy(
        update={
            "nodes": [
                node.model_copy(update={"footage_mode": "route_only"})
                if node.id in {"decision", "join"}
                else node
                for node in graph.nodes
            ]
        }
    )
    durations = {"start": 9000, "left": 1000, "right": 4000, "ending": 2000}
    assert longest_authored_route_units(graph, durations) == 15000
    plan = SimpleNamespace(
        scenes=[
            SimpleNamespace(story_node_id=node, duration_budget_units=value)
            for node, value in durations.items()
        ]
    )
    plan.scenes[0].duration_budget_units = 4000
    plan.scenes.append(
        SimpleNamespace(story_node_id="start", duration_budget_units=5000)
    )
    brief = FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 15})
    _validate_v2_scene_timing_allocation(plan, graph, brief)
    plan.scenes[-1].duration_budget_units += 1
    with pytest.raises(DomainValidationError) as failure:
        _validate_v2_scene_timing_allocation(plan, graph, brief)
    assert failure.value.issues[0]["code"] == "scene_route_budget_exceeded"
    with pytest.raises(ValueError, match="route-only"):
        longest_authored_route_units(graph, durations | {"join": 1})
    shortcut = graph.edges[0].model_copy(
        update={"id": "shortcut", "target_node_id": "ending"}
    )
    assert (
        longest_authored_route_units(
            graph.model_copy(update={"edges": [*graph.edges, shortcut]}), durations
        )
        == 15000
    )


def _uneven_board():
    board = _source_shaped_review_board(5)
    for ep in board["episodes"]:
        segment = ep["segments"][0]
        count = 2 if ep["ep"] == 1 else 1
        segment["cuts"] = segment["cuts"][:count]
        for index, cut in enumerate(segment["cuts"]):
            cut["beats"] = [index * 2 + 1, index * 2 + 2]
        alignment = "; ".join(
            f"Picture {i + 1} (from Shot {i + 1}) aligns with the {i * 5:.2f}-second mark of the target video"
            for i in range(count)
        )
        shots = "[Shot 1] Cinematic, live-action, cool gray palette. The empty beacon room of <Picture 1> holds while the camera uses a static shot."
        if count == 2:
            shots += "\n[Shot 2] At 00:05.000, the camera cuts to <Picture 2> and holds a static shot in the empty beacon room."
        first_line = (
            f"How the reference pictures align with the target video — {alignment}."
            if count == 2
            else "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
        )
        segment["h3Prompt"] = (
            f"{first_line}\n\nintegrated_multimodal_description:\n{shots}\n\noverall_soundscape: Quiet wind around an empty beacon room.\n\nnon_diegetic_music: N/A"
        )
        ep["segments"] = [segment]
    return board


@pytest.fixture
def prepared_uneven_script(tmp_path):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 15})
    )
    try:
        art_binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate(
            "ch_" + "k" * 32, render_style="realistic"
        )
        ready = store.admit_art_delivery(_deliver(store, request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=candidate.job_id,
                expected_art_revision=0,
                binding=art_binding,
                art=ready.art,
            )
        )
        candidate, request = store.prepare_script_candidate("ch_" + "l" * 32)
        script = _pilot_script()
        for ep in script["episodes"]:
            count = 4 if ep["ep"] == 1 else 2
            ep["targetSeconds"] = count * 2.5
            ep["scenes"][0]["flow"] = ep["scenes"][0]["flow"][:count]
        yield store, candidate, request, script
    finally:
        store.close()


def test_unequal_timing_installs_without_relaxing_upstream_validation(
    prepared_uneven_script,
):
    store, candidate, request, script = prepared_uneven_script
    ready = store.admit_script_delivery(
        _deliver_stage(store, request, "script.json", script, "uneven-script")
    )
    store.accept_script_candidate(
        ScriptAcceptRequest(
            job_id=candidate.job_id,
            expected_script_revision=0,
            binding=ready.binding,
            script=ready.script,
        )
    )
    board_candidate, board_request = store.prepare_storyboard_review_candidate(
        "ch_" + "b" * 32
    )
    assert (
        board_request.input_artifacts["storyboard-admission.json"][
            "targetPlaythroughSeconds"
        ]
        == 15
    )
    board_ready = store.admit_storyboard_review_delivery(
        _deliver_stage(
            store, board_request, "storyboard.json", _uneven_board(), "uneven-board"
        )
    )
    store.accept_storyboard_review_candidate(
        StoryboardReviewAcceptRequest(
            job_id=board_candidate.job_id,
            expected_review_revision=0,
            binding=board_ready.binding,
        )
    )
    proposal = store.prepare_production_bridge(
        store.production_bridge_state().preparation.request
    ).proposal
    proposal = _review_fixture_presentation(store, proposal)
    proposal = store.update_production_bridge_intent_package(
        ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
            entries=[
                {"id": entry.id, "text": "作者审核的戏剧目的"}
                for entry in proposal.intent_package.entries
            ],
        )
    ).proposal
    assert proposal.installable, proposal.conflicts
    accepted = store.accept_production_bridge(
        ProductionBridgeAcceptRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
        )
    )
    assert accepted.installation.status == "current"
    plan = store.authoring.get_stage_payload(
        store.manifest.project_id, StageName.SCENE_BEATS
    )
    assert sorted(scene.duration_budget_units for scene in plan.scenes) == [
        5000,
        5000,
        10000,
    ]


@pytest.mark.parametrize("field", ["target", "est"])
def test_script_validates_both_complete_route_totals(prepared_uneven_script, field):
    _store, candidate, _request, script = prepared_uneven_script
    stats = {
        "episodes": [
            {"ep": ep, "target": seconds, "est": seconds}
            for ep, seconds in ((1, 10), (2, 5), (3, 5))
        ]
    }
    _validate_timing_caps(script, candidate.binding, stats)
    stats["episodes"][2][field] = 5.1
    with pytest.raises(
        ValueError,
        match=f"complete script {'target' if field == 'target' else 'estimated'} route",
    ):
        _validate_timing_caps(script, candidate.binding, stats)


def test_route_hash_rejects_mutated_targets_and_removed_caps(prepared_uneven_script):
    _store, candidate, _request, _script = prepared_uneven_script
    raw = candidate.binding.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValueError, match="routeBudgetHash"):
        ScriptBinding.model_validate(raw | {"targetPlaythroughSeconds": 16})
    with pytest.raises(ValueError):
        ScriptBinding.model_validate(raw | {"sectionDurationCaps": []})
    changed = deepcopy(raw["completeRouteSectionIds"])
    changed.reverse()
    assert (
        route_budget_hash(
            target_seconds=15,
            section_bindings=raw["sectionBindings"],
            routes=changed,
            route_only_ids=raw["routeOnlySectionIds"],
        )
        != raw["routeBudgetHash"]
    )


def test_overlong_delivery_leaves_script_unaccepted(prepared_uneven_script):
    store, candidate, request, script = prepared_uneven_script
    opening = script["episodes"][0]
    opening["targetSeconds"] = 12.5
    opening["scenes"][0]["flow"].append({"action": "Lin holds at the doorway."})
    revision = store.project().revision
    with pytest.raises(ValueError, match="complete script estimated route"):
        store.admit_script_delivery(
            _deliver_stage(store, request, "script.json", script, "overlong-script")
        )
    assert store.project().revision == revision
    assert store.script_state().candidate.job_id == candidate.job_id
    assert store.script_state().candidate.status == "prepared"
    assert store.script_state().accepted_script is None
