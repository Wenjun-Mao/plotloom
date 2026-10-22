"""Installation deletion quarantine at project-owned admission boundaries."""
import sqlite3
from contextlib import closing
from pathlib import Path

from .format import ProjectStorageConfinementError
from .operational_state import ProjectAccessLease, ProjectBusyError


class ProjectDeletionPendingError(ProjectBusyError):
    """Acknowledged destruction cannot admit new work or reopen authority."""


def reject_pending_deletion():
    raise ProjectDeletionPendingError("project_deletion_pending: 主机发布权限已撤销；项目处于待完成删除隔离，不能编辑、重开或派发。请从待完成删除明确重试。")


def require_no_acknowledged_deletion(application_root: Path, project_id: str):
    database = application_root / "application.sqlite3"
    if database.is_symlink():
        raise ProjectStorageConfinementError("application deletion ledger must not be a symlink")
    if not database.exists():
        return
    with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        # Operator upgrades can precede first initialization of this installation
        # feature. No table means no deletion intent ever recorded here.
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='application_project_abandonments'").fetchone():
            return
        pending = connection.execute("SELECT 1 FROM application_project_abandonments WHERE project_id=? AND revocation_json IS NOT NULL", (project_id,)).fetchone()
    if pending:
        reject_pending_deletion()


class ProjectWriteAdmission:
    def __init__(self, require_admitted=None):
        self.require_admitted = require_admitted or (lambda _project_id: None)

    def lease(self, home, project_id, *, mode):
        lease = ProjectAccessLease.acquire(home, mode=mode)
        try:
            # The predicate must follow acquisition: an exclusive deletion may
            # have committed its ACK after this caller first resolved the home.
            self.require_admitted(project_id)
            return lease
        except BaseException:
            lease.close()
            raise
