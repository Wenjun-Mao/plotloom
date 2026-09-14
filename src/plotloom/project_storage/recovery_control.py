"""Project-owned control for work interrupted at a portable recovery boundary.

The database remains a byte-for-byte recovery payload.  A snapshot therefore
records its recovery admission separately instead of rewriting historical runs
or attempts during restore.  The control never contains credentials and can
only acknowledge a restored interruption; it cannot submit, reconcile, or
otherwise change the historical operation.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import Field

from ..domain import CamelModel
from .format import (
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    _canonical_json,
    _read_json,
    _write_new_file,
)
from .snapshot_files import _safe_regular


RECOVERY_CONTROL_FILENAME = "recovery.json"
RECOVERY_CONTROL_FORMAT_VERSION = 1


class RecoveryOperation(CamelModel):
    """One historical operation that must not be resumed by recovery."""

    kind: Literal["generation_run", "media_task"]
    operation_id: str = Field(min_length=1)
    provider_state: Literal["not_submitted", "known", "unknown"]


class ProjectRecoveryControl(CamelModel):
    """Portable admission state for operations left unfinished at capture."""

    recovery_control_format_version: Literal[RECOVERY_CONTROL_FORMAT_VERSION] = (
        RECOVERY_CONTROL_FORMAT_VERSION
    )
    project_id: str = Field(min_length=1)
    state: Literal["clear", "recovery_required", "acknowledged"]
    operations: list[RecoveryOperation]


def _connection(path: Path) -> sqlite3.Connection:
    _safe_regular(path, label="project database")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA query_only=ON")
    return connection


def capture_recovery_control(database: Path, project_id: str) -> ProjectRecoveryControl:
    """Describe nonterminal work without changing its durable evidence."""

    connection = _connection(database)
    try:
        runs = list(
            connection.execute(
                "SELECT id FROM v2_generation_runs "
                "WHERE project_id = ? AND status IN ('queued', 'running', 'cancel_requested') "
                "ORDER BY created_at, id",
                (project_id,),
            )
        )
        media_tasks = list(
            connection.execute(
                "SELECT id, provider_task_id, status FROM v2_media_tasks "
                "WHERE project_id = ? AND status IN ('queued', 'running') "
                "ORDER BY created_at, id",
                (project_id,),
            )
        )
        operations: list[RecoveryOperation] = []
        for (run_id,) in runs:
            attempts = list(
                connection.execute(
                    "SELECT dispatched_at, provider_request_id FROM v2_generation_attempts "
                    "WHERE run_id = ? ORDER BY attempt_number",
                    (run_id,),
                )
            )
            if any(request_id for _dispatched_at, request_id in attempts):
                provider_state = "known"
            elif any(dispatched_at is not None for dispatched_at, _request_id in attempts):
                provider_state = "unknown"
            else:
                provider_state = "not_submitted"
            operations.append(
                RecoveryOperation(
                    kind="generation_run",
                    operation_id=str(run_id),
                    provider_state=provider_state,
                )
            )
        for task_id, provider_task_id, status in media_tasks:
            operations.append(
                RecoveryOperation(
                    kind="media_task",
                    operation_id=str(task_id),
                    provider_state=(
                        "known"
                        if provider_task_id
                        else "not_submitted" if status == "queued" else "unknown"
                    ),
                )
            )
    except sqlite3.Error as error:
        raise ProjectStorageCorruptionError(
            "project database cannot describe unfinished recovery work"
        ) from error
    finally:
        connection.close()
    return ProjectRecoveryControl(
        project_id=project_id,
        state="recovery_required" if operations else "clear",
        operations=operations,
    )


def read_recovery_control(
    root: Path, project_id: str, *, required: bool = False
) -> ProjectRecoveryControl | None:
    """Read a confined recovery-control record without treating it as config."""

    path = root / RECOVERY_CONTROL_FILENAME
    if path.is_symlink():
        raise ProjectStorageConfinementError("recovery control must not be a symlink")
    if not path.exists():
        if required:
            raise ProjectStorageCorruptionError("snapshot has no recovery control")
        return None
    _safe_regular(path, label="recovery control")
    try:
        control = ProjectRecoveryControl.model_validate(_read_json(path))
    except ValueError as error:
        raise ProjectStorageCorruptionError("recovery control is unsupported") from error
    if control.project_id != project_id:
        raise ProjectStorageCorruptionError(
            "recovery control identity does not match the project"
        )
    return control


def validate_recovery_control(
    root: Path,
    database: Path,
    project_id: str,
    *,
    required: bool,
    snapshot: bool,
) -> ProjectRecoveryControl | None:
    """Bind a control record to exact unfinished database state."""

    control = read_recovery_control(root, project_id, required=required)
    if control is None:
        return None
    expected = capture_recovery_control(database, project_id)
    if control.operations != expected.operations:
        raise ProjectStorageCorruptionError(
            "recovery control does not match unfinished project operations"
        )
    allowed_states = (
        {expected.state}
        if snapshot or expected.state == "clear"
        else {"recovery_required", "acknowledged"}
    )
    if control.state not in allowed_states:
        raise ProjectStorageCorruptionError(
            "recovery control has an invalid admission state"
        )
    return control


def write_snapshot_recovery_control(root: Path, control: ProjectRecoveryControl) -> None:
    """Write the immutable control payload while a snapshot is private."""

    _write_new_file(
        root / RECOVERY_CONTROL_FILENAME,
        (_canonical_json(control.model_dump(mode="json", by_alias=True)) + "\n").encode(
            "utf-8"
        ),
    )


def acknowledge_recovery_control(root: Path, project_id: str) -> ProjectRecoveryControl:
    """Acknowledge recovery without replaying or changing historical work."""

    control = read_recovery_control(root, project_id, required=True)
    assert control is not None
    if control.state == "clear":
        return control
    acknowledged = control.model_copy(update={"state": "acknowledged"})
    target = root / RECOVERY_CONTROL_FILENAME
    temporary = root / f".{RECOVERY_CONTROL_FILENAME}-{uuid4().hex}.tmp"
    _write_new_file(
        temporary,
        (_canonical_json(acknowledged.model_dump(mode="json", by_alias=True)) + "\n").encode(
            "utf-8"
        ),
    )
    try:
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return acknowledged


def recovery_is_required(root: Path, project_id: str) -> bool:
    control = read_recovery_control(root, project_id)
    return control is not None and control.state == "recovery_required"


def recovered_generation_run_ids(root: Path, project_id: str) -> set[str]:
    """Return historic runs which can never be restarted by this boundary."""

    control = read_recovery_control(root, project_id)
    if control is None:
        return set()
    return {
        operation.operation_id
        for operation in control.operations
        if operation.kind == "generation_run"
    }


def recovery_operations_present(root: Path, project_id: str) -> bool:
    control = read_recovery_control(root, project_id)
    return control is not None and bool(control.operations)
