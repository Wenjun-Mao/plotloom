"""Transition-only E2E runtime for retained multi-project browser journeys.

The production executable is ``build_runtime_app``.  This fixture keeps the
legacy browser matrix isolated while project lifecycle/caller migration remains
a separately owned slice; it does not consume production storage settings.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from typing import Any

import uvicorn

from plotloom.api import create_app
from plotloom.artifacts import LocalArtifactStore
from plotloom.domain import ProviderProfileCapabilities, ProviderSettings
from plotloom.jobs import LifecycleJobRunner
from plotloom.managed_media import ManagedMediaLimits
from plotloom.media import MediaPromptCompiler
from plotloom.media_jobs import MediaJobRunner, MediaTaskSecretBroker
from plotloom.offline_wan_fake import OfflineWanFake
from plotloom.persistence import SQLiteRepository
from plotloom.pipeline import PipelineEngine, RunContext, RunSecretBroker, SnapshotTextProviderResolver
from plotloom.provider_profiles import (
    PresetId,
    StageMaxOutputTokens,
    TextProviderCapabilities,
    TextProviderProfileSnapshot,
    V2ExtractionPolicy,
)
from plotloom.providers import ProviderPorts
from plotloom.runtime import recover_runtime_jobs
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_jobs import VideoJobService


H3_FIXTURE_DIRECTORY = Path(__file__).parent / "video_backends" / "minimax_h3"
sys.path.insert(0, str(H3_FIXTURE_DIRECTORY))
from offline_gateway import OfflineH3GatewayFake  # noqa: E402


database_path = Path(os.environ["PLOTLOOM_E2E_LEGACY_DATABASE_PATH"])
artifact_root = Path(os.environ["PLOTLOOM_E2E_LEGACY_ARTIFACT_ROOT"])
image_exchange_root = Path(os.environ["PLOTLOOM_E2E_LEGACY_IMAGE_EXCHANGE_ROOT"])
mode = os.environ.get("PLOTLOOM_E2E_VIDEO_ADAPTER", "wan")

repository = SQLiteRepository(f"sqlite:///{database_path}")
artifacts = LocalArtifactStore(artifact_root)
secrets = RunSecretBroker(None)
resolver = SnapshotTextProviderResolver()
provider_defaults = ProviderSettings(
    text_provider="openai-compatible",
    text_base_url="https://api.atlascloud.ai/v1",
    text_model="deepseek-v3",
    text_auth_mode="none",
    text_capabilities=ProviderProfileCapabilities(),
)
profile = TextProviderProfileSnapshot.model_validate(
    {
        "profileSchemaVersion": 2,
        "profileId": "default",
        "profileVersion": 0,
        "profileHash": "",
        "textProvider": provider_defaults.text_provider,
        "textBaseUrl": provider_defaults.text_base_url,
        "textModel": provider_defaults.text_model,
        "textAuthMode": provider_defaults.text_auth_mode,
        "textCapabilities": TextProviderCapabilities(),
        "textContextWindowTokens": provider_defaults.text_context_window_tokens,
        "textMaxOutputTokens": provider_defaults.text_max_output_tokens,
        "textTemperature": provider_defaults.text_temperature,
        "textMaxConcurrency": provider_defaults.text_max_concurrency,
        "textConnectTimeoutSeconds": provider_defaults.text_connect_timeout_seconds,
        "textAttemptTimeoutSeconds": provider_defaults.text_attempt_timeout_seconds,
        "redirectPolicy": "no_follow",
        "requestExtension": "none",
        "reasoningMode": "provider_default",
        "extractionPolicy": V2ExtractionPolicy(),
        "stageMaxOutputTokens": StageMaxOutputTokens(
            story_bible=8192,
            story_graph=8192,
            scene_beats=4096,
            storyboard=4096,
        ),
        "maxSemanticCorrections": 2,
        "presetId": PresetId.CUSTOM,
        "presetVersion": "1",
    }
)
pipeline = PipelineEngine(repository, resolver, secrets)
run_runner = LifecycleJobRunner(
    repository,
    pipeline,
    RunContext(providers=ProviderPorts(), artifacts=artifacts),
    secret_registrar=secrets,
)
media_runner = MediaJobRunner(repository, MediaTaskSecretBroker())
if mode == "wan":
    video_service = VideoJobService(repository, artifacts, OfflineWanFake())
elif mode == "h3":
    video_service = VideoJobService(
        repository,
        artifacts,
        OfflineH3GatewayFake(),
        adapter=MiniMaxH3GatewayAdapter(),
    )
else:
    raise RuntimeError("PLOTLOOM_E2E_VIDEO_ADAPTER must be wan or h3")


@asynccontextmanager
async def lifespan(_app: Any):
    try:
        _app.state.video_startup_recovery = repository.recover_video_dispatches()
        _app.state.startup_recovery = recover_runtime_jobs(
            repository, run_runner, media_runner
        )
        yield
    finally:
        run_runner.close()
        media_runner.close()
        secrets.close()
        repository.close()


app = create_app(
    repository,
    run_scheduler=run_runner,
    media_scheduler=media_runner,
    media_prompt_compiler=MediaPromptCompiler(),
    video_job_service=video_service,
    artifact_store=artifacts,
    managed_media_limits=ManagedMediaLimits(),
    image_exchange_root=image_exchange_root,
    provider_defaults=provider_defaults,
    key_availability={
        "text_key_available": False,
        "image_key_available": False,
        "video_key_available": False,
    },
    text_profile_default=profile,
    profile_key_available=secrets.server_key_available,
    text_provider_resolver=resolver,
    text_secret_source=secrets,
    lifespan=lifespan,
)

uvicorn.run(app, host=os.environ.get("PLOTLOOM_HOST", "127.0.0.1"), port=int(os.environ["PLOTLOOM_PORT"]))
