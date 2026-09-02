from __future__ import annotations

import json

import pytest

from plotloom.domain import ProjectBrief, StageName, StoryBible, StoryGraph
from plotloom.generation.contracts import AttemptKind, AttemptStatus, RunStatus
from plotloom.generation.exceptions import GenerationRunFailed
from plotloom.generation.orchestration import GenerationOrchestrator
from plotloom.generation.prompts import PromptRenderer
from plotloom.generation.validation import CanonicalStageValidationAdapter

from conftest import QueueProvider, secret_lease


def _brief() -> ProjectBrief:
    return ProjectBrief(
        title="星海回声",
        synopsis="一名失忆领航员寻找身份。",
        ending_count=1,
        decision_points_per_path=0,
        desired_join_count=0,
        node_budget=4,
    )


def _story_bible_response() -> str:
    return json.dumps(
        StoryBible(
            logline="领航员寻找身份",
            premise="她必须决定是否唤醒人工智能",
        ).model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
    )


@pytest.mark.parametrize("supports_schema", [True, False])
def test_capability_paths_share_prompt_schema_and_local_validation(
    supports_schema: bool,
) -> None:
    provider = QueueProvider([_story_bible_response()], json_schema=supports_schema)
    orchestrator = GenerationOrchestrator(renderer=PromptRenderer(), provider=provider)
    _, lease = secret_lease()
    validator = CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=_brief())

    result = orchestrator.generate(
        prompt_id="story_bible",
        variables={"project_input": _brief()},
        validator=validator,
        model="test-model",
        secret=lease,
    )

    assert result.run.status == RunStatus.SUCCEEDED
    assert isinstance(result.value, StoryBible)
    request = provider.requests[0]
    assert (request.response_schema is not None) is supports_schema
    assert result.run.attempts[0].native_json_schema_used is supports_schema
    assert result.run.attempts[0].structured_output_mode == "prefer"
    assert result.run.attempts[0].raw_response == _story_bible_response()
    assert result.run.attempts[0].validation_accepted is True
    assert result.run.attempts[0].rendered_messages == request.messages
    assert '"logline"' in request.messages[1].content
    assert '"worldRules"' in request.messages[1].content
    assert "test-provider-secret" not in result.run.model_dump_json()


def test_semantically_invalid_output_is_quarantined_without_automatic_repair() -> None:
    invalid = json.dumps(
        {
            "startNodeId": "missing",
            "nodes": [
                {"id": "end", "title": "结局", "summary": "结束", "kind": "ending"}
            ],
            "edges": [],
            "joinContracts": [],
        },
        ensure_ascii=False,
    )
    valid_repair = json.dumps(
        {
            "startNodeId": "start",
            "nodes": [
                {"id": "start", "title": "开始", "summary": "苏醒", "kind": "start"},
                {"id": "end", "title": "结局", "summary": "离开", "kind": "ending"},
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "sourceNodeId": "start",
                    "targetNodeId": "end",
                    "kind": "continuation",
                    "choiceText": None,
                    "stateEffects": {},
                }
            ],
            "joinContracts": [],
        },
        ensure_ascii=False,
    )
    provider = QueueProvider([invalid, valid_repair], json_schema=False)
    orchestrator = GenerationOrchestrator(renderer=PromptRenderer(), provider=provider)
    _, lease = secret_lease(max_uses=2)
    validator = CanonicalStageValidationAdapter(StageName.STORY_GRAPH, brief=_brief())

    with pytest.raises(GenerationRunFailed) as captured:
        orchestrator.generate(
            prompt_id="story_graph",
            variables={"story_bible": StoryBible(logline="失忆", premise="寻找身份"), "graph_constraints": _brief()},
            validator=validator,
            model="test-model",
            secret=lease,
        )
    parent = captured.value.run
    assert parent.status == RunStatus.QUARANTINED
    assert len(parent.attempts) == 1
    assert parent.attempts[0].kind == AttemptKind.PRIMARY
    assert parent.attempts[0].status == AttemptStatus.QUARANTINED
    assert parent.attempts[0].raw_response == invalid
    assert parent.attempts[0].validation_accepted is False
    assert len(provider.requests) == 1
    assert any(
        issue.code == "semantic.missing_start_node"
        for issue in parent.attempts[0].validation_issues
    )

    quarantine_id = parent.quarantine_ids[0]
    quarantine = orchestrator.quarantine.get(quarantine_id)
    assert quarantine is not None
    assert quarantine.schema_id == "story_graph.v2"
    repaired = orchestrator.repair(
        quarantine_id=quarantine_id,
        parent_run_id=parent.run_id,
        validator=validator,
        model="test-model",
        secret=lease,
    )
    assert repaired.run.kind == "repair"
    assert repaired.run.parent_run_id == parent.run_id
    assert repaired.run.source_quarantine_id == quarantine_id
    assert len(repaired.run.attempts) == 1
    assert repaired.run.attempts[0].kind == AttemptKind.REPAIR
    assert isinstance(repaired.value, StoryGraph)
    assert len(provider.requests) == 2
    assert provider.requests[1].response_schema is None
    assert "semantic.missing_start_node" in provider.requests[1].messages[1].content


def test_explicit_repair_rejects_mismatched_parent_run() -> None:
    provider = QueueProvider(["not json"], json_schema=False)
    orchestrator = GenerationOrchestrator(renderer=PromptRenderer(), provider=provider)
    _, lease = secret_lease()
    validator = CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=_brief())
    with pytest.raises(GenerationRunFailed) as captured:
        orchestrator.generate(
            prompt_id="story_bible",
            variables={"project_input": _brief()},
            validator=validator,
            model="test-model",
            secret=lease,
        )
    quarantine_id = captured.value.run.quarantine_ids[0]
    with pytest.raises(ValueError, match="does not belong"):
        orchestrator.repair(
            quarantine_id=quarantine_id,
            parent_run_id="another-run",
            validator=validator,
            model="test-model",
            secret=lease,
        )
    assert len(provider.requests) == 1
