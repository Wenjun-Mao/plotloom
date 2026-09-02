"""Execute compiled Plotloom media tasks without persisting provider credentials.

The API compiles and snapshots the media prompt before enqueueing a task. This
module owns the remaining lifecycle: resolve the snapshotted public provider
configuration, borrow an ephemeral credential, submit, poll when necessary,
and persist a terminal result.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, RLock
from typing import Callable, Protocol

from .domain import (
    TERMINAL_MEDIA_TASK_STATUSES,
    MediaKind,
    MediaTask,
    MediaTaskStatus,
)
from .exceptions import InvalidTransitionError
from .generation.exceptions import SecretLeaseError
from .generation.secrets import InMemorySecretVault, SecretLease
from .media import (
    MediaGateway,
    MediaPollResult,
    MediaProviderAdapter,
    MediaProviderError,
    MediaSubmission,
    get_media_adapter,
)
from .persistence import SQLiteRepository


class MediaGatewayPort(Protocol):
    def submit(
        self,
        *,
        adapter: MediaProviderAdapter,
        params: dict[str, object],
        base_url: str,
        secret: SecretLease,
    ) -> MediaSubmission: ...

    def poll(
        self,
        *,
        adapter: MediaProviderAdapter,
        provider_task_id: str,
        base_url: str,
        secret: SecretLease,
    ) -> MediaPollResult: ...


class MissingMediaCredentialError(RuntimeError):
    pass


class MediaTaskSecretBroker:
    """Process-local server keys plus per-task session overrides.

    Only opaque aliases are retained outside ``InMemorySecretVault``. A task
    override is removed as soon as the worker reaches a terminal state. The
    server key stays available until the runner is closed.
    """

    def __init__(
        self,
        *,
        image_api_key: str | None = None,
        video_api_key: str | None = None,
        lease_ttl_seconds: float = 3600.0,
        vault: InMemorySecretVault | None = None,
    ) -> None:
        if lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be greater than zero")
        self._vault = vault or InMemorySecretVault()
        self._lease_ttl_seconds = lease_ttl_seconds
        self._lock = RLock()
        self._task_aliases: dict[str, str] = {}
        self._server_aliases: dict[MediaKind, str] = {}
        self._put_server_key(MediaKind.IMAGE, image_api_key)
        self._put_server_key(MediaKind.VIDEO, video_api_key)

    def _put_server_key(self, kind: MediaKind, value: str | None) -> None:
        normalized = value.strip() if value else ""
        if not normalized:
            return
        alias = f"media:server:{kind.value}"
        self._vault.put(alias, normalized)
        self._server_aliases[kind] = alias

    def register_task_override(self, task_id: str, value: str | None) -> None:
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("task_id must not be blank")
        normalized = value.strip() if value else ""
        with self._lock:
            previous = self._task_aliases.pop(task_id, None)
            if previous is not None:
                self._vault.remove(previous)
            if normalized:
                alias = f"media:task:{task_id}"
                self._vault.put(alias, normalized)
                self._task_aliases[task_id] = alias

    def lease(self, task_id: str, kind: MediaKind) -> SecretLease:
        with self._lock:
            alias = self._task_aliases.get(task_id) or self._server_aliases.get(kind)
            if alias is None:
                raise MissingMediaCredentialError(
                    f"No {kind.value} API key is available for this media task"
                )
            return self._vault.lease(alias, ttl_seconds=self._lease_ttl_seconds)

    def redact(self, task_id: str, kind: MediaKind, message: str) -> str:
        """Remove known task/server credentials before durable error storage."""

        redacted = message
        with self._lock:
            aliases = tuple(
                alias
                for alias in (self._task_aliases.get(task_id), self._server_aliases.get(kind))
                if alias is not None
            )
        for alias in aliases:
            try:
                lease = self._vault.lease(alias, ttl_seconds=5.0, max_uses=1)
                with lease.reveal() as value:
                    redacted = redacted.replace(value, "[redacted]")
            except SecretLeaseError:
                continue
        return redacted

    def release_task_override(self, task_id: str) -> None:
        with self._lock:
            alias = self._task_aliases.pop(task_id, None)
            if alias is not None:
                self._vault.remove(alias)

    def clear(self) -> None:
        with self._lock:
            self._task_aliases.clear()
            self._server_aliases.clear()
            self._vault.clear()


AdapterResolver = Callable[[str, str | None], MediaProviderAdapter]


class MediaJobRunner:
    """Bounded local worker for synchronous and asynchronous media providers."""

    def __init__(
        self,
        repository: SQLiteRepository,
        secret_broker: MediaTaskSecretBroker,
        *,
        gateway: MediaGatewayPort | None = None,
        adapter_resolver: AdapterResolver = get_media_adapter,
        max_workers: int = 2,
        poll_interval_seconds: float = 2.0,
        max_poll_attempts: int = 300,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least one")
        if poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds must not be negative")
        if max_poll_attempts < 1:
            raise ValueError("max_poll_attempts must be at least one")
        self.repository = repository
        self.secret_broker = secret_broker
        self.gateway = gateway or MediaGateway()
        self.adapter_resolver = adapter_resolver
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_attempts = max_poll_attempts
        self.sleeper = sleeper
        self._shutdown = Event()
        self._clear_secrets_when_idle = False
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="plotloom-media",
        )
        self._futures: dict[str, Future[MediaTask]] = {}
        self._lock = RLock()

    def submit(
        self,
        task_id: str,
        *,
        session_api_key: str | None = None,
    ) -> Future[MediaTask]:
        with self._lock:
            existing = self._futures.get(task_id)
            if existing is not None:
                return existing
            registered_override = False
            if session_api_key:
                self.secret_broker.register_task_override(task_id, session_api_key)
                registered_override = True
            try:
                future = self._executor.submit(self._execute, task_id)
            except Exception:
                if registered_override:
                    self.secret_broker.release_task_override(task_id)
                raise
            self._futures[task_id] = future
            future.add_done_callback(
                lambda completed, resource_id=task_id: self._forget_future(
                    resource_id,
                    completed,
                )
            )
            return future

    def _forget_future(
        self,
        task_id: str,
        completed: Future[MediaTask],
    ) -> None:
        clear_secrets = False
        with self._lock:
            if self._futures.get(task_id) is completed:
                self._futures.pop(task_id, None)
            if self._clear_secrets_when_idle and not self._futures:
                self._clear_secrets_when_idle = False
                clear_secrets = True
        if clear_secrets:
            self.secret_broker.clear()

    def _execute(self, task_id: str) -> MediaTask:
        try:
            return self._execute_task(task_id)
        finally:
            self.secret_broker.release_task_override(task_id)

    def _execute_task(self, task_id: str) -> MediaTask:
        task = self.repository.get_media_task(task_id)
        if self._shutdown.is_set():
            return task
        provider_name = _provider_name(task)
        if task.status in TERMINAL_MEDIA_TASK_STATUSES:
            return task
        if task.status == MediaTaskStatus.QUEUED:
            task = self.repository.start_media_task(task_id, provider=provider_name)
        elif task.status == MediaTaskStatus.RUNNING and not task.provider_task_id:
            return self._fail(
                task,
                "Media submission state is uncertain because no provider task ID was persisted; "
                "the task was not resubmitted to avoid duplicate billing",
            )
        elif task.status != MediaTaskStatus.RUNNING:
            raise InvalidTransitionError(f"cannot execute media task from {task.status.value}")

        try:
            adapter = self.adapter_resolver(task.kind.value, provider_name)
            base_url = _base_url(task, adapter)
            secret = self.secret_broker.lease(task.id, task.kind)
            if task.provider_task_id:
                return self._poll(
                    task,
                    adapter,
                    task.provider_task_id,
                    base_url,
                    secret,
                )
            params = _provider_params(task, adapter)
            submission = self.gateway.submit(
                adapter=adapter,
                params=params,
                base_url=base_url,
                secret=secret,
            )
            self.repository.record_media_submission(
                task.id,
                provider=adapter.name,
                provider_task_id=submission.provider_task_id,
            )
            if submission.status == "succeeded":
                return self._succeed(task.id, submission.outputs)
            if submission.status == "failed":
                return self._fail(task, "Media provider rejected the submitted task")
            if not submission.provider_task_id:
                return self._fail(task, "Asynchronous media provider returned no task ID")
            return self._poll(task, adapter, submission.provider_task_id, base_url, secret)
        except Exception as error:  # noqa: BLE001 - durable worker boundary
            return self._fail(task, _error_message(error))

    def _poll(
        self,
        task: MediaTask,
        adapter: MediaProviderAdapter,
        provider_task_id: str,
        base_url: str,
        secret: SecretLease,
    ) -> MediaTask:
        for _attempt in range(self.max_poll_attempts):
            if self._wait_for_poll():
                return self.repository.get_media_task(task.id)
            result = self.gateway.poll(
                adapter=adapter,
                provider_task_id=provider_task_id,
                base_url=base_url,
                secret=secret,
            )
            if self._shutdown.is_set():
                return self.repository.get_media_task(task.id)
            if result.status == "succeeded":
                return self._succeed(task.id, result.outputs)
            if result.status == "failed":
                return self._fail(task, result.error or "Media provider task failed")
        return self._fail(
            task,
            f"Media provider task did not finish after {self.max_poll_attempts} polls",
        )

    def _wait_for_poll(self) -> bool:
        if self._shutdown.is_set():
            return True
        if not self.poll_interval_seconds:
            return False
        if self.sleeper is None:
            return self._shutdown.wait(self.poll_interval_seconds)
        self.sleeper(self.poll_interval_seconds)
        return self._shutdown.is_set()

    def _succeed(self, task_id: str, outputs: tuple[str, ...]) -> MediaTask:
        output_uri = next((value.strip() for value in outputs if value.strip()), None)
        if output_uri is None:
            task = self.repository.get_media_task(task_id)
            return self._fail(task, "Media provider reported success without an output URI")
        return self.repository.finish_media_task(
            task_id,
            MediaTaskStatus.SUCCEEDED,
            output_uri=output_uri,
        )

    def _fail(self, task: MediaTask, message: str) -> MediaTask:
        current = self.repository.get_media_task(task.id)
        if current.status in TERMINAL_MEDIA_TASK_STATUSES:
            return current
        safe_message = self.secret_broker.redact(task.id, task.kind, message).strip()
        if not safe_message:
            safe_message = "Media task failed"
        return self.repository.finish_media_task(
            task.id,
            MediaTaskStatus.FAILED,
            error=safe_message[:2000],
        )

    def close(self, *, wait: bool = True, clear_secrets: bool = True) -> None:
        self._shutdown.set()
        self._executor.shutdown(wait=wait, cancel_futures=False)
        if not clear_secrets:
            return
        if wait:
            self.secret_broker.clear()
            return
        with self._lock:
            if self._futures:
                self._clear_secrets_when_idle = True
                return
        self.secret_broker.clear()


def _provider_name(task: MediaTask) -> str:
    settings = task.public_settings
    value = task.provider or _setting(
        settings,
        f"{task.kind.value}_provider",
        f"{task.kind.value}Provider",
        "provider",
    )
    return str(value or "atlascloud").strip().lower()


def _base_url(task: MediaTask, adapter: MediaProviderAdapter) -> str:
    value = _setting(
        task.public_settings,
        f"{task.kind.value}_base_url",
        f"{task.kind.value}BaseUrl",
        "base_url",
        "baseUrl",
    )
    return str(value or adapter.default_base_url).strip()


def _provider_params(task: MediaTask, adapter: MediaProviderAdapter) -> dict[str, object]:
    settings = task.public_settings
    params: dict[str, object] = {
        "prompt": task.derived_prompt,
        "model": _setting(
            settings,
            f"{task.kind.value}_model",
            f"{task.kind.value}Model",
            "model",
        )
        or adapter.default_model,
    }
    aliases = {
        "size": ("size",),
        "quality": ("quality",),
        "moderation": ("moderation",),
        "output_format": ("output_format", "outputFormat"),
        "edit_model": ("edit_model", "editModel"),
        "reference_images": ("reference_images", "referenceImages"),
        "resolution": ("resolution",),
        "aspect_ratio": ("aspect_ratio", "aspectRatio"),
        "duration": ("duration", "duration_seconds", "durationSeconds"),
    }
    for canonical_name, names in aliases.items():
        value = _setting(settings, *names)
        if value is not None:
            params[canonical_name] = value

    if "aspect_ratio" not in params:
        constraints = task.prompt_components.get("mediaConstraints")
        if isinstance(constraints, dict) and constraints.get("aspectRatio"):
            params["aspect_ratio"] = constraints["aspectRatio"]
    if "duration" not in params:
        constraints = task.prompt_components.get("mediaConstraints")
        if isinstance(constraints, dict) and constraints.get("durationSeconds") is not None:
            params["duration"] = constraints["durationSeconds"]

    if task.kind == MediaKind.VIDEO:
        image_url = _setting(
            settings,
            "image_url",
            "imageUrl",
            "source_uri",
            "sourceUri",
            "start_frame_uri",
            "startFrameUri",
        )
        if not isinstance(image_url, str) or not image_url.strip():
            raise MediaProviderError(
                "Video generation requires a source image URL in publicSettings",
                status=400,
            )
        params["image_url"] = image_url.strip()
    return params


def _setting(settings: dict[str, object], *names: str) -> object | None:
    for name in names:
        value = settings.get(name)
        if value is not None and value != "":
            return value
    return None


def _error_message(error: Exception) -> str:
    message = str(error).strip()
    return f"{type(error).__name__}: {message}" if message else type(error).__name__
