"""Import direction and concrete fact authority at the compiler-free boundary."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.correction_directives import (
    CorrectionDirectivePlanError,
    compile_correction_instruction_plan,
)
from plotloom.generation.dialogue_repair_contracts import (
    CueOrderRepairAssignment,
    CueOrderRepairFact,
)
from plotloom.generation.graph_repair_contracts import JoinStateEffectRepairFact
from plotloom.generation.repair_facts import (
    parse_semantic_repair_fact,
    serialize_semantic_repair_fact,
)


@pytest.mark.parametrize("reverse", [False, True])
def test_contract_consumers_import_cold_without_the_compiler(reverse: bool) -> None:
    owners = [
        "scene_response_contracts",
        "storyboard_response_contracts",
        "dialogue_repair_contracts",
        "graph_repair_contracts",
        "continuity_repair_contracts",
        "storyboard_repair_contracts",
        "repair_facts",
        "work_unit_contracts",
        "correction_directives",
        "correction_schema",
        "correction_postconditions",
    ]
    if reverse:
        owners.reverse()
    code = f"""
import importlib, sys
for name in {owners!r}:
    importlib.import_module('plotloom.generation.' + name)
assert 'plotloom.generation.work_units' not in sys.modules
importlib.import_module('plotloom.generation.work_units')
"""
    subprocess.run([sys.executable, "-c", code], check=True)


@pytest.mark.parametrize("forged", ["same_name", "subclass"])
def test_directives_refuse_forged_same_name_and_subclass_facts(forged: str) -> None:
    fact = CueOrderRepairFact(
        code="semantic.cue_order",
        path=("dialogueCues",),
        assignments=(
            CueOrderRepairAssignment(
                local_cue_id="cue", beat_local_id="beat", expected_order=1
            ),
        ),
    )
    if forged == "subclass":
        untrusted = type("UnexpectedCueFact", (CueOrderRepairFact,), {})(
            **fact.model_dump()
        )
    else:
        untrusted = type(
            "CueOrderRepairFact",
            (),
            {
                "model_dump": lambda *_args, **_kwargs: fact.model_dump(
                    mode="json", by_alias=True
                )
            },
        )()
    issue = ValidationIssue(code=fact.code, path=fact.path, message="rejected order")
    with pytest.raises(CorrectionDirectivePlanError, match="typed current fact"):
        compile_correction_instruction_plan([issue], [untrusted])
    accepted = compile_correction_instruction_plan([issue], [fact])
    assert (
        accepted.audit_issue_selection["factBindings"][0]["model"]
        == "CueOrderRepairFact"
    )


def test_leaf_codec_preserves_authorized_nested_nulls_in_json_and_directives() -> None:
    payload = {
        "code": "semantic.join_state_effect_missing",
        "path": ["edges", "left", "stateEffects", "route"],
        "joinContractId": "join",
        "joinNodeId": "node",
        "stateKey": "route",
        "mode": "convergent",
        "incomingEdges": [
            {"edgeId": "left", "sourceNodeId": "a"},
            {"edgeId": "right", "sourceNodeId": "b"},
        ],
        "repairAction": "set_missing",
        "hasExpectedValue": True,
        "expectedValue": None,
        "preservedStateEffects": [
            {
                "stateKey": "sibling",
                "incomingEffects": [
                    {"edgeId": "left", "expectedValue": None},
                    {"edgeId": "right", "expectedValue": {"nested": None}},
                ],
            }
        ],
    }
    fact = parse_semantic_repair_fact(payload)
    assert type(fact) is JoinStateEffectRepairFact
    encoded = serialize_semantic_repair_fact(fact)
    assert encoded == payload
    assert (
        serialize_semantic_repair_fact(
            parse_semantic_repair_fact(json.loads(json.dumps(encoded)))
        )
        == payload
    )
    plan = compile_correction_instruction_plan(
        [ValidationIssue(code=fact.code, path=fact.path, message="missing")], [fact]
    )
    group = plan.prompt_evidence["facts"][0]
    assert group["expectedValue"] is None
    assert group["preservedStateEffects"] == payload["preservedStateEffects"]
