from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable
from threading import Event

import pytest

from plotloom.artifacts import MemoryArtifactStore
from plotloom.domain import (
    DEFAULT_TEXT_BASE_URL,
    DEFAULT_TEXT_MODEL,
    DEFAULT_TEXT_PROVIDER,
    STAGE_ORDER,
    Artifact,
    ArtifactKind,
    AttemptStatus,
    RunKind,
    RunStatus,
    StageName,
    WorkUnitStatus,
)
from plotloom.generation.contracts import (
    GenerationRequest,
    ProviderCapabilities,
    ProviderResponse,
    ProviderUsage,
)
from plotloom.generation.exceptions import ProviderError
from plotloom.generation.secrets import SecretLease
from plotloom.exceptions import InvalidTransitionError
from plotloom.jobs import LifecycleJobRunner
from plotloom.pipeline import (
    PipelineEngine,
    RunSecretBroker,
    SnapshotTextProviderResolver,
)
from plotloom.persistence import stable_hash
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext

from .conftest import all_stage_payloads


class QueueProvider:
    name = "queue-provider"
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(
        self,
        responses: list[str | Exception],
        *,
        after_response: Callable[[], None] | None = None,
    ) -> None:
        self.responses = deque(responses)
        self.requests: list[GenerationRequest] = []
        self.observed_secrets: list[str] = []
        self.after_response = after_response

    def generate(self, request: GenerationRequest, secret: SecretLease) -> ProviderResponse:
        self.requests.append(request)
        with secret.reveal() as value:
            self.observed_secrets.append(value)
        content = self.responses.popleft()
        if isinstance(content, Exception):
            raise content
        response = ProviderResponse(
            provider=self.name,
            model=request.model,
            request_id=f"provider-request-{len(self.requests)}",
            finish_reason="stop",
            usage=ProviderUsage(input_tokens=10, output_tokens=20),
            raw={
                "id": f"response-{len(self.requests)}",
                "model": request.model,
                "choices": [{"message": {"role": "assistant", "content": content}}],
            },
        )
        if self.after_response is not None:
            self.after_response()
        return response


class RecordingResolver:
    def __init__(self, provider: QueueProvider) -> None:
        self.provider = provider
        self.snapshots: list[dict[str, object]] = []

    def resolve(self, provider_snapshot):
        self.snapshots.append(dict(provider_snapshot))
        return self.provider, str(provider_snapshot["textModel"])


def _responses(*payloads) -> list[str]:
    return [
        json.dumps(payload.model_dump(mode="json", by_alias=True), ensure_ascii=False)
        for payload in payloads
    ]


def _work_unit_responses() -> list[str]:
    """Return only model-facing payloads for the durable stage-plan units."""

    bible, graph, scene_beats, storyboard = all_stage_payloads()
    responses = _responses(bible, graph)
    responses.extend(
        json.dumps(
            {
                "storyNodeId": node.id,
                "scenes": [
                    scene.model_dump(mode="json", by_alias=True)
                    for scene in scene_beats.scenes
                    if scene.story_node_id == node.id
                ],
                "beats": [
                    beat.model_dump(mode="json", by_alias=True)
                    for beat in scene_beats.beats
                    if any(
                        scene.id == beat.scene_id and scene.story_node_id == node.id
                        for scene in scene_beats.scenes
                    )
                ],
            },
            ensure_ascii=False,
        )
        for node in graph.nodes
    )
    responses.extend(
        json.dumps(
            {
                "sceneId": scene.id,
                "shots": [
                    shot.model_dump(mode="json", by_alias=True)
                    for shot in storyboard.shots
                    if shot.scene_id == scene.id
                ],
                "shotBeatLinks": [
                    link.model_dump(mode="json", by_alias=True)
                    for link in storyboard.shot_beat_links
                    if any(
                        shot.id == link.shot_id and shot.scene_id == scene.id
                        for shot in storyboard.shots
                    )
                ],
            },
            ensure_ascii=False,
        )
        for scene in scene_beats.scenes
    )
    return responses


def test_snapshot_provider_resolver_translates_canonical_capability_aliases() -> None:
    resolver = SnapshotTextProviderResolver()

    adapter, model = resolver.resolve(
        {
            "textProvider": "local-openai-compatible",
            "textBaseUrl": "http://127.0.0.1:8080/v1",
            "textModel": "local-model",
            "textAuthMode": "none",
            "textCapabilities": {
                "chatCompletions": True,
                "jsonObject": True,
                "jsonSchema": False,
            },
        }
    )

    assert model == "local-model"
    assert adapter.capabilities == ProviderCapabilities(
        chat_completions=True,
        json_object=True,
        json_schema=False,
    )


def test_run_resolves_provider_defaults_before_enqueue_and_never_reads_later_fallbacks(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    supplied_snapshot: dict[str, object] = {}
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot=supplied_snapshot,
    )
    supplied_snapshot.update(
        {
            "textProvider": "changed-after-enqueue",
            "textBaseUrl": "http://127.0.0.1:65535/v1",
            "textModel": "changed-after-enqueue",
        }
    )

    adapter, model = SnapshotTextProviderResolver().resolve(run.provider_snapshot)

    assert adapter.name == DEFAULT_TEXT_PROVIDER
    assert adapter.base_url == DEFAULT_TEXT_BASE_URL
    assert model == DEFAULT_TEXT_MODEL
    assert run.provider_snapshot["profileHash"] == repository.get_generation_plan(
        run.id
    ).provider_profile_hash


def _run(repository, engine: PipelineEngine, secrets: RunSecretBroker, run_id: str):
    runner = LifecycleJobRunner(
        repository,
        engine,
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
        secret_registrar=secrets,
    )
    try:
        return runner.submit(run_id).result(timeout=5)
    finally:
        runner.close()


def test_pipeline_generates_traces_then_commits_all_stages_atomically(
    repository,
    brief,
    monkeypatch,
) -> None:
    project = repository.create_project(brief)
    provider = QueueProvider(_work_unit_responses())
    resolver = RecordingResolver(provider)
    secrets = RunSecretBroker("server-only-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        STAGE_ORDER,
        provider_snapshot={
            "textProvider": "queue-provider",
            "textBaseUrl": "https://unused.example/v1",
            "textModel": "fixture-model",
        },
    )

    def reject_legacy_payload_commit(*_args, **_kwargs):
        raise AssertionError("sealed PipelineEngine results must not use caller-owned payload commits")

    monkeypatch.setattr(repository, "commit_run_outputs", reject_legacy_payload_commit)

    completed = _run(repository, PipelineEngine(repository, resolver, secrets), secrets, run.id)

    assert completed.status == RunStatus.SUCCEEDED
    assert resolver.snapshots == [run.provider_snapshot]
    expected_unit_count = len(provider.requests)
    assert expected_unit_count > 4
    assert provider.observed_secrets == ["server-only-secret"] * expected_unit_count
    trace = repository.get_run_trace(run.id)
    assert [attempt.status for attempt in trace.attempts] == [AttemptStatus.SUCCEEDED] * expected_unit_count
    assert [artifact.kind for artifact in trace.artifacts].count(ArtifactKind.CANDIDATE) == expected_unit_count
    assert [artifact.kind for artifact in trace.artifacts].count(ArtifactKind.CANONICAL) == 4
    first_response = next(
        artifact for artifact in trace.artifacts if artifact.kind == ArtifactKind.RESPONSE
    )
    assert first_response.content["providerRequestId"] == "provider-request-1"
    assert first_response.content["finishReason"] == "stop"
    assert first_response.content["usage"] == {"inputTokens": 10, "outputTokens": 20}
    assert all(repository.get_stage_head(project.id, stage).revision == 1 for stage in STAGE_ORDER)
    execution = repository.get_run_execution_trace(run.id)
    assert [plan.stage for plan in execution.stage_plans] == list(STAGE_ORDER)
    assert [aggregate.stage for aggregate in execution.sealed_aggregates] == list(STAGE_ORDER)
    assert all(request.metadata["run_id"] == run.id for request in provider.requests)
    assert all(request.metadata["attempt_id"] in {attempt.id for attempt in trace.attempts} for request in provider.requests)
    assert "snapshotHash" not in provider.requests[0].messages[1].content
    assert "stageHeads" not in provider.requests[0].messages[1].content


def test_dispatch_marker_is_committed_before_the_provider_call(repository, brief, monkeypatch) -> None:
    project = repository.create_project(brief)
    provider = QueueProvider(_responses(all_stage_payloads()[0]))
    secrets = RunSecretBroker("marker-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "fixture-model"},
    )
    events: list[str] = []
    original_marker = repository.mark_attempt_dispatched
    original_generate = provider.generate

    def record_marker(attempt_id: str):
        events.append("dispatch")
        return original_marker(attempt_id)

    def record_provider(request, secret):
        events.append("provider")
        durable_attempt = next(
            attempt
            for attempt in repository.get_run_trace(run.id).attempts
            if attempt.id == request.metadata["attempt_id"]
        )
        assert durable_attempt.dispatched_at is not None
        return original_generate(request, secret)

    monkeypatch.setattr(repository, "mark_attempt_dispatched", record_marker)
    monkeypatch.setattr(provider, "generate", record_provider)

    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        secrets,
        run.id,
    )

    assert completed.status == RunStatus.SUCCEEDED
    assert events == ["dispatch", "provider"]


def test_post_dispatch_provider_failure_is_outcome_unknown_and_is_not_replayed(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    provider = QueueProvider([ProviderError("deadline after submission")])
    secrets = RunSecretBroker("unknown-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "fixture-model"},
    )

    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        secrets,
        run.id,
    )

    assert completed.status == RunStatus.FAILED
    assert len(provider.requests) == 1
    trace = repository.get_run_trace(run.id)
    assert trace.attempts[0].outcome_unknown is True
    assert repository.get_run_execution_trace(run.id).work_units[0].status == WorkUnitStatus.OUTCOME_UNKNOWN
    assert "server-only-secret" not in trace.model_dump_json()


def test_startup_recovery_recommits_complete_seals_without_a_provider_replay(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    provider = QueueProvider(_responses(all_stage_payloads()[0]))
    secrets = RunSecretBroker("recovery-secret")
    engine = PipelineEngine(repository, RecordingResolver(provider), secrets)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "fixture-model"},
    )

    # Model a process loss after the durable seal but before LifecycleJobRunner
    # reaches its final commit boundary.
    started = repository.start_run(run.id)
    result = engine.execute(
        started,
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        Event(),
    )
    assert result.sealed_aggregate_ids
    assert len(provider.requests) == 1

    recovery = repository.reconcile_startup_jobs()
    assert recovery.resubmit_run_ids == [run.id]

    completed = _run(repository, engine, secrets, run.id)

    assert completed.status == RunStatus.SUCCEEDED
    assert len(provider.requests) == 1
    assert repository.get_stage_head(project.id, StageName.STORY_BIBLE).revision == 1


def test_later_provider_failure_retains_prior_trace_and_current_prompt(repository, brief) -> None:
    project = repository.create_project(brief)
    bible = all_stage_payloads()[0]
    provider = QueueProvider(
        [*_responses(bible), ProviderError("simulated second-stage provider failure")]
    )
    secrets = RunSecretBroker("trace-only-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        STAGE_ORDER[:2],
        provider_snapshot={"textModel": "fixture-model"},
    )

    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        secrets,
        run.id,
    )

    assert completed.status == RunStatus.FAILED
    trace = repository.get_run_trace(run.id)
    assert [attempt.status for attempt in trace.attempts] == [
        AttemptStatus.SUCCEEDED,
        AttemptStatus.FAILED,
    ]
    artifacts_by_stage = {
        stage: [artifact.kind for artifact in trace.artifacts if artifact.stage == stage]
        for stage in STAGE_ORDER[:2]
    }
    assert artifacts_by_stage[StageName.STORY_BIBLE] == [
        ArtifactKind.PROMPT,
        ArtifactKind.RESPONSE,
        ArtifactKind.VALIDATION,
        ArtifactKind.CANDIDATE,
    ]
    assert artifacts_by_stage[StageName.STORY_GRAPH] == [ArtifactKind.PROMPT]
    assert all(repository.get_stage_head(project.id, stage).revision == 0 for stage in STAGE_ORDER)
    assert "trace-only-secret" not in trace.model_dump_json()


def test_invalid_json_persists_response_before_local_parsing_quarantines(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    provider = QueueProvider(["not json"])
    secrets = RunSecretBroker("parse-only-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "fixture-model"},
    )

    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        secrets,
        run.id,
    )

    assert completed.status == RunStatus.QUARANTINED
    trace = repository.get_run_trace(run.id)
    assert [artifact.kind for artifact in trace.artifacts] == [
        ArtifactKind.PROMPT,
        ArtifactKind.RESPONSE,
        ArtifactKind.VALIDATION,
    ]
    response = trace.artifacts[1]
    validation = trace.artifacts[2]
    assert response.content["rawResponse"]["choices"][0]["message"]["content"] == "not json"
    assert validation.content["accepted"] is False
    assert validation.content["issues"][0]["code"] == "response.extraction"
    assert "parse-only-secret" not in trace.model_dump_json()


def test_cancellation_retains_completed_attempt_trace(repository, brief) -> None:
    project = repository.create_project(brief)
    bible = all_stage_payloads()[0]
    provider = QueueProvider(_responses(bible))
    secrets = RunSecretBroker("cancel-only-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        STAGE_ORDER[:2],
        provider_snapshot={"textModel": "fixture-model"},
    )
    runner = LifecycleJobRunner(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
        secret_registrar=secrets,
    )
    provider.after_response = lambda: runner.request_cancel(run.id)
    try:
        completed = runner.submit(run.id).result(timeout=5)
    finally:
        runner.close()

    assert completed.status == RunStatus.CANCELLED
    trace = repository.get_run_trace(run.id)
    assert [attempt.status for attempt in trace.attempts] == [AttemptStatus.CANCELLED]
    assert [artifact.kind for artifact in trace.artifacts] == [
        ArtifactKind.PROMPT,
        ArtifactKind.RESPONSE,
    ]
    assert all(repository.get_stage_head(project.id, stage).revision == 0 for stage in STAGE_ORDER)
    assert "cancel-only-secret" not in trace.model_dump_json()


def test_prompt_persistence_failure_prevents_provider_spend(
    repository,
    brief,
    monkeypatch,
) -> None:
    project = repository.create_project(brief)
    provider = QueueProvider(_responses(all_stage_payloads()[0]))
    secrets = RunSecretBroker("unspent-secret")
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "fixture-model"},
    )
    original_add_artifact = repository.add_artifact

    def fail_prompt_persistence(artifact: Artifact) -> Artifact:
        if artifact.kind == ArtifactKind.PROMPT:
            raise OSError("simulated trace persistence failure")
        return original_add_artifact(artifact)

    monkeypatch.setattr(repository, "add_artifact", fail_prompt_persistence)
    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        secrets,
        run.id,
    )

    assert completed.status == RunStatus.FAILED
    assert provider.requests == []
    trace = repository.get_run_trace(run.id)
    assert trace.artifacts == []
    assert [attempt.status for attempt in trace.attempts] == [AttemptStatus.FAILED]
    assert "unspent-secret" not in trace.model_dump_json()


def test_work_unit_quarantine_installs_no_heads_and_requires_an_explicit_rebuild(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    bible = all_stage_payloads()[0]
    initial_provider = QueueProvider([*_responses(bible), "{}"])
    initial_resolver = RecordingResolver(initial_provider)
    secrets = RunSecretBroker("server-secret")
    parent = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        STAGE_ORDER,
        provider_snapshot={"textModel": "fixture-model"},
    )

    quarantined = _run(
        repository,
        PipelineEngine(repository, initial_resolver, secrets),
        secrets,
        parent.id,
    )

    assert quarantined.status == RunStatus.QUARANTINED
    assert all(repository.get_stage_head(project.id, stage).revision == 0 for stage in STAGE_ORDER)
    parent_trace = repository.get_run_trace(parent.id)
    assert [attempt.stage for attempt in parent_trace.attempts] == [
        StageName.STORY_BIBLE,
        StageName.STORY_GRAPH,
    ]
    assert parent_trace.attempts[-1].status == AttemptStatus.FAILED
    assert parent_trace.attempts[-1].work_unit_id is not None

    with pytest.raises(InvalidTransitionError, match="exact work-unit repair"):
        repository.create_repair_run(
            parent.id,
            provider_snapshot={"textModel": "repair-model"},
        )

    rebuild = repository.create_run(
        project.id,
        RunKind.REBUILD,
        STAGE_ORDER[1:],
        provider_snapshot={"textModel": "rebuild-model"},
    )
    assert rebuild.requested_stages == list(STAGE_ORDER[1:])
    assert all(repository.get_stage_head(project.id, stage).revision == 0 for stage in STAGE_ORDER)


def test_legacy_unbound_repair_remains_compatible(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    bible = all_stage_payloads()[0]
    secrets = RunSecretBroker("legacy-repair-secret")
    parent = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "parent-model"},
    )
    repository.start_run(parent.id)
    attempt = repository.create_attempt(parent.id, StageName.STORY_BIBLE)
    response = {"rawResponse": "{}"}
    validation = {
        "accepted": False,
        "issues": [{"code": "schema", "message": "missing story bible"}],
    }
    for kind, content in (
        (ArtifactKind.RESPONSE, response),
        (ArtifactKind.VALIDATION, validation),
    ):
        repository.add_artifact(
            Artifact(
                run_id=parent.id,
                attempt_id=attempt.id,
                stage=StageName.STORY_BIBLE,
                kind=kind,
                content=content,
                content_hash=stable_hash(content),
            )
        )
    repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="invalid bible")
    repository.finish_run(parent.id, quarantine_reason="invalid bible")

    repair = repository.create_repair_run(
        parent.id,
        provider_snapshot={"textModel": "legacy-repair-model"},
    )
    repair_provider = QueueProvider(_responses(bible))
    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(repair_provider), secrets),
        secrets,
        repair.id,
    )

    assert completed.status == RunStatus.SUCCEEDED
    assert len(repair_provider.requests) == 1
    assert "修复" in repair_provider.requests[0].messages[0].content
    assert repository.get_stage_payload(project.id, StageName.STORY_BIBLE) == bible
    assert "legacy-repair-secret" not in repository.get_run_trace(repair.id).model_dump_json()


def test_preexisting_work_unit_repair_is_rejected_before_provider_dispatch(
    repository,
    brief,
    monkeypatch,
) -> None:
    project = repository.create_project(brief)
    parent = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "parent-model"},
    )
    repository.start_run(parent.id)
    attempt = repository.create_attempt(parent.id, StageName.STORY_BIBLE)
    response = {"rawResponse": "{}"}
    validation = {"accepted": False, "issues": []}
    for kind, content in (
        (ArtifactKind.RESPONSE, response),
        (ArtifactKind.VALIDATION, validation),
    ):
        repository.add_artifact(
            Artifact(
                run_id=parent.id,
                attempt_id=attempt.id,
                stage=StageName.STORY_BIBLE,
                kind=kind,
                content=content,
                content_hash=stable_hash(content),
            )
        )
    repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="invalid bible")
    repository.finish_run(parent.id, quarantine_reason="invalid bible")
    repair = repository.create_repair_run(
        parent.id,
        provider_snapshot={"textModel": "repair-model"},
    )

    original_get_run_trace = repository.get_run_trace
    parent_trace = original_get_run_trace(parent.id)
    guarded_trace = parent_trace.model_copy(
        update={
            "attempts": [
                item.model_copy(update={"work_unit_id": "migrated-work-unit"})
                if item.id == attempt.id
                else item
                for item in parent_trace.attempts
            ]
        }
    )

    def get_run_trace_with_migrated_attempt(run_id: str):
        if run_id == parent.id:
            return guarded_trace
        return original_get_run_trace(run_id)

    monkeypatch.setattr(repository, "get_run_trace", get_run_trace_with_migrated_attempt)
    provider = QueueProvider(_responses(all_stage_payloads()[0]))
    secrets = RunSecretBroker("secret")
    completed = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(provider), secrets),
        secrets,
        repair.id,
    )

    assert completed.status == RunStatus.FAILED
    assert "exact work-unit repair" in (completed.error or "")
    assert provider.requests == []
