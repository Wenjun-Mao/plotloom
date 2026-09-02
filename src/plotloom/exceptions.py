from __future__ import annotations

from typing import TYPE_CHECKING

from .domain import StageName

if TYPE_CHECKING:
    from .domain import Artifact


class PlotloomError(Exception):
    """Base class for errors deliberately exposed by the Plotloom application layer."""


class NotFoundError(PlotloomError):
    pass


class RevisionConflictError(PlotloomError):
    def __init__(self, resource: str, expected_revision: int, actual_revision: int) -> None:
        self.resource = resource
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        super().__init__(
            f"{resource} revision conflict: expected {expected_revision}, current revision is {actual_revision}"
        )


class StagePrerequisiteError(PlotloomError):
    def __init__(self, stage: StageName, prerequisite: StageName, status: str) -> None:
        self.stage = stage
        self.prerequisite = prerequisite
        self.status = status
        super().__init__(f"{stage.value} requires {prerequisite.value} to be ready; current status is {status}")


class InvalidTransitionError(PlotloomError):
    pass


class IdempotencyConflictError(PlotloomError):
    """A creation key was already bound to a different aggregate request."""

    def __init__(self) -> None:
        super().__init__("Idempotency-Key has already been used for a different project creation request")


class BootstrapContentionError(PlotloomError):
    """Project creation could not acquire the bounded SQLite writer lease."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("project creation is temporarily busy; retry with the same Idempotency-Key")


class QuarantinedOutputError(PlotloomError):
    """A provider candidate failed validation and carries trace evidence."""

    def __init__(self, message: str, *, artifacts: list[Artifact]) -> None:
        super().__init__(message)
        self.artifacts = artifacts
