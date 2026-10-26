"""Persisted null and sibling authority through the actual correction runner."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

import plotloom.generation.fragment_validation as fragment_validation
import plotloom.persistence.project.generation_snapshots as generation_snapshots
import plotloom.correction_source as correction_source
from plotloom.artifact_contracts import Artifact, ArtifactKind
from plotloom.run_contracts import RunStatus
from plotloom.stage_contracts import StageName
from plotloom.generation.repair_facts import (
    parse_semantic_repair_fact,
    serialize_semantic_repair_fact,
)
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology
from plotloom.persistence import stable_hash
from plotloom.runtime_secrets import RunSecretBroker
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from tests.project_storage_fixtures import FixtureResolver, _json_after, fixture_profile
from tests.project_storage_generation_support import (
    _execute_stages,
    _MutatingFixtureProvider,
    _response_payload,
    _store,
    _with_payload,
)


@pytest.mark.parametrize("family", ["join", "continuity"])
@pytest.mark.parametrize("tamper", [False, True])
def test_persisted_repair_null_and_sibling_authority_is_revalidated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, family: str, tamper: bool
) -> None:
    # Explicit current footage-bearing topology fixture, frozen before admission.
    # The default creation policy uses route-only joins with no scene-state facts.
    if family == "join":
        original_planner = generation_snapshots.plan_story_graph_topology

        def footage_join_fixture(**kwargs):
            topology = original_planner(**kwargs)
            payload = topology.model_dump(mode="json", by_alias=True)
            for node in payload["nodes"]:
                if node["kind"] == "join":
                    node["footageMode"] = "footage"
            del payload["topologyHash"]
            payload["topologyHash"] = stable_hash(payload)
            return StoryGraphTopology.model_validate(payload)

        monkeypatch.setattr(
            generation_snapshots, "plan_story_graph_topology", footage_join_fixture
        )
    store = _store(tmp_path)
    corrected = None
    code = (
        "semantic.join_state_effect_missing"
        if family == "join"
        else "semantic.continuity_beat_sequence_mismatch"
    )
    source_assertion = (
        "assert_join_state_effect_repair_fact_matches_source"
        if family == "join"
        else "assert_continuity_repair_fact_matches_source"
    )
    original_assertion = getattr(correction_source, source_assertion)
    observed = []

    def observe_parsed_fact(fact, value, **kwargs):
        observed.append(serialize_semantic_repair_fact(fact))
        return original_assertion(fact, value, **kwargs)

    monkeypatch.setattr(correction_source, source_assertion, observe_parsed_fact)

    def reject_once(request, response):
        nonlocal corrected
        prompt = "\n".join(message.content for message in request.messages)
        if corrected is not None:
            return _with_payload(response, corrected) if code in prompt else response
        marker = "【不可变图骨架清单】" if family == "join" else "【目标故事节点】"
        if marker not in prompt:
            return response
        payload = _response_payload(response)
        if family == "join":
            topology = _json_after(prompt, marker)
            join = topology["joinContracts"][0]
            incoming = sorted(
                edge["id"]
                for edge in topology["edges"]
                if edge["targetNodeId"] == join["joinNodeId"]
                and edge["sourceNodeId"] in join["incomingNodeIds"]
            )
            payload["joinContracts"][0].update(
                requiredStateKeys=["route", "sibling"], allowedDifferences=["sibling"]
            )
            edges = {edge["id"]: edge for edge in payload["edges"]}
            for position, edge_id in enumerate(incoming):
                edges[edge_id]["stateEffects"] = {
                    "route": None,
                    "sibling": None if position == 0 else {"branch": position},
                }
            corrected = deepcopy(payload)
            del edges[incoming[0]]["stateEffects"]["route"]
        else:
            payload["scenes"][0]["entryState"]["facts"] = {"nullable": None}
            payload["beats"][0]["entryState"]["facts"] = {"nullable": "wrong"}
            corrected = deepcopy(payload)
            corrected["beats"][0]["entryState"]["facts"]["nullable"] = None
        return _with_payload(response, payload)

    provider = _MutatingFixtureProvider(reject_once)
    original_add = store.generation.add_artifact

    def tamper_persisted_authority(artifact: Artifact) -> Artifact:
        if tamper and artifact.kind == ArtifactKind.VALIDATION:
            content = deepcopy(artifact.content)
            matching = [
                fact for fact in content.get("repairFacts", []) if fact["code"] == code
            ]
            if matching:
                if family == "join":
                    matching[0]["preservedStateEffects"][0]["incomingEffects"][0][
                        "expectedValue"
                    ] = "foreign"
                else:
                    matching[0]["boundaries"][0]["assignments"][0]["expectedValue"] = (
                        "foreign"
                    )
                artifact = artifact.model_copy(
                    update={"content": content, "content_hash": stable_hash(content)}
                )
        return original_add(artifact)

    monkeypatch.setattr(store.generation, "add_artifact", tamper_persisted_authority)
    broker = RunSecretBroker()
    stages = [StageName.STORY_BIBLE, StageName.STORY_GRAPH]
    if family == "continuity":
        stages.append(StageName.SCENE_BEATS)
    try:
        run, completed = _execute_stages(store, stages, provider, broker)
    finally:
        broker.close()
    trace = store.run_trace(run.id)
    outcomes = [(item.stage, item.outcome_code, item.error) for item in trace.attempts]
    assert completed.status == (RunStatus.FAILED if tamper else RunStatus.SUCCEEDED), (
        outcomes
    )
    assert any(item.outcome_code == code for item in trace.attempts), outcomes
    rejected = next(item for item in trace.attempts if item.outcome_code == code)
    artifact = next(
        item
        for item in trace.artifacts
        if item.attempt_id == rejected.id and item.kind == ArtifactKind.VALIDATION
    )
    assert stable_hash(artifact.content) == artifact.content_hash
    persisted = json.loads(artifact.model_dump_json())["content"]["repairFacts"]
    assert observed == persisted
    assert [
        serialize_semantic_repair_fact(parse_semantic_repair_fact(item))
        for item in persisted
    ] == persisted
    if family == "join":
        assert persisted[0]["hasExpectedValue"] is True
        assert persisted[0]["expectedValue"] is None
        assert persisted[0]["preservedStateEffects"][0]["incomingEffects"][0][
            "expectedValue"
        ] == ("foreign" if tamper else None)
    else:
        assert persisted[0]["boundaries"][0]["assignments"][0]["key"] == "nullable"
        assert persisted[0]["boundaries"][0]["assignments"][0]["expectedValue"] == (
            "foreign" if tamper else None
        )
    correction = next(
        item for item in trace.attempts if item.source_attempt_id == rejected.id
    )
    if tamper:
        assert correction.outcome_code == "contract.correction_source_changed"
        assert not any(
            code in request.messages[1].content for request in provider.requests
        )
    else:
        assert correction.status.value == "succeeded"
    before = trace.model_dump(mode="json")
    project_id = store.project().id
    store.close()
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    reopened = storage.projects.open(project_id)
    try:
        assert reopened.run_trace(run.id).model_dump(mode="json") == before
    finally:
        reopened.close()


def test_trusted_binder_fault_fails_durably_without_model_correction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    resolver = FixtureResolver()

    def broken_binder(*args, **kwargs):
        raise RuntimeError("trusted binder fixture fault")

    monkeypatch.setattr(fragment_validation, "_bind_fragment", broken_binder)
    completed = ProjectPipelineExecutor(resolver).execute(
        store, profile=fixture_profile()
    )
    assert completed.status == RunStatus.FAILED
    trace = store.run_trace(completed.id)
    failures = [
        attempt
        for attempt in trace.attempts
        if attempt.outcome_code == "validation.internal_error"
    ]
    assert len(failures) == 1
    failed = failures[0]
    assert not any(attempt.source_attempt_id == failed.id for attempt in trace.attempts)
    validation = next(
        artifact
        for artifact in trace.artifacts
        if artifact.attempt_id == failed.id and artifact.kind == ArtifactKind.VALIDATION
    )
    assert validation.content["issues"] == validation.content["repairFacts"] == []
    assert store.canonical_stages() == []
    store.close()
