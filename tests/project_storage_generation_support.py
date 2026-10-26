"""Shared current-fixture mutation and native project execution helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from plotloom.artifacts import LocalArtifactStore
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.run_contracts import RunKind
from plotloom.stage_contracts import StageName
from plotloom.generation.contracts import ProviderResponse
from plotloom.jobs import LifecycleJobRunner
from plotloom.pipeline import PipelineEngine
from plotloom.runtime_secrets import RunSecretBroker
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
        RunContext(
            providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")
        ),
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


def _with_payload(
    response: ProviderResponse, payload: dict[str, object]
) -> ProviderResponse:
    return response.model_copy(
        update={
            "raw": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    }
                ]
            }
        }
    )
