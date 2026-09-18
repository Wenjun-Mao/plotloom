"""Cross-process admission for explicitly open project folders.

The durable row says whether a folder may accept work. The adjacent advisory
lock protects the transition itself: normal handles retain a shared lease for
their lifetime, while close/reopen take an exclusive lease. A filesystem lock
is intentionally used in addition to SQLite because package publication writes
project files outside a database transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import stat
from typing import Literal

from ..domain import TERMINAL_MEDIA_TASK_STATUSES, TERMINAL_RUN_STATUSES
from .format import ProjectStorageConfinementError, ProjectStorageError


class ProjectClosedError(ProjectStorageError):
    """Raised when a delayed request targets an explicitly closed project."""


class ProjectBusyError(ProjectStorageError):
    """Raised when writers or nonterminal work prevent a safe transition."""


@dataclass
class ProjectAccessLease:
    """One OS-level project lease; release is idempotent for request cleanup."""

    descriptor: int
    mode: Literal["shared", "exclusive"]

    @classmethod
    def acquire(
        cls,
        project_home: Path,
        *,
        mode: Literal["shared", "exclusive"],
        create: bool = True,
    ) -> "ProjectAccessLease":
        lock_path = project_home / ".project-operation.lock"
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        if create:
            flags |= os.O_CREAT
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except FileNotFoundError:
            if not create and mode == "shared":
                # Restored CLOSED folders intentionally omit operational
                # debris. A read-only inspection must not recreate it.
                return cls(descriptor=-1, mode=mode)
            raise
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            os.close(descriptor)
            raise ProjectStorageConfinementError(
                "project operation lock must be one regular unlinked file"
            )
        operation = fcntl.LOCK_SH if mode == "shared" else fcntl.LOCK_EX
        try:
            fcntl.flock(descriptor, operation | fcntl.LOCK_NB)
        except BlockingIOError as error:
            os.close(descriptor)
            raise ProjectBusyError("project_busy: another local writer is active") from error
        return cls(descriptor=descriptor, mode=mode)

    def close(self) -> None:
        if self.descriptor < 0:
            return
        try:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        finally:
            os.close(self.descriptor)
            self.descriptor = -1


def close_blockers(store: object) -> list[str]:
    """Report durable work that cannot be copied or safely resumed by close."""

    repository = store.repository  # type: ignore[attr-defined]
    media = store.media  # type: ignore[attr-defined]
    project_id = store.manifest.project_id  # type: ignore[attr-defined]
    blockers: list[str] = []
    terminal_runs = tuple(item.value for item in TERMINAL_RUN_STATUSES)
    terminal_tasks = tuple(item.value for item in TERMINAL_MEDIA_TASK_STATUSES)
    with repository.engine.connect() as connection:
        active_run = connection.exec_driver_sql(
            "SELECT 1 FROM v2_generation_runs WHERE project_id = ? AND status NOT IN (?, ?, ?, ?) LIMIT 1",
            (project_id, *terminal_runs),
        ).first()
        active_task = connection.exec_driver_sql(
            "SELECT 1 FROM v2_media_tasks WHERE project_id = ? AND status NOT IN (?, ?, ?) LIMIT 1",
            (project_id, *terminal_tasks),
        ).first()
        active_video = connection.exec_driver_sql(
            "SELECT 1 FROM v2_video_jobs WHERE project_id = ? "
            "AND state NOT IN ('ingested', 'cancelled', 'failed') LIMIT 1",
            (project_id,),
        ).first()
    if active_run is not None:
        blockers.append("nonterminal_text_run")
    if active_task is not None:
        blockers.append("nonterminal_media_task")
    if active_video is not None:
        blockers.append("nonterminal_video_job")
    # Manual image and character-reference packages are filesystem publications.
    # Their exported/prepared states cannot prove the external specialist is idle,
    # so close fails closed until they become delivery/rejection terminal records.
    if any(job.get("state") not in {"delivered", "rejected", "cancelled"} for job in media.list_image_jobs(project_id)):
        blockers.append("image_publication_active")
    if any(proposal.get("state") not in {"delivered", "rejected", "cancelled"} for proposal in media.list_character_reference_proposals(project_id)):
        blockers.append("character_reference_publication_active")
    blockers.extend(source_outline_publication_blockers(store))
    blockers.extend(cast_publication_blockers(store))
    return blockers


def source_outline_publication_blockers(store: object) -> list[str]:
    """Prepared outline handoffs remain externally publishable until cancelled."""

    repository = store.repository  # type: ignore[attr-defined]
    project_id = store.manifest.project_id  # type: ignore[attr-defined]
    with repository.engine.connect() as connection:
        prepared = connection.exec_driver_sql(
            "SELECT 1 FROM v2_source_outline_candidates "
            "WHERE project_id = ? AND status = 'prepared' LIMIT 1",
            (project_id,),
        ).first()
    return ["source_outline_publication_active"] if prepared is not None else []

def cast_publication_blockers(store: object) -> list[str]:
    repository = store.repository  # type: ignore[attr-defined]
    project_id = store.manifest.project_id  # type: ignore[attr-defined]
    with repository.engine.connect() as connection:
        prepared = connection.exec_driver_sql("SELECT 1 FROM v2_cast_candidates WHERE project_id = ? AND status = 'prepared' LIMIT 1", (project_id,)).first()
    return ["cast_publication_active"] if prepared is not None else []
