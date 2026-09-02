from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable

from plotloom.artifacts import MemoryArtifactStore
from plotloom.domain import (
    STAGE_ORDER,
    Artifact,
    ArtifactKind,
    AttemptStatus,
    RunKind,
    RunStatus,
    StageName,
)
from plotloom.generation.contracts import (
    GenerationRequest,
    ProviderCapabilities,
    ProviderResponse,
    ProviderUsage,
)
from plotloom.generation.exceptions import ProviderError
from plotloom.generation.secrets import SecretLease
from plotloom.jobs import LifecycleJobRunner
from plotloom.pipeline import PipelineEngine, RunSecretBroker
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


def test_pipeline_generates_traces_then_commits_all_stages_atomically(repository, brief) -> None:
    project = repository.create_project(brief)
    payloads = all_stage_payloads()
    provider = QueueProvider(_responses(*payloads))
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

    completed = _run(repository, PipelineEngine(repository, resolver, secrets), secrets, run.id)

    assert completed.status == RunStatus.SUCCEEDED
    assert resolver.snapshots == [run.provider_snapshot]
    assert provider.observed_secrets == ["server-only-secret"] * 4
    trace = repository.get_run_trace(run.id)
    assert [attempt.status for attempt in trace.attempts] == [AttemptStatus.SUCCEEDED] * 4
    assert [artifact.kind for artifact in trace.artifacts].count(ArtifactKind.CANDIDATE) == 4
    assert [artifact.kind for artifact in trace.artifacts].count(ArtifactKind.CANONICAL) == 4
    first_response = next(
        artifact for artifact in trace.artifacts if artifact.kind == ArtifactKind.RESPONSE
    )
    assert first_response.content["providerRequestId"] == "provider-request-1"
    assert first_response.content["finishReason"] == "stop"
    assert first_response.content["usage"] == {"inputTokens": 10, "outputTokens": 20}
    assert all(repository.get_stage_head(project.id, stage).revision == 1 for stage in STAGE_ORDER)
    assert "server-only-secret" not in trace.model_dump_json()


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
    assert response.content["rawResponse"] == "not json"
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
    assert [attempt.status for attempt in trace.attempts] == [AttemptStatus.SUCCEEDED]
    assert [artifact.kind for artifact in trace.artifacts] == [
        ArtifactKind.PROMPT,
        ArtifactKind.RESPONSE,
        ArtifactKind.VALIDATION,
        ArtifactKind.CANDIDATE,
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


def test_quarantine_installs_no_partial_heads_and_explicit_repair_resumes(repository, brief) -> None:
    project = repository.create_project(brief)
    bible, graph, scene_beats, storyboard = all_stage_payloads()
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

    repair = repository.create_repair_run(
        parent.id,
        provider_snapshot={"textModel": "repair-model"},
    )
    assert repair.repair_stage == StageName.STORY_GRAPH
    assert repair.repair_source is not None
    frozen_bible_artifact_id = repair.repair_source.reused_candidate_artifact_ids[
        StageName.STORY_BIBLE
    ]
    poison = bible.model_copy(update={"logline": "LATE APPENDED CANDIDATE"}).model_dump(
        mode="json", by_alias=False
    )
    repository.add_artifact(
        Artifact(
            run_id=parent.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.CANDIDATE,
            content=poison,
            content_hash=stable_hash(poison),
        )
    )
    repair_provider = QueueProvider(_responses(graph, scene_beats, storyboard))
    repair_resolver = RecordingResolver(repair_provider)
    repaired = _run(
        repository,
        PipelineEngine(repository, repair_resolver, secrets),
        secrets,
        repair.id,
    )

    assert repaired.status == RunStatus.SUCCEEDED
    assert len(repair_provider.requests) == 3
    assert "修复" in repair_provider.requests[0].messages[0].content
    assert all(repository.get_stage_head(project.id, stage).revision == 1 for stage in STAGE_ORDER)
    repair_trace = repository.get_run_trace(repair.id)
    reused_bible = next(
        artifact
        for artifact in repair_trace.artifacts
        if artifact.stage == StageName.STORY_BIBLE and artifact.kind == ArtifactKind.CANDIDATE
    )
    assert reused_bible.attempt_id is None
    assert reused_bible.source_artifact_id == frozen_bible_artifact_id
    installed_bible = repository.get_stage_payload(project.id, StageName.STORY_BIBLE)
    assert installed_bible.logline == bible.logline


def test_multi_hop_repair_freezes_each_generation_of_lineage_and_finishes_downstream(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    bible, graph, scene_beats, storyboard = all_stage_payloads()
    secrets = RunSecretBroker("multi-hop-secret")

    parent_provider = QueueProvider([*_responses(bible), "{}"])
    parent = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        STAGE_ORDER,
        provider_snapshot={"textModel": "parent-model"},
    )
    parent_result = _run(
        repository,
        PipelineEngine(repository, RecordingResolver(parent_provider), secrets),
        secrets,
        parent.id,
    )

    assert parent_result.status == RunStatus.QUARANTINED
    parent_trace = repository.get_run_trace(parent.id)
    assert [attempt.stage for attempt in parent_trace.attempts] == [
        StageName.STORY_BIBLE,
        StageName.STORY_GRAPH,
    ]
    assert len(parent_provider.requests) == 2
    parent_graph_attempt = parent_trace.attempts[-1]
    parent_graph_response = next(
        artifact
        for artifact in parent_trace.artifacts
        if artifact.attempt_id == parent_graph_attempt.id
        and artifact.kind == ArtifactKind.RESPONSE
    )
    parent_graph_validation = next(
        artifact
        for artifact in parent_trace.artifacts
        if artifact.attempt_id == parent_graph_attempt.id
        and artifact.kind == ArtifactKind.VALIDATION
    )
    parent_bible_candidate = next(
        artifact
        for artifact in parent_trace.artifacts
        if artifact.stage == StageName.STORY_BIBLE
        and artifact.kind == ArtifactKind.CANDIDATE
    )
    assert parent_graph_attempt.status == AttemptStatus.FAILED
    assert parent_graph_validation.content["accepted"] is False

    first_repair = repository.create_repair_run(
        parent.id,
        provider_snapshot={"textModel": "first-repair-model"},
    )
    assert first_repair.parent_run_id == parent.id
    assert first_repair.repair_stage == StageName.STORY_GRAPH
    assert first_repair.repair_source is not None
    assert first_repair.repair_source.failed_attempt_id == parent_graph_attempt.id
    assert first_repair.repair_source.response_artifact_id == parent_graph_response.id
    assert first_repair.repair_source.validation_artifact_id == parent_graph_validation.id
    assert first_repair.repair_source.reused_candidate_artifact_ids == {
        StageName.STORY_BIBLE: parent_bible_candidate.id,
    }

    first_repair_provider = QueueProvider([*_responses(graph), "{}"])
    first_repair_result = _run(
        repository,
        PipelineEngine(
            repository,
            RecordingResolver(first_repair_provider),
            secrets,
        ),
        secrets,
        first_repair.id,
    )

    assert first_repair_result.status == RunStatus.QUARANTINED
    first_repair_trace = repository.get_run_trace(first_repair.id)
    assert [attempt.stage for attempt in first_repair_trace.attempts] == [
        StageName.STORY_GRAPH,
        StageName.SCENE_BEATS,
    ]
    assert len(first_repair_provider.requests) == 2
    assert "修复" in first_repair_provider.requests[0].messages[0].content
    first_repair_bible = next(
        artifact
        for artifact in first_repair_trace.artifacts
        if artifact.stage == StageName.STORY_BIBLE
        and artifact.kind == ArtifactKind.CANDIDATE
    )
    first_repair_graph = next(
        artifact
        for artifact in first_repair_trace.artifacts
        if artifact.stage == StageName.STORY_GRAPH
        and artifact.kind == ArtifactKind.CANDIDATE
    )
    first_repair_beats_attempt = first_repair_trace.attempts[-1]
    first_repair_beats_response = next(
        artifact
        for artifact in first_repair_trace.artifacts
        if artifact.attempt_id == first_repair_beats_attempt.id
        and artifact.kind == ArtifactKind.RESPONSE
    )
    first_repair_beats_validation = next(
        artifact
        for artifact in first_repair_trace.artifacts
        if artifact.attempt_id == first_repair_beats_attempt.id
        and artifact.kind == ArtifactKind.VALIDATION
    )
    assert first_repair_bible.attempt_id is None
    assert first_repair_bible.source_artifact_id == parent_bible_candidate.id
    assert first_repair_graph.attempt_id == first_repair_trace.attempts[0].id
    assert first_repair_beats_attempt.status == AttemptStatus.FAILED
    assert first_repair_beats_validation.content["accepted"] is False
    assert all(
        repository.get_stage_head(project.id, stage).revision == 0
        for stage in STAGE_ORDER
    )

    second_repair = repository.create_repair_run(
        first_repair.id,
        provider_snapshot={"textModel": "second-repair-model"},
    )
    assert second_repair.parent_run_id == first_repair.id
    assert second_repair.repair_stage == StageName.SCENE_BEATS
    assert second_repair.repair_source is not None
    assert second_repair.repair_source.failed_attempt_id == first_repair_beats_attempt.id
    assert second_repair.repair_source.response_artifact_id == first_repair_beats_response.id
    assert (
        second_repair.repair_source.validation_artifact_id
        == first_repair_beats_validation.id
    )
    assert second_repair.repair_source.reused_candidate_artifact_ids == {
        StageName.STORY_BIBLE: first_repair_bible.id,
        StageName.STORY_GRAPH: first_repair_graph.id,
    }

    second_repair_provider = QueueProvider(_responses(scene_beats, storyboard))
    second_repair_result = _run(
        repository,
        PipelineEngine(
            repository,
            RecordingResolver(second_repair_provider),
            secrets,
        ),
        secrets,
        second_repair.id,
    )

    assert second_repair_result.status == RunStatus.SUCCEEDED
    second_repair_trace = repository.get_run_trace(second_repair.id)
    assert [attempt.stage for attempt in second_repair_trace.attempts] == [
        StageName.SCENE_BEATS,
        StageName.STORYBOARD,
    ]
    assert len(second_repair_provider.requests) == 2
    assert "修复" in second_repair_provider.requests[0].messages[0].content
    second_repair_bible = next(
        artifact
        for artifact in second_repair_trace.artifacts
        if artifact.stage == StageName.STORY_BIBLE
        and artifact.kind == ArtifactKind.CANDIDATE
    )
    second_repair_graph = next(
        artifact
        for artifact in second_repair_trace.artifacts
        if artifact.stage == StageName.STORY_GRAPH
        and artifact.kind == ArtifactKind.CANDIDATE
    )
    assert second_repair_bible.source_artifact_id == first_repair_bible.id
    assert second_repair_graph.source_artifact_id == first_repair_graph.id
    assert [
        artifact.stage
        for artifact in second_repair_trace.artifacts
        if artifact.kind == ArtifactKind.CANONICAL
    ] == list(STAGE_ORDER)
    assert all(
        repository.get_stage_head(project.id, stage).revision == 1
        for stage in STAGE_ORDER
    )
    assert repository.get_stage_payload(project.id, StageName.STORY_BIBLE) == bible
    assert repository.get_stage_payload(project.id, StageName.STORY_GRAPH) == graph
    assert repository.get_stage_payload(project.id, StageName.SCENE_BEATS) == scene_beats
    assert repository.get_stage_payload(project.id, StageName.STORYBOARD) == storyboard
    assert "multi-hop-secret" not in parent_trace.model_dump_json()
    assert "multi-hop-secret" not in first_repair_trace.model_dump_json()
    assert "multi-hop-secret" not in second_repair_trace.model_dump_json()
