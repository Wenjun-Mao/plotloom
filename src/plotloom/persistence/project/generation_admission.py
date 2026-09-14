"""Process-local admission state for one bound project generation surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy.orm import Session

from ...exceptions import InvalidTransitionError
from ..codec import stable_hash


class ProjectGenerationAdmission:
    """Own the narrow non-persistent admission state for a project repository.

    Provider-snapshot admission exists only while a caller is executing a
    project-bound pipeline. Recovery callbacks are installed by the project
    storage handle after it knows the project home. Neither concern belongs on
    the persistence composition root or in a general service container.
    """

    def __init__(self) -> None:
        self._admitted_provider_snapshot_hash: str | None = None
        self._recovered_run_ids: Callable[[], set[str]] = set
        self._recovery_operations_present: Callable[[], bool] = lambda: False

    @contextmanager
    def admit_provider_snapshot(self, provider_snapshot: Mapping[str, Any]) -> Iterator[None]:
        previous = self._admitted_provider_snapshot_hash
        self._admitted_provider_snapshot_hash = stable_hash(dict(provider_snapshot))
        try:
            yield
        finally:
            self._admitted_provider_snapshot_hash = previous

    def assert_new_run_profile_enabled(
        self, _session: Session, provider_snapshot: dict[str, Any]
    ) -> None:
        if self._admitted_provider_snapshot_hash != stable_hash(provider_snapshot):
            raise InvalidTransitionError(
                "project generation requires an application-admitted provider snapshot"
            )

    def set_recovery_admission(
        self,
        *,
        recovered_run_ids: Callable[[], set[str]],
        recovery_operations_present: Callable[[], bool],
    ) -> None:
        self._recovered_run_ids = recovered_run_ids
        self._recovery_operations_present = recovery_operations_present

    def run_requires_recovery(self, run_id: str) -> bool:
        return run_id in self._recovered_run_ids()

    def recovery_operations_are_present(self) -> bool:
        return self._recovery_operations_present()
