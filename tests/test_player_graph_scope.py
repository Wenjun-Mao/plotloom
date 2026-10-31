"""Do not silently invent runtime state semantics or drop source content."""
from copy import deepcopy

import pytest

from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.player_export import _assert_graph


def graph():
    return {"startNodeId": "a", "joinContracts": [], "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"id": "go", "sourceNodeId": "a", "targetNodeId": "b", "kind": "continuation",
            "choiceText": None, "stateEffects": {}, "entityStateEffects": []}]}


@pytest.mark.parametrize("change", ["state", "entity_state", "join", "cycle", "dangling", "unreachable", "ambiguous"])
def test_structural_player_refuses_unimplemented_or_incomplete_graph_semantics(change):
    value = graph()
    if change == "state": value["edges"][0]["stateEffects"] = {"secretFlag": True}
    elif change == "entity_state": value["edges"][0]["entityStateEffects"] = [{"entityId": "x"}]
    elif change == "join": value["joinContracts"] = [{"id": "join"}]
    elif change == "cycle": value["edges"].append(dict(value["edges"][0], id="back", sourceNodeId="b", targetNodeId="a"))
    elif change == "dangling": value["edges"][0]["targetNodeId"] = "missing"
    elif change == "unreachable": value["nodes"].append({"id": "lost"})
    else: value["edges"].append(dict(value["edges"][0], id="go2"))
    with pytest.raises(InvalidTransitionError): _assert_graph(value, {"choices": []})


def test_current_choice_provenance_is_exact_metadata_without_invented_state_execution():
    value = graph()
    value["nodes"].append({"id": "c"})
    first = value["edges"][0]
    first.update(kind="choice", choiceText="B", stateEffects={"sourceMapChoiceId": "a", "sourceMapOutcomeId": "go", "sourceMapConsequence": "B result"})
    value["edges"].append(dict(first, id="go2", targetNodeId="c", choiceText="C", stateEffects={}))
    choices = {"choices": [{"sectionId": "a", "outcomes": [
        {"outcomeId": "go", "endingSectionId": "b", "label": "B", "consequence": "B result"},
        {"outcomeId": "go2", "endingSectionId": "c", "label": "C", "consequence": "C result"}]}]}
    _assert_graph(value, choices)
    for mutation in ("provenance", "label", "coverage"):
        altered = deepcopy(value)
        if mutation == "provenance": altered["edges"][0]["stateEffects"]["sourceMapConsequence"] = "wrong source"
        elif mutation == "label": altered["edges"][0]["choiceText"] = "Silent rewrite"
        else: altered["edges"].pop()
        with pytest.raises(InvalidTransitionError): _assert_graph(altered, choices)
