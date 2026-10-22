"""Pure and persisted command proof; provider/job/media owners are never touched."""
import pytest

from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.graph_authoring_drafts import GraphAuthoringDraft
from plotloom.graph_command_execution import execute_graph_command
from plotloom.graph_commands import GraphCommandApplyRequest, GraphCommandRequest
from plotloom.persistence.project.graph_workbench import GraphDraftRebaseRequest
from tests.graph_authoring_fixtures import authored_map, copy_accepted_source_project
from tests.graph_draft_fixtures import save_graph_mapping


@pytest.fixture
def source_project(tmp_path, accepted_source_project_seed):
    store = copy_accepted_source_project(accepted_source_project_seed, tmp_path)
    try:
        yield store
    finally:
        store.close()


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


def test_remove_join_preview_discloses_contract_content_removal_and_retained_graph(source_project):
    receipt = save_graph_mapping(source_project, authored_map(source_project))
    before = GraphAuthoringDraft.model_validate(receipt.payload)
    # Keep this a safety-valid one-input join; removing a multi-input contract
    # must continue to fail when it would create an unreviewed merge.
    before.mapping.topology.edges = [edge for edge in before.mapping.topology.edges
        if edge.id in {"opening-choice", "option-123", "option-222", "option-333", "branch-input", "new-continuation", "merge-ending"}]
    before.mapping.topology.joins[0].incoming_node_ids = ["inserted-step"]
    before.mapping.topology.joins[0].required_state_keys = ["arrival"]
    before.mapping.topology.joins[0].allowed_differences = ["arrival"]
    before.mapping.join_reconciliations["join-contract"] = "Each route reconciles arrival before the ending."
    before.mapping.topology.joins[0].notes = "Keep the bridge intact."
    before.field_buffers = {
        "join:join-contract:reconciliation": "unfinished reconciliation",
        "join:join-contract:notes": "unfinished note",
        "edge:branch-input:stateEffects": "unrelated pending edge field",
    }
    remove = GraphCommandRequest.model_validate({"expectedDraftRevision": receipt.draft_revision,
        "command": {"operation": "remove_join", "joinId": "join-contract"}}).command

    result, impact = execute_graph_command(before, remove, source_project.project().brief)

    assert [node.id for node in result.mapping.topology.nodes] == [node.id for node in before.mapping.topology.nodes]
    assert result.mapping.topology.edges == before.mapping.topology.edges
    assert result.mapping.topology.joins == []
    assert "join-contract" not in result.mapping.join_reconciliations
    assert "join:join-contract:reconciliation" not in result.field_buffers
    assert "join:join-contract:notes" not in result.field_buffers
    assert result.field_buffers["edge:branch-input:stateEffects"] == "unrelated pending edge field"
    assert impact.affected_join_ids == ["join-contract"]
    message = " ".join(impact.messages)
    assert "移除汇合合同" in message
    assert "必需状态键、允许差异、协调说明、备注和未提交字段输入" in message
    assert "汇合节点与图连接保留" in message
    assert "保留原有事实" not in message


def test_add_join_preview_names_new_contract_without_claiming_existing_content_is_preserved(source_project):
    receipt = save_graph_mapping(source_project, authored_map(source_project))
    before = GraphAuthoringDraft.model_validate(receipt.payload)
    add = GraphCommandRequest.model_validate({"expectedDraftRevision": receipt.draft_revision,
        "command": {"operation": "add_join", "joinId": "new-contract", "nodeId": "ending"}}).command

    result, impact = execute_graph_command(before, add, source_project.project().brief)

    new_join = next(join for join in result.mapping.topology.joins if join.id == "new-contract")
    assert new_join.incoming_node_ids == ["merge"]
    assert result.mapping.join_reconciliations["new-contract"] == ""
    assert impact.affected_join_ids == ["new-contract"]
    message = " ".join(impact.messages)
    assert "新增汇合合同" in message
    assert "合同字段目前为空" in message
    assert "保留原有事实" not in message


def test_retained_join_input_membership_change_preserves_contract_fields_and_requests_review(source_project):
    receipt = save_graph_mapping(source_project, authored_map(source_project))
    before = GraphAuthoringDraft.model_validate(receipt.payload)
    before.mapping.topology.joins[0].required_state_keys = ["arrival"]
    before.mapping.topology.joins[0].allowed_differences = ["arrival"]
    before.mapping.join_reconciliations["join-contract"] = "Preserve each arrival state."
    before.mapping.topology.joins[0].notes = "Original contract note."
    retarget = GraphCommandRequest.model_validate({"expectedDraftRevision": receipt.draft_revision,
        "command": {"operation": "retarget", "edgeId": "branch-input", "endpoint": "target", "nodeId": "merge"}}).command

    result, impact = execute_graph_command(before, retarget, source_project.project().brief)

    changed_join = result.mapping.topology.joins[0]
    assert set(changed_join.incoming_node_ids) == {"inserted-step", "branch-123", "branch-222", "branch-333"}
    assert changed_join.required_state_keys == ["arrival"]
    assert changed_join.allowed_differences == ["arrival"]
    assert changed_join.notes == "Original contract note."
    assert result.mapping.join_reconciliations["join-contract"] == "Preserve each arrival state."
    assert impact.affected_join_ids == ["join-contract"]
    message = " ".join(impact.messages)
    assert "直接输入节点集合已变化" in message
    assert "原合同字段保留" in message
    assert "请重新审阅" in message


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


def test_graph_command_seed_copies_are_independent(tmp_path, accepted_source_project_seed):
    first = copy_accepted_source_project(accepted_source_project_seed, tmp_path / "first")
    second = copy_accepted_source_project(accepted_source_project_seed, tmp_path / "second")
    try:
        assert first.home != second.home
        assert first.manifest.project_id == second.manifest.project_id
        assert first.graph_workbench_state().draft is None
        assert second.graph_workbench_state().draft is None

        save_graph_mapping(first, authored_map(first))

        assert first.graph_workbench_state().draft is not None
        assert second.graph_workbench_state().draft is None
    finally:
        first.close()
        second.close()
