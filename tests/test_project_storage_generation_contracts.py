"""Regression coverage for generation contracts owned by one project folder.

These tests intentionally drive the production ``ProjectStore`` and its typed
generation owner.  They prove retained behavior without recreating a shared
repository facade or a compatibility storage mode.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest
from sqlalchemy import select

import plotloom.work_unit_pipeline as work_unit_pipeline
from plotloom.artifacts import LocalArtifactStore
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import GenerationAttemptKind, ProviderSettings, RunKind, RunStatus, StageName
from plotloom.exceptions import RepairEligibilityError, RevisionConflictError
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse, ProviderUsage
from plotloom.jobs import LifecycleJobRunner
from plotloom.pipeline import PipelineEngine, RunSecretBroker
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from plotloom.project_storage.application_profiles import ApplicationProfileRepository
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext
from plotloom.persistence.schema.project_generation import ArtifactRow
from tests.project_storage_fixtures import FixtureProvider, fixture_profile


class _ProcessLoss(BaseException):
    """Model a process loss after a response has committed but before local work."""


class _QueueProvider:
    """Offline provider that can interleave rejected and valid fixture responses."""

    name = "project-contract-fixture"
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(self, responses: list[str], *, on_request=None, echo_secret: bool = False) -> None:
        self._responses = deque(responses)
        self._fixture = FixtureProvider()
        self.on_request = on_request
        self.echo_secret = echo_secret
        self.requests = []

    def generate(self, request, secret):
        self.requests.append(request)
        if self.on_request is not None:
            self.on_request(request)
        response = self._next_response(request)
        if self.echo_secret:
            assert secret is not None
            with secret.reveal() as value:
                response = response.model_copy(
                    update={
                        "raw": {
                            **response.raw,
                            "apiKey": "provider-echoed-secret",
                            "providerDiagnostic": f"outbound credential was {value}",
                        }
                    }
                )
        return response

    def _next_response(self, request) -> ProviderResponse:
        response = self._responses.popleft()
        if response == "fixture":
            fixture_response = self._fixture.generate(request, None)
            return fixture_response.model_copy(
                update={"provider": self.name, "model": request.model, "request_id": f"request-{len(self.requests)}"}
            )
        if response == "reasoning-only":
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                finish_reason="length",
                final_content=None,
                reasoning_present=True,
                outcome_code="response.missing_final_content",
                raw={
                    "choices": [{"message": {"role": "assistant", "content": [
                        {"type": "reasoning", "text": "private reasoning must never be reused"},
                        {"type": "unknown", "content": "unknown content must never be reused"},
                    ]}}]
                },
            )
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            request_id=f"request-{len(self.requests)}",
            raw={"choices": [{"message": {"role": "assistant", "content": response}}]},
            usage=ProviderUsage(input_tokens=1, output_tokens=1),
        )


class _Resolver:
    def __init__(self, provider: _QueueProvider) -> None:
        self.provider = provider

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _RejectFinalStoryboardProvider:
    """Creates one exact-repair candidate while retaining all sibling evidence."""

    def __init__(self) -> None:
        self.delegate = FixtureProvider()
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.storyboard_requests = 0

    def generate(self, request, secret):
        prompt = "\n".join(message.content for message in request.messages)
        if "【目标戏剧场景】" in prompt:
            self.storyboard_requests += 1
            if self.storyboard_requests == 9:
                return ProviderResponse(
                    provider=self.name,
                    model=request.model,
                    raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                    usage=ProviderUsage(input_tokens=1, output_tokens=1),
                )
        return self.delegate.generate(request, secret)


class _RejectFinalStoryboardResolver:
    def __init__(self) -> None:
        self.provider = _RejectFinalStoryboardProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def _store(tmp_path: Path) -> ProjectStore:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    return storage.projects.create(FIXED_CHINESE_BRIEF)


def _create_bible_run(store: ProjectStore, profile) -> object:
    snapshot = profile.model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        return store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=snapshot,
        )


def _execute(
    store: ProjectStore,
    run_id: str,
    provider: _QueueProvider,
    broker: RunSecretBroker,
    *,
    session_api_key: str | None = None,
):
    runner = LifecycleJobRunner(
        store.generation,
        PipelineEngine(store.generation, _Resolver(provider), broker),
        RunContext(providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")),
        max_workers=1,
        secret_registrar=broker,
    )
    try:
        return runner.submit(run_id, session_api_key=session_api_key).result()
    finally:
        runner.close()


def test_project_generation_caps_corrections_and_keeps_durable_lineage(tmp_path: Path) -> None:
    store = _store(tmp_path)
    profile = fixture_profile()
    run = _create_bible_run(store, profile)
    provider = _QueueProvider(["not json", "still not json", "not JSON either"])
    broker = RunSecretBroker()
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    trace = store.run_trace(run.id)
    assert completed.status == RunStatus.QUARANTINED
    assert len(provider.requests) == 3
    assert [attempt.attempt_number for attempt in trace.attempts] == [1, 2, 3]
    assert [attempt.source_attempt_id for attempt in trace.attempts] == [None, trace.attempts[0].id, trace.attempts[1].id]
    assert [attempt.attempt_kind for attempt in trace.attempts] == [
        GenerationAttemptKind.PRIMARY,
        GenerationAttemptKind.CORRECTION,
        GenerationAttemptKind.CORRECTION,
    ]
    prompts = [artifact.content["contract"] for artifact in trace.artifacts if artifact.kind.value == "prompt"]
    assert [prompt["correction_ordinal"] for prompt in prompts] == [None, 1, 2]
    assert [prompt["correction_strategy"] for prompt in prompts] == [None, "repair_previous_final", "reconstruct_from_schema"]


def test_project_generation_dispatches_before_call_and_never_reuses_reasoning(tmp_path: Path) -> None:
    store = _store(tmp_path)
    profile = fixture_profile()
    run = _create_bible_run(store, profile)

    def assert_durable_dispatch(request) -> None:
        attempt = next(item for item in store.run_trace(run.id).attempts if item.id == request.metadata["attempt_id"])
        assert attempt.dispatched_at is not None

    provider = _QueueProvider(["reasoning-only", "fixture"], on_request=assert_durable_dispatch)
    broker = RunSecretBroker()
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    trace = store.run_trace(run.id)
    assert completed.status == RunStatus.SUCCEEDED
    assert [attempt.outcome_code for attempt in trace.attempts] == ["response.missing_final_content", "response.accepted"]
    correction_prompt = provider.requests[1].messages[1].content
    assert "response.missing_final_content" in correction_prompt
    assert "private reasoning must never be reused" not in correction_prompt
    assert "unknown content must never be reused" not in correction_prompt


@pytest.mark.parametrize("response_sequence, crashed_kind", [(["fixture"], GenerationAttemptKind.PRIMARY), (["not json", "fixture"], GenerationAttemptKind.CORRECTION)])
def test_project_generation_recovers_durable_primary_and_correction_responses_without_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, response_sequence: list[str], crashed_kind: GenerationAttemptKind
) -> None:
    store = _store(tmp_path)
    run = _create_bible_run(store, fixture_profile())
    provider = _QueueProvider(response_sequence)
    broker = RunSecretBroker()
    original_persist = store.generation.persist_attempt_response

    def persist_then_lose_process(attempt_id, content, *, provider_request_id=None):
        artifact = original_persist(attempt_id, content, provider_request_id=provider_request_id)
        attempt = next(item for item in store.run_trace(run.id).attempts if item.id == attempt_id)
        if attempt.attempt_kind == crashed_kind:
            raise _ProcessLoss()
        return artifact

    monkeypatch.setattr(store.generation, "persist_attempt_response", persist_then_lose_process)
    try:
        with pytest.raises(_ProcessLoss):
            _execute(store, run.id, provider, broker)
        before = store.run_trace(run.id)
        crashed = next(item for item in before.attempts if item.attempt_kind == crashed_kind)
        assert crashed.response_persisted_at is not None
        calls_before_recovery = len(provider.requests)
        monkeypatch.setattr(store.generation, "persist_attempt_response", original_persist)
        assert store.generation.reconcile_startup_jobs().resubmit_run_ids == [run.id]
        assert _execute(store, run.id, provider, broker).status == RunStatus.SUCCEEDED
    finally:
        broker.close()

    after = store.run_trace(run.id)
    assert len(provider.requests) == calls_before_recovery
    assert next(item for item in after.attempts if item.id == crashed.id).response_persisted_at is not None


def test_project_generation_redacts_provider_secret_echoes_before_project_persistence(tmp_path: Path) -> None:
    store = _store(tmp_path)
    profile_values = fixture_profile().model_dump(mode="json", by_alias=True)
    profile_values.update(textAuthMode="bearer", profileHash="")
    profile = type(fixture_profile()).model_validate(profile_values)
    run = _create_bible_run(store, profile)
    provider = _QueueProvider(["fixture"], echo_secret=True)
    secret = "project-folder-provider-secret"
    broker = RunSecretBroker(server_profile_keys={profile.profile_id: secret})
    try:
        assert _execute(store, run.id, provider, broker).status == RunStatus.SUCCEEDED
    finally:
        broker.close()

    trace_json = store.run_trace(run.id).model_dump_json()
    assert secret not in trace_json
    assert "provider-echoed-secret" not in trace_json
    assert secret.encode() not in (store.home / "project.sqlite3").read_bytes()


def test_application_profiles_freeze_run_snapshots_and_keep_session_keys_out_of_project_state(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    values = fixture_profile().model_dump(mode="json", by_alias=True)
    values.update(textAuthMode="bearer", profileHash="")
    bearer_profile = type(fixture_profile()).model_validate(values)
    profiles = ApplicationProfileRepository(storage.application, ProviderSettings())
    saved = profiles.create_text_provider_profile(
        "project_owner_profile", "Project owner profile", configuration=bearer_profile
    )
    assert profiles.activate_text_provider_profile(saved.profile_id, 0).revision == 1
    with pytest.raises(RevisionConflictError):
        profiles.activate_text_provider_profile(saved.profile_id, 0)

    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    run = _create_bible_run(store, saved.configuration)
    updated = profiles.update_text_provider_profile(
        saved.profile_id,
        saved.revision,
        display_name=saved.display_name,
        configuration=saved.configuration.model_copy(update={"text_model": "later-fixture-model"}),
    )
    assert updated.revision == saved.revision + 1
    assert store.generation.get_run(run.id).provider_snapshot["textModel"] == "fixture-model"

    session_key = "project-owner-session-key"
    broker = RunSecretBroker()
    try:
        assert _execute(
            store, run.id, _QueueProvider(["fixture"]), broker, session_api_key=session_key
        ).status == RunStatus.SUCCEEDED
    finally:
        broker.close()
    assert session_key not in store.run_trace(run.id).model_dump_json()
    assert session_key.encode() not in (store.home / "project.sqlite3").read_bytes()


def test_project_generation_rejects_tampered_correction_audit_before_second_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    run = _create_bible_run(store, fixture_profile())
    provider = _QueueProvider(["not json", "fixture"])
    original_compile = work_unit_pipeline.compile_correction_instruction_plan

    def compile_with_tampered_audit(*args, **kwargs):
        plan = original_compile(*args, **kwargs)
        return plan.model_copy(update={"audit_issue_selection": {**plan.audit_issue_selection, "tampered": True}})

    monkeypatch.setattr(work_unit_pipeline, "compile_correction_instruction_plan", compile_with_tampered_audit)
    broker = RunSecretBroker()
    try:
        completed = _execute(store, run.id, provider, broker)
    finally:
        broker.close()

    assert completed.status == RunStatus.FAILED
    assert len(provider.requests) == 1
    assert [attempt.outcome_code for attempt in store.run_trace(run.id).attempts] == [
        "response.extraction",
        "contract.correction_source_changed",
    ]


def test_project_exact_repair_refuses_tampered_response_evidence_without_creating_a_child(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    profile = fixture_profile(max_semantic_corrections=0)
    parent = ProjectPipelineExecutor(_RejectFinalStoryboardResolver()).execute(store, profile=profile)
    assert parent.status == RunStatus.QUARANTINED
    target = next(unit for unit in store.generation.list_generation_work_units(parent.id) if unit.status.value == "quarantined")
    response = next(
        artifact for artifact in store.run_trace(parent.id).artifacts
        if artifact.work_unit_id == target.id and artifact.kind.value == "response"
    )
    with store.repository._write() as session:  # noqa: SLF001 - corruption boundary proof
        row = session.scalar(select(ArtifactRow).where(ArtifactRow.id == response.id))
        assert row is not None
        row.content_hash = "0" * 64

    with store.generation.admit_provider_snapshot(profile.model_dump(mode="json", by_alias=True)):
        with pytest.raises(RepairEligibilityError, match="repair"):
            store.generation.create_work_unit_repair_run(
                parent.id, target.id, idempotency_key="tampered-project-evidence"
            )
    assert [run.id for run in store.generation_runs()] == [parent.id]
