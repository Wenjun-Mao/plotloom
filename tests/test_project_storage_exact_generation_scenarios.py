"""Exact generation regressions exercised through the project-folder owner."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from plotloom.artifacts import LocalArtifactStore
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import Artifact, ArtifactKind, RunKind, RunStatus, StageName
from plotloom.generation.contracts import ProviderResponse
from plotloom.jobs import LifecycleJobRunner
from plotloom.persistence import stable_hash
from plotloom.pipeline import PipelineEngine, RunSecretBroker
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext
from tests.project_storage_fixtures import FixtureProvider, fixture_profile


class _FixtureResolver:
    def __init__(self, provider: "_MutatingFixtureProvider") -> None:
        self.provider = provider

    def resolve(self, provider_snapshot: dict[str, object]):
        return self.provider, str(provider_snapshot["textModel"])


class _MutatingFixtureProvider:
    """Mutate one production-shaped fixture response before durable validation."""

    name = FixtureProvider.name
    capabilities = FixtureProvider.capabilities

    def __init__(self, mutate_response) -> None:
        self._delegate = FixtureProvider()
        self._mutate_response = mutate_response
        self.requests: list[Any] = []

    def generate(self, request: Any, secret: object | None) -> ProviderResponse:
        self.requests.append(request)
        response = self._delegate.generate(request, None)
        return self._mutate_response(request, response)


def _store(tmp_path: Path) -> ProjectStore:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    return storage.projects.create(FIXED_CHINESE_BRIEF)


def _execute_stages(
    store: ProjectStore,
    stages: list[StageName],
    provider: _MutatingFixtureProvider,
    broker: RunSecretBroker,
):
    snapshot = fixture_profile().model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        run = store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            stages,
            provider_snapshot=snapshot,
        )
    runner = LifecycleJobRunner(
        store.generation,
        PipelineEngine(store.generation, _FixtureResolver(provider), broker),
        RunContext(providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")),
        max_workers=1,
        secret_registrar=broker,
    )
    try:
        return run, runner.submit(run.id).result()
    finally:
        runner.close()


def _response_payload(response: ProviderResponse) -> dict[str, object]:
    content = response.raw["choices"][0]["message"]["content"]
    assert isinstance(content, str)
    return json.loads(content)


def _with_payload(response: ProviderResponse, payload: dict[str, object]) -> ProviderResponse:
    return response.model_copy(
        update={
            "raw": {
                "choices": [
                    {"message": {"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)}}
                ]
            }
        }
    )


def test_project_storyboard_audio_timing_uses_exact_frozen_repair_fact(tmp_path: Path) -> None:
    """An overflowing audio event is corrected from facts, not diagnostic prose."""

    mutated = False
    corrected_payload: dict[str, object] | None = None

    def overflow_first_storyboard(request: Any, response: ProviderResponse) -> ProviderResponse:
        nonlocal mutated, corrected_payload
        prompt = "\n".join(message.content for message in request.messages)
        if corrected_payload is not None and "semantic.audio_timing" in prompt:
            return _with_payload(response, corrected_payload)
        if mutated or "【目标戏剧场景】" not in prompt:
            return response
        mutated = True
        payload = _response_payload(response)
        shots = payload["shots"]
        assert isinstance(shots, list) and isinstance(shots[0], dict)
        shot = shots[0]
        duration = shot["durationUnits"]
        assert isinstance(duration, int)
        shot["audioPlan"] = {
            "events": [
                {
                    "kind": "ambience",
                    "description": "低频机器声",
                    "startOffsetUnits": 0,
                    "durationUnits": duration + 1,
                }
            ]
        }
        corrected_payload = deepcopy(payload)
        corrected_shots = corrected_payload["shots"]
        assert isinstance(corrected_shots, list) and isinstance(corrected_shots[0], dict)
        corrected_shots[0]["audioPlan"]["events"][0]["durationUnits"] = duration
        return _with_payload(response, payload)

    store = _store(tmp_path)
    provider = _MutatingFixtureProvider(overflow_first_storyboard)
    profile_values = fixture_profile().model_dump(mode="json", by_alias=True)
    profile_values.update(textAuthMode="bearer", profileHash="")
    profile = type(fixture_profile()).model_validate(profile_values)
    secret = "audio-timing-repair-secret"
    broker = RunSecretBroker(server_profile_keys={profile.profile_id: secret})
    try:
        completed = ProjectPipelineExecutor(_FixtureResolver(provider)).execute(
            store, profile=profile, secret_broker=broker
        )
    finally:
        broker.close()

    assert completed.status == RunStatus.SUCCEEDED
    trace = store.run_trace(completed.id)
    rejected = next(item for item in trace.attempts if item.outcome_code == "semantic.audio_timing")
    correction = next(item for item in trace.attempts if item.source_attempt_id == rejected.id)
    assert correction.status.value == "succeeded"
    validation = next(
        artifact
        for artifact in trace.artifacts
        if artifact.attempt_id == rejected.id and artifact.kind == ArtifactKind.VALIDATION
    )
    # The response artifact is the frozen source; never recalculate repair guidance from the prompt.
    source_response = next(
        artifact
        for artifact in trace.artifacts
        if artifact.attempt_id == rejected.id and artifact.kind == ArtifactKind.RESPONSE
    )
    source_content = source_response.content["rawResponse"]["choices"][0]["message"]["content"]
    assert isinstance(source_content, str)
    rejected_payload = json.loads(source_content)
    shot = rejected_payload["shots"][0]
    assert validation.content["repairFacts"] == [
        {
            "code": "semantic.audio_timing",
            "path": ["shots", 0, "audioPlan", "events", 0, "durationUnits"],
            "shotLocalId": shot["localShotId"],
            "eventIndex": 0,
            "startOffsetUnits": 0,
            "durationUnits": shot["durationUnits"] + 1,
            "shotDurationUnits": shot["durationUnits"],
            "repairAction": "replace_duration",
            "replacementDurationUnits": shot["durationUnits"],
        }
    ]
    correction_prompt = next(
        request.messages[1].content
        for request in provider.requests
        if "semantic.audio_timing" in request.messages[1].content
    )
    assert "验证器说明" in correction_prompt
    assert "audio event must fit within the shot duration" not in correction_prompt
    assert secret not in correction_prompt
    assert next(item for item in store.canonical_stages() if item.head.stage == StageName.STORYBOARD).head.revision == 1


def test_project_cue_order_fact_rejects_rebound_membership_before_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mutated = False

    def reject_first_scene(request: Any, response: ProviderResponse) -> ProviderResponse:
        nonlocal mutated
        prompt = "\n".join(message.content for message in request.messages)
        if mutated or "【目标故事节点】" not in prompt:
            return response
        mutated = True
        payload = _response_payload(response)
        beats = payload["beats"]
        assert isinstance(beats, list) and isinstance(beats[0], dict)
        first_beat = beats[0]
        second_beat = deepcopy(first_beat)
        second_beat.update(
            {
                "localBeatId": "beat-cue-order-b",
                "order": 2,
                "description": "远处的警报打断了回答。",
                "purpose": "推动第二个可观察动作。",
            }
        )
        beats.append(second_beat)
        payload["dialogueCues"] = [
            {
                "localCueId": "cue-a",
                "beatLocalId": first_beat["localBeatId"],
                "order": 1,
                "speakerId": None,
                "voiceOver": "narrator",
                "text": "第一句",
                "language": "zh-CN",
                "delivery": "natural",
                "performanceNotes": "平静",
            },
            {
                "localCueId": "cue-b",
                "beatLocalId": second_beat["localBeatId"],
                "order": 2,
                "speakerId": None,
                "voiceOver": "narrator",
                "text": "第二句",
                "language": "zh-CN",
                "delivery": "natural",
                "performanceNotes": "警觉",
            },
        ]
        return _with_payload(response, payload)

    store = _store(tmp_path)
    provider = _MutatingFixtureProvider(reject_first_scene)
    original_add_artifact = store.generation.add_artifact
    tampered_artifact_ids: list[str] = []

    def add_rebound_cue_order_validation(artifact: Artifact) -> Artifact:
        if artifact.kind == ArtifactKind.VALIDATION and isinstance(artifact.content, dict):
            content = deepcopy(artifact.content)
            matching = [
                item
                for item in content.get("repairFacts", [])
                if isinstance(item, dict) and item.get("code") == "semantic.cue_order"
            ]
            if matching:
                first, second = matching[0]["assignments"]
                first["beatLocalId"], second["beatLocalId"] = second["beatLocalId"], first["beatLocalId"]
                artifact = artifact.model_copy(
                    update={"content": content, "content_hash": stable_hash(content)}
                )
                tampered_artifact_ids.append(artifact.id)
        return original_add_artifact(artifact)

    monkeypatch.setattr(store.generation, "add_artifact", add_rebound_cue_order_validation)
    broker = RunSecretBroker()
    try:
        run, completed = _execute_stages(
            store,
            [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
            provider,
            broker,
        )
    finally:
        broker.close()

    assert tampered_artifact_ids
    assert completed.status == RunStatus.FAILED
    trace = store.run_trace(run.id)
    rejected = next(item for item in trace.attempts if item.outcome_code == "semantic.cue_order")
    correction = next(item for item in trace.attempts if item.source_attempt_id == rejected.id)
    assert correction.outcome_code == "contract.correction_source_changed"
    assert len(provider.requests) == 3
    assert all(item.head.stage != StageName.SCENE_BEATS for item in store.canonical_stages())
