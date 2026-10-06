"""Pure and persisted command proof; provider/job/media owners are never touched."""
import pytest

from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.graph_authoring_drafts import GraphAuthoringDraft
from plotloom.graph_command_execution import execute_graph_command
from plotloom.graph_commands import GraphCommandApplyRequest, GraphCommandRequest
from plotloom.persistence.project.graph_workbench import GraphDraftRebaseRequest
from tests.graph_draft_fixtures import save_graph_mapping
from tests.test_graph_authoring_contract import authored_map, source_project  # noqa: F401


def request(receipt, command):
    return GraphCommandRequest(expected_draft_revision=receipt.draft_revision, command=command)


def insert_command(**changes):
    return {"operation": "insert", "nodeId": "new-step", "kind": "scene", "rowHint": 3, "createPendingChoices": changes.get("kind") == "decision",
        "edgeId": "branch-input", "continuationEdgeId": "new-step-output"} | changes


def apply(store, receipt, command):
    preview = store.preview_graph_command(request(receipt, command))
    saved = store.apply_graph_command(GraphCommandApplyRequest(
        expected_draft_revision=receipt.draft_revision, command=command, preview_hash=preview.preview_hash))
    assert saved.payload == preview.result.model_dump(mode="json", by_alias=True)
    return saved, preview


def test_preview_cancel_insert_metadata_and_double_submission(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    preview = store.preview_graph_command(request(receipt, insert_command()))
    assert store.graph_workbench_state().draft == receipt  # Cancel is no write.
    changed = next(edge for edge in preview.result.mapping.topology.edges if edge.id == "branch-input")
    assert changed.state_effects == {"retainedFact": "original traversal"}
    assert changed.target_node_id == "new-step"
    assert next(edge for edge in preview.result.mapping.topology.edges if edge.id == "new-step-output").target_node_id == "inserted-step"
    saved, again = apply(store, receipt, insert_command())
    assert again == preview
    with pytest.raises(RevisionConflictError):
        store.apply_graph_command(GraphCommandApplyRequest(expected_draft_revision=receipt.draft_revision,
            command=insert_command(), preview_hash=preview.preview_hash))
    assert store.graph_workbench_state().draft == saved
    assert store.authoring.get_stage_head(store.manifest.project_id, StageName.STORY_GRAPH).revision == 0


def test_stale_preview_and_changed_context_preserve_acknowledged_draft(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    preview = store.preview_graph_command(request(receipt, insert_command()))
    typed = dict(receipt.payload)
    typed["mapping"] = dict(typed["mapping"])
    typed["mapping"]["sections"] = [dict(section) for section in typed["mapping"]["sections"]]
    typed["mapping"]["sections"][0]["summary"] = "New prose after preview"
    saved = store.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=0,
        expected_draft_revision=receipt.draft_revision, payload=typed)
    with pytest.raises(RevisionConflictError):
        store.apply_graph_command(GraphCommandApplyRequest(expected_draft_revision=receipt.draft_revision,
            command=insert_command(), preview_hash=preview.preview_hash))
    assert store.graph_workbench_state().draft == saved
    fresh_preview = store.preview_graph_command(request(saved, insert_command()))
    project = store.project()
    store.update_brief(project.brief.model_copy(update={"target_playthrough_seconds": 240}), expected_revision=project.revision)
    with pytest.raises(RevisionConflictError, match="context"):
        store.apply_graph_command(GraphCommandApplyRequest(expected_draft_revision=saved.draft_revision,
            command=insert_command(), preview_hash=fresh_preview.preview_hash))
    state = store.graph_workbench_state()
    assert state.draft == saved
    recovered = store.rebase_graph_draft(GraphDraftRebaseRequest(expected_draft_revision=saved.draft_revision,
        expected_binding_hash=state.binding_hash, payload=None))
    assert recovered.payload["mapping"]["seedTopology"] == saved.payload["mapping"]["seedTopology"]
    assert recovered.payload["mapping"]["sections"] == saved.payload["mapping"]["sections"]
    assert recovered.payload["mapping"]["topologyOrigin"] == "author"


def test_only_delete_retains_both_endpoints_option_prose_and_effects(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    saved, preview = apply(store, receipt, {"operation": "delete", "nodeId": "branch-123", "method": "only_delete"})
    draft = GraphAuthoringDraft.model_validate(saved.payload)
    option = next(option for option in draft.mapping.choices[0].outcomes if option.outcome_id == "option-123")
    assert option.label == "123" and option.consequence == "Action 123." and option.ending_section_id is None
    outgoing = next(edge for edge in draft.mapping.topology.edges if edge.id == "branch-input")
    assert outgoing.source_node_id is None and outgoing.state_effects == {"retainedFact": "original traversal"}
    assert draft.detached_endpoints["option-123"]["target"].node_id == "branch-123"
    assert draft.detached_endpoints["branch-input"]["source"].title == "branch-123"
    assert "inserted-step" in preview.impact.retained_node_ids
    assert store.graph_workbench_state().draft.payload == saved.payload


def test_deleting_decision_preserves_detached_option_text_until_explicit_reassignment(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    saved, _ = apply(store, receipt, {"operation": "delete", "nodeId": "choose", "method": "only_delete"})
    options = saved.payload["mapping"]["choices"][0]["outcomes"]
    assert [(option["outcomeId"], option["label"], option["consequence"]) for option in options] == [
        (f"option-{number}", str(number), f"Action {number}.") for number in (123, 222, 333)]
    with pytest.raises(ValueError):
        GraphAuthoringDraft.model_validate(saved.payload).admitted_mapping()
    saved, _ = apply(store, saved, {"operation": "add", "nodeId": "new-choice", "kind": "decision", "rowHint": 1, "createPendingChoices": False,
        "sourceNodeId": None, "targetNodeId": None, "incomingEdgeId": "unused-input", "outgoingEdgeId": "unused-output"})
    for number in (123, 222, 333):
        saved, _ = apply(store, saved, {"operation": "retarget", "edgeId": f"option-{number}", "endpoint": "source", "nodeId": "new-choice"})
    choices = saved.payload["mapping"]["choices"]
    assert [choice["sectionId"] for choice in choices] == ["new-choice"]
    assert [(option["label"], option["consequence"]) for option in choices[0]["outcomes"]] == [(str(number), f"Action {number}.") for number in (123, 222, 333)]


@pytest.mark.parametrize("command,reason", [
    ({"operation": "delete", "nodeId": "opening", "method": "only_delete"}, "开场"),
    ({"operation": "delete", "nodeId": "choose", "method": "safe_bypass"}, "安全绕过"),
    ({"operation": "delete", "nodeId": "merge", "method": "safe_bypass"}, "单入口"),
    ({"operation": "retarget", "edgeId": "branch-input", "endpoint": "target", "nodeId": "branch-123"}, "self_link"),
    ({"operation": "retarget", "edgeId": "merge-ending", "endpoint": "target", "nodeId": "choose"}, "cycle"),
    ({"operation": "retarget", "edgeId": "branch-input", "endpoint": "source", "nodeId": "ending"}, "out_degree"),
    ({"operation": "add", "nodeId": "parallel", "kind": "scene", "rowHint": 2, "createPendingChoices": False, "sourceNodeId": "branch-123", "targetNodeId": None,
        "incomingEdgeId": "parallel-input", "outgoingEdgeId": "parallel-output"}, "隐式分叉"),
])
def test_failed_safety_preview_mutates_nothing(source_project, command, reason):
    receipt = save_graph_mapping(source_project, authored_map(source_project))
    with pytest.raises(InvalidTransitionError, match=reason):
        source_project.preview_graph_command(request(receipt, command))
    assert source_project.graph_workbench_state().draft == receipt


def test_safe_bypass_preserves_exact_input_and_undo_snapshot(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    saved, _ = apply(store, receipt, {"operation": "delete", "nodeId": "inserted-step", "method": "safe_bypass"})
    input_edge = next(edge for edge in saved.payload["mapping"]["topology"]["edges"] if edge["id"] == "branch-input")
    assert input_edge["targetNodeId"] == "merge" and input_edge["stateEffects"] == {"retainedFact": "original traversal"}
    undo = store.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=0,
        expected_draft_revision=saved.draft_revision, payload=receipt.payload)
    assert undo.payload == receipt.payload
    assert store.authoring.get_stage_head(store.manifest.project_id, StageName.STORY_GRAPH).revision == 0


def test_capacity_refusal_and_pending_decision_insertion(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    _, preview = apply(store, receipt, insert_command(kind="decision"))
    choice = next(choice for choice in preview.result.mapping.choices if choice.section_id == "new-step")
    assert len(choice.outcomes) == 2 and all(option.ending_section_id is None for option in choice.outcomes)
    with pytest.raises(ValueError):
        preview.result.admitted_mapping()
    current = GraphAuthoringDraft.model_validate(receipt.payload)
    command = request(receipt, insert_command()).command
    with pytest.raises(InvalidTransitionError, match="node_capacity"):
        execute_graph_command(current, command, store.project().brief.model_copy(update={"node_budget": 8}))


def test_choice_initialization_is_explicit_and_capacity_preserves_retained_options(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    deleted, _ = apply(store, receipt, {"operation": "delete", "nodeId": "choose", "method": "only_delete"})
    command = {"operation": "add", "nodeId": "fresh-choice", "kind": "decision", "rowHint": 1, "createPendingChoices": True,
        "sourceNodeId": None, "targetNodeId": None, "incomingEdgeId": "unused-input", "outgoingEdgeId": "fresh-options"}
    saved, preview = apply(store, deleted, command)
    fresh = next(choice for choice in preview.result.mapping.choices if choice.section_id == "fresh-choice")
    assert len(fresh.outcomes) == 2 and all(option.ending_section_id is None for option in fresh.outcomes)
    saved, _ = apply(store, saved, {"operation": "retarget", "edgeId": "option-123", "endpoint": "source", "nodeId": "fresh-choice"})
    with pytest.raises(InvalidTransitionError, match="out_degree"):
        store.preview_graph_command(request(saved, {"operation": "retarget", "edgeId": "option-222", "endpoint": "source", "nodeId": "fresh-choice"}))
    assert store.graph_workbench_state().draft == saved
    for option in fresh.outcomes:
        saved, _ = apply(store, saved, {"operation": "remove_edge", "edgeId": option.outcome_id})
    for number in (222, 333):
        saved, _ = apply(store, saved, {"operation": "retarget", "edgeId": f"option-{number}", "endpoint": "source", "nodeId": "fresh-choice"})
    assert [(option["label"], option["consequence"]) for option in saved.payload["mapping"]["choices"][0]["outcomes"]] == [(str(number), f"Action {number}.") for number in (123, 222, 333)]


def test_reuse_retains_content_identity_and_existing_outputs(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    detached, _ = apply(store, receipt, {"operation": "retarget", "edgeId": "option-123", "endpoint": "target", "nodeId": None})
    command = {"operation": "reuse", "nodeId": "branch-123", "rowHint": 7, "sourceNodeId": None,
        "targetNodeId": None, "incomingEdgeId": "reuse-input", "outgoingEdgeId": "reuse-output"}
    saved, _ = apply(store, detached, command)
    assert saved.payload["mapping"] == detached.payload["mapping"]
    assert saved.payload["rowHints"]["branch-123"] == 7
    with pytest.raises(InvalidTransitionError, match="已有后续"):
        store.preview_graph_command(request(saved, command | {"targetNodeId": "merge"}))
    assert store.graph_workbench_state().draft == saved


def test_input_replacement_detaches_prior_and_preserves_displaced_target(source_project):
    store = source_project
    receipt = save_graph_mapping(store, authored_map(store))
    saved, preview = apply(store, receipt, {"operation": "replace_input", "nodeId": "inserted-step",
        "priorEdgeId": "branch-input", "chosenEdgeId": "option-222"})
    edges = {edge["id"]: edge for edge in saved.payload["mapping"]["topology"]["edges"]}
    assert edges["branch-input"]["targetNodeId"] is None
    assert edges["branch-input"]["stateEffects"] == {"retainedFact": "original traversal"}
    assert edges["option-222"]["targetNodeId"] == "inserted-step"
    assert "branch-222" in preview.impact.retained_node_ids
    assert preview.impact.changed_edge_ids == ["branch-input", "option-222"]
    with pytest.raises(InvalidTransitionError, match="原样"):
        store.preview_graph_command(request(saved, {"operation": "replace_input", "nodeId": "inserted-step",
            "priorEdgeId": "option-222", "chosenEdgeId": "option-222"}))
    assert store.graph_workbench_state().draft == saved
