from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, RLock
from typing import TYPE_CHECKING, Callable, Protocol

from .domain import GenerationRun, RunStatus
from .exceptions import (
    InvalidTransitionError,
    QuarantinedOutputError,
    RevisionConflictError,
    RunExecutionError,
    StagePrerequisiteError,
)
from .generation.aggregation import AggregateValidationError
from .generation.exceptions import SecretLeaseError
from .generation.planning import PlanningError
from .runtime import GenerationEngine, RunContext
from .validation import DomainValidationError

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )


class LifecycleJobRunner:
    """Small local-process runner with cooperative cancellation and durable states."""

    def __init__(
        self,
        repository: "GenerationRunRepository",
        engine: GenerationEngine,
        context: RunContext,
        *,
        max_workers: int = 2,
        secret_registrar: "RunSecretRegistrar | None" = None,
        completion_observer: Callable[[GenerationRun], None] | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine
        self.context = context
        self.secret_registrar = secret_registrar
        self._completion_observer = completion_observer
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="plotloom")
        self._cancellations: dict[str, Event] = {}
        self._futures: dict[str, Future[GenerationRun]] = {}
        self._lock = RLock()

    def submit(
        self,
        run_id: str,
        *,
        session_api_key: str | None = None,
    ) -> Future[GenerationRun]:
        with self._lock:
            existing = self._futures.get(run_id)
            if existing is not None:
                return existing
            run = self.repository.get_run(run_id)
            profile_id = str(
                run.provider_snapshot.get("profileId")
                or run.provider_snapshot.get("profile_id")
                or "default"
            )
            auth_mode = str(
                run.provider_snapshot.get("textAuthMode")
                or run.provider_snapshot.get("text_auth_mode")
                or "bearer"
            )
            if auth_mode == "bearer" and self.secret_registrar is not None:
                if not session_api_key and not self.secret_registrar.server_key_available(
                    profile_id
                ):
                    raise SecretLeaseError(
                        "queued generation requires its profile's browser-session key"
                    )
            if (
                auth_mode == "bearer"
                and session_api_key
                and self.secret_registrar is not None
            ):
                self.secret_registrar.register_run_override(
                    run_id,
                    session_api_key,
                    profile_id=profile_id,
                )
            cancellation = Event()
            self._cancellations[run_id] = cancellation
            future = self._executor.submit(self._execute, run_id, cancellation)
            self._futures[run_id] = future
            future.add_done_callback(
                lambda completed, resource_id=run_id: self._forget_future(
                    resource_id,
                    completed,
                )
            )
            return future

    def _forget_future(
        self,
        run_id: str,
        completed: Future[GenerationRun],
    ) -> None:
        with self._lock:
            if self._futures.get(run_id) is completed:
                self._futures.pop(run_id, None)
            observer = self._completion_observer
        if observer is None or completed.cancelled():
            return
        try:
            observer(completed.result())
        except Exception:
            # An observation is non-durable UI state and must never turn a
            # completed canonical run into a failed worker callback.
            return

    def set_completion_observer(
        self, observer: Callable[[GenerationRun], None] | None
    ) -> None:
        with self._lock:
            self._completion_observer = observer

    def request_cancel(self, run_id: str) -> GenerationRun:
        run = self.repository.cancel_run(run_id)
        with self._lock:
            event = self._cancellations.get(run_id)
            if event is not None:
                event.set()
        return run

    def _execute(self, run_id: str, cancellation: Event) -> GenerationRun:
        """Execute and always release run-scoped process state.

        Cancellation may win before ``start_run``.  Cleanup therefore wraps
        the transition itself rather than only the engine body.
        """

        try:
            return self._execute_run(run_id, cancellation)
        finally:
            if self.secret_registrar is not None:
                self.secret_registrar.release_run(run_id)
            with self._lock:
                self._cancellations.pop(run_id, None)

    def _execute_run(self, run_id: str, cancellation: Event) -> GenerationRun:
        try:
            run = self.repository.start_run(run_id)
        except InvalidTransitionError:
            run = self.repository.get_run(run_id)
            if run.status == RunStatus.CANCELLED:
                return run
            raise
        if run.status == RunStatus.CANCELLED:
            return run
        try:
            self.repository.assert_run_inputs_current(run_id)
            result = self.engine.execute(run, self.context, cancellation)
            if cancellation.is_set() or self.repository.get_run(run_id).status == RunStatus.CANCEL_REQUESTED:
                return self.repository.finish_run(run_id)
            if result.sealed_aggregate_ids:
                if result.stage_payloads:
                    raise ValueError(
                        "an execution result must use either sealed aggregates or legacy payloads, not both"
                    )
                # The durable runner must not receive or install an in-memory
                # payload dictionary.  The repository re-reads these immutable
                # seals and verifies their exact manifests in the commit
                # transaction.
                return self.repository.commit_sealed_run(
                    run_id,
                    sealed_aggregate_ids=result.sealed_aggregate_ids,
                )
            for artifact in result.artifacts:
                if artifact.run_id != run_id:
                    raise ValueError("engine artifact run_id does not match the executing run")
                self.repository.add_artifact(artifact)
            expected_stages = set(run.requested_stages)
            if set(result.stage_payloads) != expected_stages:
                return self.repository.finish_run(
                    run_id,
                    quarantine_reason="engine result must contain exactly one candidate for each requested stage",
                )
            if cancellation.is_set() or self.repository.get_run(run_id).status == RunStatus.CANCEL_REQUESTED:
                return self.repository.finish_run(run_id)
            return self.repository.commit_run_outputs(run_id, result.stage_payloads)
        except QuarantinedOutputError as error:
            for artifact in error.artifacts:
                if artifact.run_id != run_id:
                    raise ValueError("quarantine artifact run_id does not match the executing run")
                self.repository.add_artifact(artifact)
            return self.repository.finish_run(
                run_id,
                quarantine_reason=str(error),
                failure_code=error.code,
                failed_stage=error.stage,
            )
        except AggregateValidationError as error:
            return self.repository.finish_run(
                run_id,
                quarantine_reason=str(error),
                failure_code=error.code,
                failed_stage=error.stage,
            )
        except RunExecutionError as error:
            return self.repository.finish_run(
                run_id,
                error=str(error),
                failure_code=error.code,
                failed_stage=error.stage,
            )
        except (DomainValidationError, RevisionConflictError, StagePrerequisiteError) as error:
            return self.repository.finish_run(
                run_id,
                quarantine_reason=str(error),
                failure_code="validation.canonical_rejected",
                failed_stage=getattr(error, "stage", None),
            )
        except PlanningError as error:
            return self.repository.finish_run(
                run_id,
                error=str(error),
                failure_code=error.code,
                failed_stage=error.stage,
            )
        # This is the outer worker boundary: unknown engine/adapter failures must
        # become a durable failed run instead of escaping the executor thread.
        except Exception as error:  # noqa: BLE001
            current = self.repository.get_run(run_id)
            if current.status == RunStatus.CANCEL_REQUESTED:
                return self.repository.finish_run(run_id)
            return self.repository.finish_run(
                run_id,
                error=str(error),
                failure_code="run.internal_error",
            )
    def close(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=False)


class RunSecretRegistrar(Protocol):
    def server_key_available(self, profile_id: str = "default") -> bool: ...

    def register_run_override(
        self,
        run_id: str,
        value: str | None,
        *,
        profile_id: str = "default",
    ) -> None: ...

    def release_run(self, run_id: str) -> None: ...
