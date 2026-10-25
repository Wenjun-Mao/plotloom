"""Whole-home erasure at the project-owned storage boundary."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import shutil
import stat
from typing import TYPE_CHECKING

from ..exceptions import InvalidTransitionError, RevisionConflictError
from .format import (
    PROJECT_MANIFEST_FILENAME, ProjectManifest, ProjectStorageConfinementError,
    _read_json, parse_project_manifest,
)
from .operational_state import ProjectAccessLease, ProjectBusyError, close_blockers

if TYPE_CHECKING:
    from .project_handle import ProjectStore


def permanently_delete_home(
    store: ProjectStore,
    *,
    outputs_root: Path,
    expected_project_revision: int,
    expected_lifecycle_revision: int,
    confirmation_title: str,
    native_blockers: Callable[[ProjectStore], list[str]],
    scope_hash: str | None = None,
) -> None:
    """Admit one exact idle project, independently of Archive and Close."""
    try:
        project = store.project()
        if scope_hash is not None:
            from .deletion_preparation import deletion_scope
            if deletion_scope(store) != scope_hash:
                raise InvalidTransitionError("项目内容或任务范围已改变；未删除，请重新核对。")
        for owner, expected, actual in (
            ("project", expected_project_revision, project.revision),
            ("project-lifecycle", expected_lifecycle_revision, project.lifecycle_revision),
        ):
            if expected != actual:
                raise RevisionConflictError(owner, expected, actual)
        if not confirmation_title.strip() or confirmation_title != store.display_title():
            raise InvalidTransitionError("confirmation title does not match the project title")
        blockers = close_blockers(store) + native_blockers(store)
        with store.repository._read() as session:
            for run_id, state in session.connection().exec_driver_sql(
                "SELECT id,state FROM v2_autopilot_runs WHERE project_id=? AND state NOT IN ('cancelled','taken_over','stale','handed_off')", (store.manifest.project_id,)):
                blockers.append(f"自动任务 {run_id} 仍为 {state}；请明确停止后再删除。")
            if session.connection().exec_driver_sql(
                    "SELECT 1 FROM v2_autopilot_exec_attempts WHERE project_id=? LIMIT 1", (store.manifest.project_id,)).first():
                blockers.append("项目保留自动任务执行记录；请通过「删除项目…」核对原主机撤销与删除，不能绕过未知结果或本地进程检查。")
        if blockers:
            raise ProjectBusyError("project_busy: " + ", ".join(blockers))
        # Media records and their immutable bytes share this home. The row-only
        # persistence eraser cannot provide this filesystem ownership guarantee.
        store.remove_home(outputs_root=outputs_root)
    finally:
        store.close()


def remove_owned_home(
    home: Path,
    *,
    outputs_root: Path,
    manifest: ProjectManifest,
    lease: ProjectAccessLease | None,
    close_repository: Callable[[], None],
) -> None:
    """Erase only the manifest-bound direct child without following links."""
    if lease is None or lease.mode != "exclusive" or lease.descriptor < 0:
        raise ProjectStorageConfinementError("project deletion requires an exclusive project lease")
    if home.is_symlink() or not home.is_dir() or home.parent != outputs_root.resolve():
        raise ProjectStorageConfinementError("project deletion must target one real outputs-root child")
    manifest_path = home / PROJECT_MANIFEST_FILENAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProjectStorageConfinementError("project deletion requires its regular manifest")
    if parse_project_manifest(_read_json(manifest_path)) != manifest:
        raise ProjectStorageConfinementError("project deletion manifest changed after admission")
    lock_metadata = (home / ".project-operation.lock").lstat()
    held_metadata = os.fstat(lease.descriptor)
    if not stat.S_ISREG(lock_metadata.st_mode) or (
        lock_metadata.st_dev, lock_metadata.st_ino
    ) != (held_metadata.st_dev, held_metadata.st_ino):
        raise ProjectStorageConfinementError("project deletion lock changed after admission")
    if not shutil.rmtree.avoids_symlink_attacks:
        raise ProjectStorageConfinementError("safe project deletion is unsupported on this platform")
    close_repository()
    # Withdraw admission before recursive erasure can unlink the lock. Even
    # a late resolver cannot recreate a lease and reopen a half-erased home.
    manifest_path.unlink()
    shutil.rmtree(home)
