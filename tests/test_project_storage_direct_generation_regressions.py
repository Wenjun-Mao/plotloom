"""Fault-boundary regressions for direct project-folder generation.

These scenarios deliberately exercise the production ``ProjectStore`` path.
They replace the former shared-repository pipeline fixture without adding a
compatibility facade or a second persistence mode.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from threading import Event

import pytest

from plotloom.artifacts import LocalArtifactStore
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import ArtifactKind, AttemptStatus, GenerationAttemptKind, RunKind, RunStatus, STAGE_ORDER, StageName, WorkUnitStatus
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse, ProviderUsage
from plotloom.generation.exceptions import ProviderError, ProviderResponseError
from plotloom.jobs import LifecycleJobRunner
from plotloom.persistence import stable_hash
from plotloom.pipeline import PipelineEngine, RunSecretBroker
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext
from tests.project_storage_fixtures import FixtureProvider, FixtureResolver, fixture_profile


class _ProcessLoss(BaseException):
    """Model a process ending between two durable lifecycle boundaries."""


class _Responses:
    """Offline adapter with explicit provider-boundary failures."""

    name = "project-fault-fixture"
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(self, responses: list[str | BaseException], *, echo_secret: bool = False) -> None:
        self._responses = deque(responses)
        self._fixture = FixtureProvider()
        self.echo_secret = echo_secret
        self.requests = []

    def generate(self, request, secret):
        self.requests.append(request)
        next_response = self._responses.popleft()
        if isinstance(next_response, BaseException):
            raise next_response
        if next_response == "fixture":
            response = self._fixture.generate(request, secret)
        else:
            response = ProviderResponse(
                provider=self.name,
                model=request.model,
                raw={"choices": [{"message": {"role": "assistant", "content": next_response}}]},
                usage=ProviderUsage(input_tokens=1, output_tokens=1),
            )
        if not self.echo_secret:
            return response
        assert secret is not None
        with secret.reveal() as value:
            return response.model_copy(
                update={
                    "raw": {
                        **response.raw,
                        "apiKey": "adapter-echoed-secret",
                        "providerDiagnostic": f"request used {value}",
                    }
                }
            )


class _Resolver:
    def __init__(self, provider: _Responses) -> None:
        self.provider = provider

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def _store(tmp_path: Path) -> ProjectStore:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    return storage.projects.create(FIXED_CHINESE_BRIEF)


def _run(store: ProjectStore, *, profile=None):
    profile = profile or fixture_profile()
    snapshot = profile.model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        run = store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=snapshot,
        )
    return run, profile


def _execute(store: ProjectStore, run_id: str, provider: _Responses, broker: RunSecretBroker):
    runner = LifecycleJobRunner(
        store.generation,
        PipelineEngine(store.generation, _Resolver(provider), broker),
        RunContext(providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")),
        max_workers=1,
        secret_registrar=broker,
    )
    try:
        return runner.submit(run_id).result()
    finally:
        runner.close()


def test_direct_generation_marks_ambiguous_provider_loss_unknown_without_replay_and_redacts_error(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    profile_values = fixture_profile().model_dump(mode="json", by_alias=True)
    profile_values.update(textAuthMode="bearer", profileHash="")
    bearer_profile = type(fixture_profile()).model_validate(profile_values)
    run, profile = _run(store, profile=bearer_profile)
    secret = "direct-project-provider-secret"
    provider = _Responses([ProviderError(f"connection ended after sending {secret}")])
    broker = RunSecretBroker(server_profile_keys={profile.profile_id: secret})
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    trace = store.run_trace(run.id)
    assert completed.status == RunStatus.FAILED
    assert completed.failure_code == "provider.outcome_unknown"
    assert completed.failed_stage == StageName.STORY_BIBLE
    assert len(provider.requests) == 1
    assert trace.attempts[0].outcome_unknown is True
    assert trace.attempts[0].outcome_code == "provider.outcome_unknown"
    assert store.generation.get_run_execution_trace(run.id).work_units[0].status == WorkUnitStatus.OUTCOME_UNKNOWN
    assert secret not in trace.model_dump_json()
    assert secret.encode() not in (store.home / "project.sqlite3").read_bytes()
    assert store.generation.reconcile_startup_jobs().resubmit_run_ids == []


def test_direct_generation_records_known_provider_response_failure_without_unknown_state(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    run, _profile = _run(store)
    provider = _Responses([ProviderResponseError("provider.http_503", status_code=503, request_id="known")])
    broker = RunSecretBroker()
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    attempt = store.run_trace(run.id).attempts[0]
    assert completed.status == RunStatus.FAILED
    assert completed.failure_code == "provider.http_503"
    assert completed.failed_stage == StageName.STORY_BIBLE
    assert len(provider.requests) == 1
    assert attempt.outcome_unknown is False
    assert attempt.outcome_code == "provider.http_503"
    assert store.generation.get_run_execution_trace(run.id).work_units[0].status == WorkUnitStatus.FAILED


def test_direct_generation_treats_response_persistence_loss_as_known_storage_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    run, _profile = _run(store)
    provider = _Responses(["fixture"])
    broker = RunSecretBroker()

    def reject_response(*_args, **_kwargs):
        raise OSError("simulated response storage failure")

    monkeypatch.setattr(store.generation, "persist_attempt_response", reject_response)
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    attempt = store.run_trace(run.id).attempts[0]
    assert completed.status == RunStatus.FAILED
    assert completed.failure_code == "storage.response_persist_failed"
    assert completed.failed_stage == StageName.STORY_BIBLE
    assert len(provider.requests) == 1
    assert attempt.outcome_unknown is False
    assert attempt.outcome_code == "storage.response_persist_failed"
    assert store.generation.get_run_execution_trace(run.id).work_units[0].status == WorkUnitStatus.FAILED


def test_direct_project_pipeline_seals_four_stages_then_installs_the_complete_prefix_atomically(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    profile = fixture_profile()

    completed = ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=profile)

    trace = store.run_trace(completed.id)
    execution = store.generation.get_run_execution_trace(completed.id)
    assert completed.status == RunStatus.SUCCEEDED
    assert trace.run.provider_snapshot == profile.model_dump(mode="json", by_alias=True)
    assert trace.attempts and all(attempt.status == AttemptStatus.SUCCEEDED for attempt in trace.attempts)
    assert sum(artifact.kind == ArtifactKind.CANDIDATE for artifact in trace.artifacts) == len(trace.attempts)
    assert sum(artifact.kind == ArtifactKind.CANONICAL for artifact in trace.artifacts) == len(STAGE_ORDER)
    assert [plan.stage for plan in execution.stage_plans] == list(STAGE_ORDER)
    assert [aggregate.stage for aggregate in execution.sealed_aggregates] == list(STAGE_ORDER)
    assert [envelope.head.stage for envelope in store.canonical_stages()] == list(STAGE_ORDER)
    assert all(envelope.head.revision == 1 for envelope in store.canonical_stages())


def test_direct_generation_binds_frozen_profile_prompt_plan_topology_and_seal_provenance(
    tmp_path: Path,
) -> None:
    """Every installed candidate remains traceable to one immutable run contract."""

    class RecordingFixtureProvider(FixtureProvider):
        def __init__(self) -> None:
            self.requests = []

        def generate(self, request, secret):
            self.requests.append(request)
            return super().generate(request, secret)

    class RecordingFixtureResolver:
        def __init__(self) -> None:
            self.provider = RecordingFixtureProvider()

        def resolve(self, provider_snapshot):
            return self.provider, str(provider_snapshot["textModel"])

    store = _store(tmp_path)
    profile = fixture_profile()
    resolver = RecordingFixtureResolver()
    completed = ProjectPipelineExecutor(resolver).execute(store, profile=profile)

    trace = store.run_trace(completed.id)
    execution = store.generation.get_run_execution_trace(completed.id)
    generation_plan = execution.generation_plan
    topology = execution.story_graph_topology
    assert generation_plan is not None
    assert topology is not None
    assert trace.run.provider_snapshot == profile.model_dump(mode="json", by_alias=True)
    assert generation_plan.plan["provider_profile_hash"] == profile.profile_hash
    assert generation_plan.plan["story_graph_topology_hash"] == topology.topology_hash
    assert topology.generation_plan_hash == generation_plan.plan_hash

    stage_plans = {item.stage: item for item in execution.stage_plans}
    work_units = {item.id: item for item in execution.work_units}
    prompts = [item for item in trace.artifacts if item.kind == ArtifactKind.PROMPT]
    requests = {
        request.metadata["attempt_id"]: request for request in resolver.provider.requests
    }
    assert len(prompts) == len(work_units)
    for prompt in prompts:
        contract = prompt.content["contract"]
        rendered = prompt.content["trace"]
        request = requests[prompt.attempt_id]
        work_unit = work_units[prompt.work_unit_id]
        stage_plan = stage_plans[prompt.stage]
        assert contract["stage_plan_hash"] == stage_plan.stage_plan_hash
        assert contract["work_unit_id"] == work_unit.id
        assert contract["work_unit_input_hash"] == work_unit.input_hash
        assert contract["dependency_hash"] == work_unit.dependency_hash
        assert contract["unit_dependency_hash"] == work_unit.unit_dependency_hash
        assert prompt.content["schemaId"] == contract["schema_id"]
        assert rendered["prompt_id"] == contract["prompt_id"]
        assert rendered["prompt_version"] == contract["prompt_version"]
        assert rendered["spec_hash"] == contract["prompt_spec_hash"]
        assert rendered["input_hash"] == contract["variables_hash"]
        assert rendered["rendered_hash"] == contract["rendered_hash"]
        assert request.metadata["prompt_hash"] == contract["rendered_hash"]
        assert request.response_schema is not None
        assert stable_hash(request.response_schema) == contract["schema_hash"]

    assert {item.stage for item in execution.sealed_aggregates} == set(STAGE_ORDER)
    for aggregate in execution.sealed_aggregates:
        stage_plan = stage_plans[aggregate.stage]
        assert aggregate.manifest["stagePlanHash"] == stage_plan.stage_plan_hash
        assert aggregate.manifest["generationPlanHash"] == generation_plan.plan_hash
        assert aggregate.manifest["dependencyHash"] == stage_plan.dependency_hash
        assert aggregate.manifest["aggregatePayloadHash"] == stable_hash(aggregate.payload)


def test_direct_generation_persists_invalid_raw_response_before_quarantining_without_install(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    run, _profile = _run(store)
    provider = _Responses(["not json", "not json", "not json"])
    broker = RunSecretBroker()
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    trace = store.run_trace(run.id)
    assert completed.status == RunStatus.QUARANTINED
    assert [artifact.kind for artifact in trace.artifacts[:3]] == [
        ArtifactKind.PROMPT,
        ArtifactKind.RESPONSE,
        ArtifactKind.VALIDATION,
    ]
    assert trace.artifacts[1].content["rawResponse"]["choices"][0]["message"]["content"] == "not json"
    assert trace.artifacts[2].content["accepted"] is False
    assert trace.artifacts[2].content["issues"][0]["code"] == "response.extraction"
    assert store.canonical_stages() == []


def test_direct_generation_restarts_a_predispatch_attempt_with_its_original_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    run, _profile = _run(store)
    provider = _Responses(["fixture"])
    broker = RunSecretBroker()
    original_dispatch = store.generation.mark_attempt_dispatched

    def lose_process_before_dispatch(_attempt_id: str):
        raise _ProcessLoss()

    monkeypatch.setattr(store.generation, "mark_attempt_dispatched", lose_process_before_dispatch)
    try:
        with pytest.raises(_ProcessLoss):
            _execute(store, run.id, provider, broker)
        before = store.run_trace(run.id)
        assert provider.requests == []
        assert len(before.attempts) == 1
        assert before.attempts[0].dispatched_at is None
        attempt_id = before.attempts[0].id
        monkeypatch.setattr(store.generation, "mark_attempt_dispatched", original_dispatch)
        assert store.generation.reconcile_startup_jobs().resubmit_run_ids == [run.id]
        assert _execute(store, run.id, provider, broker).status == RunStatus.SUCCEEDED
    finally:
        broker.close()

    after = store.run_trace(run.id)
    assert len(provider.requests) == 1
    assert [(attempt.id, attempt.attempt_number) for attempt in after.attempts] == [(attempt_id, 1)]


def test_direct_generation_recommits_complete_seals_after_restart_without_provider_replay(
    tmp_path: Path,
) -> None:
    """Recovery may cross the sealed commit point, never the provider boundary again."""

    store = _store(tmp_path)
    run, _profile = _run(store)
    provider = _Responses(["fixture"])
    broker = RunSecretBroker()
    engine = PipelineEngine(store.generation, _Resolver(provider), broker)
    try:
        sealed = engine.execute(
            store.generation.start_run(run.id),
            RunContext(
                providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")
            ),
            Event(),
        )
        assert sealed.sealed_aggregate_ids
        assert len(provider.requests) == 1
        assert store.canonical_stages() == []

        assert store.generation.reconcile_startup_jobs().resubmit_run_ids == [run.id]
        assert _execute(store, run.id, provider, broker).status == RunStatus.SUCCEEDED
    finally:
        broker.close()

    assert len(provider.requests) == 1
    assert [
        artifact.stage
        for artifact in store.run_trace(run.id).artifacts
        if artifact.kind == ArtifactKind.CANONICAL
    ] == [StageName.STORY_BIBLE]


@pytest.mark.parametrize(
    ("responses", "lost_kind"),
    [(["fixture"], GenerationAttemptKind.PRIMARY), (["not json", "fixture"], GenerationAttemptKind.CORRECTION)],
)
def test_direct_generation_reuses_a_durable_primary_or_correction_response_without_provider_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    responses: list[str],
    lost_kind: GenerationAttemptKind,
) -> None:
    store = _store(tmp_path)
    run, _profile = _run(store)
    provider = _Responses(responses)
    broker = RunSecretBroker()
    original_persist = store.generation.persist_attempt_response

    def persist_then_lose_process(attempt_id, content, *, provider_request_id=None):
        artifact = original_persist(attempt_id, content, provider_request_id=provider_request_id)
        attempt = next(item for item in store.run_trace(run.id).attempts if item.id == attempt_id)
        if attempt.attempt_kind == lost_kind:
            raise _ProcessLoss()
        return artifact

    monkeypatch.setattr(store.generation, "persist_attempt_response", persist_then_lose_process)
    try:
        with pytest.raises(_ProcessLoss):
            _execute(store, run.id, provider, broker)
        before = store.run_trace(run.id)
        lost = next(item for item in before.attempts if item.attempt_kind == lost_kind)
        calls_before_recovery = len(provider.requests)
        assert lost.response_persisted_at is not None
        monkeypatch.setattr(store.generation, "persist_attempt_response", original_persist)
        assert store.generation.reconcile_startup_jobs().resubmit_run_ids == [run.id]
        assert _execute(store, run.id, provider, broker).status == RunStatus.SUCCEEDED
    finally:
        broker.close()

    after = store.run_trace(run.id)
    assert len(provider.requests) == calls_before_recovery
    recovered = next(item for item in after.attempts if item.id == lost.id)
    assert recovered.response_persisted_at is not None
    assert recovered.attempt_kind == lost_kind
