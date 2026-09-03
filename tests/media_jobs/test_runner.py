from __future__ import annotations

import time
from collections import deque
from concurrent.futures import Future
from threading import Event

import pytest
from pydantic import ValidationError

from plotloom.domain import MediaKind, MediaTaskStatus
from plotloom.media import MediaPollResult, MediaProviderError, MediaSubmission
from plotloom.media_jobs import MediaJobRunner, MediaTaskSecretBroker
from tests.media_jobs.conftest import make_media_task


class ScriptedGateway:
    def __init__(self, submissions, polls=()):
        self.submissions = deque(submissions)
        self.polls = deque(polls)
        self.seen_keys: list[str] = []
        self.submit_calls: list[dict[str, object]] = []
        self.poll_calls: list[str] = []

    def submit(self, *, adapter, params, base_url, secret, auth_mode):
        if secret is not None:
            with secret.reveal() as api_key:
                self.seen_keys.append(api_key)
        self.submit_calls.append(
            {
                "adapter": adapter.name,
                "params": params,
                "base_url": base_url,
                "auth_mode": auth_mode,
            }
        )
        return self.submissions.popleft()

    def poll(self, *, adapter, provider_task_id, base_url, secret, auth_mode):
        if secret is not None:
            with secret.reveal() as api_key:
                self.seen_keys.append(api_key)
        self.poll_calls.append(provider_task_id)
        return self.polls.popleft()


def test_media_future_cleanup_preserves_newer_mapping(repository) -> None:
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(),
        gateway=ScriptedGateway([]),
        poll_interval_seconds=0,
    )
    stale: Future = Future()
    replacement: Future = Future()
    runner._futures["same-task"] = replacement
    try:
        runner._forget_future("same-task", stale)
        assert runner._futures["same-task"] is replacement
    finally:
        runner._futures.pop("same-task", None)
        runner.close()


def test_session_override_beats_server_key_and_neither_is_persisted(
    repository,
    prepared_project,
):
    first = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example/v1", "imageModel": "image-x"},
    )
    second = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example/v1"},
    )
    gateway = ScriptedGateway(
        [
            MediaSubmission("openai", None, "succeeded", ("https://cdn.example/one.png",)),
            MediaSubmission("openai", None, "succeeded", ("https://cdn.example/two.png",)),
        ]
    )
    broker = MediaTaskSecretBroker(image_api_key="server-image-key")
    runner = MediaJobRunner(repository, broker, gateway=gateway, poll_interval_seconds=0)
    try:
        callbacks_finished = Event()
        first_future = runner.submit(first.id, session_api_key="session-image-key")
        first_future.add_done_callback(lambda _completed: callbacks_finished.set())
        first_result = first_future.result(timeout=2)
        assert callbacks_finished.wait(timeout=1)
        assert first.id not in runner._futures
        second_result = runner.submit(second.id).result(timeout=2)
    finally:
        runner.close()

    assert first_result.status == MediaTaskStatus.SUCCEEDED
    assert second_result.status == MediaTaskStatus.SUCCEEDED
    assert gateway.seen_keys == ["session-image-key", "server-image-key"]
    serialized = first_result.model_dump_json() + second_result.model_dump_json()
    assert "session-image-key" not in serialized
    assert "server-image-key" not in serialized
    assert gateway.submit_calls[0]["params"]["model"] == "image-x"


def test_async_video_submission_polls_and_persists_provider_task_id(
    repository,
    prepared_project,
):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.VIDEO,
        provider="atlascloud",
        public_settings={
            "videoBaseUrl": "https://api.example/v1",
            "videoModel": "video-x",
            "imageUrl": "https://cdn.example/keyframe.jpg",
        },
    )
    gateway = ScriptedGateway(
        [MediaSubmission("atlascloud", "provider-task-7", "processing")],
        [
            MediaPollResult("processing"),
            MediaPollResult("succeeded", ("https://cdn.example/output.mp4",)),
        ],
    )
    sleeps: list[float] = []
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(video_api_key="video-key"),
        gateway=gateway,
        poll_interval_seconds=0.25,
        sleeper=sleeps.append,
    )
    try:
        result = runner.submit(task.id).result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.SUCCEEDED
    assert result.provider == "atlascloud"
    assert result.provider_task_id == "provider-task-7"
    assert result.output_uri == "https://cdn.example/output.mp4"
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.updated_at == result.finished_at
    assert gateway.poll_calls == ["provider-task-7", "provider-task-7"]
    assert sleeps == [0.25, 0.25]
    assert gateway.submit_calls[0]["params"]["image_url"].endswith("keyframe.jpg")
    assert gateway.submit_calls[0]["params"]["duration"] == 8


def test_recovered_running_media_task_only_polls_with_server_key(
    repository,
    prepared_project,
):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example/v1"},
    )
    repository.start_media_task(task.id, provider="openai")
    repository.record_media_submission(
        task.id,
        provider="openai",
        provider_task_id="provider-task-resume",
    )
    gateway = ScriptedGateway(
        [],
        [MediaPollResult("succeeded", ("https://cdn.example/recovered.png",))],
    )
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(image_api_key="server-image-key"),
        gateway=gateway,
        poll_interval_seconds=0,
    )
    try:
        result = runner.submit(task.id).result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.SUCCEEDED
    assert gateway.submit_calls == []
    assert gateway.poll_calls == ["provider-task-resume"]
    assert gateway.seen_keys == ["server-image-key"]


def test_recovered_media_without_server_key_fails_without_resubmission(
    repository,
    prepared_project,
):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example/v1"},
    )
    repository.start_media_task(task.id, provider="openai")
    repository.record_media_submission(
        task.id,
        provider="openai",
        provider_task_id="provider-task-needs-key",
    )
    gateway = ScriptedGateway([])
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(),
        gateway=gateway,
        poll_interval_seconds=0,
    )
    try:
        result = runner.submit(task.id).result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.FAILED
    assert "No image API key" in result.error
    assert gateway.submit_calls == []
    assert gateway.poll_calls == []


class SignallingSecretBroker(MediaTaskSecretBroker):
    def __init__(self, *, image_api_key: str) -> None:
        super().__init__(image_api_key=image_api_key)
        self.lease_started = Event()

    def lease(self, task_id, kind, *, auth_mode):
        lease = super().lease(task_id, kind, auth_mode=auth_mode)
        self.lease_started.set()
        return lease


def test_close_interrupts_poll_wait_and_leaves_provider_task_resumable(
    repository,
    prepared_project,
):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example/v1"},
    )
    repository.start_media_task(task.id, provider="openai")
    repository.record_media_submission(
        task.id,
        provider="openai",
        provider_task_id="provider-task-long-poll",
    )
    broker = SignallingSecretBroker(image_api_key="server-image-key")
    gateway = ScriptedGateway([])
    runner = MediaJobRunner(
        repository,
        broker,
        gateway=gateway,
        poll_interval_seconds=30,
    )
    future = runner.submit(task.id)
    assert broker.lease_started.wait(timeout=2)

    started = time.monotonic()
    runner.close()
    elapsed = time.monotonic() - started
    result = future.result(timeout=1)

    assert elapsed < 2
    assert result.status == MediaTaskStatus.RUNNING
    assert result.provider_task_id == "provider-task-long-poll"
    assert result.finished_at is None
    assert gateway.submit_calls == []
    assert gateway.poll_calls == []
    assert task.id not in runner._futures


def test_missing_video_source_fails_without_calling_provider(repository, prepared_project):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.VIDEO,
        provider="atlascloud",
        public_settings={"videoBaseUrl": "https://api.example/v1"},
    )
    gateway = ScriptedGateway([])
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(video_api_key="video-key"),
        gateway=gateway,
        poll_interval_seconds=0,
    )
    try:
        result = runner.submit(task.id).result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.FAILED
    assert result.finished_at is not None
    assert "source image URL" in result.error
    assert gateway.submit_calls == []


def test_poll_failure_redacts_session_key_before_persisting_error(
    repository,
    prepared_project,
):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.VIDEO,
        provider="atlascloud",
        public_settings={
            "videoBaseUrl": "https://api.example/v1",
            "imageUrl": "https://cdn.example/keyframe.jpg",
        },
    )
    gateway = ScriptedGateway(
        [MediaSubmission("atlascloud", "provider-task-8", "processing")],
        [MediaPollResult("failed", error="credential video-session-key was rejected")],
    )
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(video_api_key="server-video-key"),
        gateway=gateway,
        poll_interval_seconds=0,
    )
    try:
        result = runner.submit(task.id, session_api_key="video-session-key").result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.FAILED
    assert result.provider_task_id == "provider-task-8"
    assert "video-session-key" not in result.error
    assert "[redacted]" in result.error
    assert "video-session-key" not in repository.get_media_task(task.id).model_dump_json()


def test_poll_limit_produces_terminal_failure(repository, prepared_project):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="atlascloud",
        public_settings={"imageBaseUrl": "https://api.example/v1"},
    )
    gateway = ScriptedGateway(
        [MediaSubmission("atlascloud", "provider-task-9", "processing")],
        [MediaPollResult("processing"), MediaPollResult("processing")],
    )
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(image_api_key="image-key"),
        gateway=gateway,
        poll_interval_seconds=0,
        max_poll_attempts=2,
    )
    try:
        result = runner.submit(task.id).result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.FAILED
    assert result.finished_at is not None
    assert "after 2 polls" in result.error


@pytest.mark.parametrize(
    ("provider", "public_settings"),
    [
        ("openai", {"nested": {"apiKey": "must-never-persist"}}),
        ("openai", {"model": "Bearer must-never-persist"}),
        ("openai", {"baseUrl": "https://user:password@example.test/v1"}),
        ("openai", {"baseUrl": "https://example.test/v1?access_token=secret"}),
        ("openai", {"baseUrl": "https://example.test/v1?signature=secret"}),
        ("openai", {"key": "must-never-persist"}),
        ("sk-must-never-persist", {}),
    ],
)
def test_repository_rejects_secret_material_in_media_configuration(
    repository,
    prepared_project,
    provider,
    public_settings,
):
    with pytest.raises(ValidationError):
        make_media_task(
            repository,
            prepared_project,
            MediaKind.IMAGE,
            provider=provider,
            public_settings=public_settings,
        )


class EchoingFailureGateway(ScriptedGateway):
    def submit(self, *, adapter, params, base_url, secret, auth_mode):
        assert secret is not None
        with secret.reveal() as api_key:
            raise MediaProviderError(f"provider echoed {api_key}")


def test_unexpected_gateway_error_is_terminal_and_secret_safe(repository, prepared_project):
    task = make_media_task(
        repository,
        prepared_project,
        MediaKind.IMAGE,
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example/v1"},
    )
    runner = MediaJobRunner(
        repository,
        MediaTaskSecretBroker(image_api_key="server-key"),
        gateway=EchoingFailureGateway([]),
        poll_interval_seconds=0,
    )
    try:
        result = runner.submit(task.id, session_api_key="session-secret").result(timeout=2)
    finally:
        runner.close()

    assert result.status == MediaTaskStatus.FAILED
    assert "session-secret" not in result.error
    assert "[redacted]" in result.error
