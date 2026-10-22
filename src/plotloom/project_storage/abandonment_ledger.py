"""Minimal deletion intent, outside the home being erased; never a content copy."""
import json
import os
import shutil
import stat
from pathlib import Path

from ..exceptions import InvalidTransitionError
from .format import PROJECT_MANIFEST_FILENAME, parse_project_manifest
from .operational_state import ProjectAccessLease


class ApplicationAbandonmentLedger:
    def __init__(self, application):
        self.application = application
        with application._write() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS application_project_abandonments (
                project_id TEXT PRIMARY KEY, home TEXT NOT NULL, device INTEGER NOT NULL,
                inode INTEGER NOT NULL, manifest_json TEXT NOT NULL, consent_json TEXT NOT NULL,
                revocation_json TEXT)""")

    def current(self, project_id):
        with self.application._read() as connection:
            row = connection.execute("SELECT * FROM application_project_abandonments WHERE project_id=?", (project_id,)).fetchone()
            return dict(row) if row else None

    def require_admitted(self, project_id):
        from .write_admission import reject_pending_deletion
        row = self.current(project_id)
        if row is not None and row["revocation_json"] is not None:
            reject_pending_deletion()

    def pending(self):
        with self.application._read() as connection:
            return [{"projectId": row["project_id"], **json.loads(row["consent_json"]),
                     "revoked": row["revocation_json"] is not None}
                for row in connection.execute("SELECT * FROM application_project_abandonments ORDER BY project_id")]

    def prepare(self, home, project_id, consent):
        metadata = home.path.stat()
        manifest_json = home.manifest.model_dump_json(by_alias=True)
        with self.application._write() as connection:
            row = connection.execute("SELECT * FROM application_project_abandonments WHERE project_id=?", (project_id,)).fetchone()
            if row is None:
                connection.execute("INSERT INTO application_project_abandonments VALUES (?,?,?,?,?,?,NULL)",
                    (project_id, str(home.path), metadata.st_dev, metadata.st_ino,
                     manifest_json, json.dumps(consent, ensure_ascii=False)))
                return
            if ((row["home"], row["device"], row["inode"]) != (str(home.path), metadata.st_dev, metadata.st_ino)
                    or parse_project_manifest(json.loads(row["manifest_json"])) != home.manifest):
                raise InvalidTransitionError("删除确认的原目录或清单身份已变化；不能改用替代目录。")
            if row["revocation_json"] is not None:
                if json.loads(row["consent_json"]) != consent:
                    raise InvalidTransitionError("已确认主机撤销的删除请求不可替换；请使用原请求重试。")
                return
            # The caller has revalidated this new, explicit consent against a
            # fresh server preview under the original project's exclusive lease.
            connection.execute("UPDATE application_project_abandonments SET consent_json=? WHERE project_id=? AND revocation_json IS NULL",
                (json.dumps(consent, ensure_ascii=False), project_id))

    def acknowledge(self, project_id, receipt):
        with self.application._write() as connection:
            connection.execute("UPDATE application_project_abandonments SET revocation_json=? WHERE project_id=? AND revocation_json IS NULL",
                (receipt.model_dump_json(by_alias=True), project_id))

    def finish(self, project_id):
        self.application.project_lifecycle.forget_project(project_id)
        with self.application._write() as connection:
            connection.execute("DELETE FROM application_project_abandonments WHERE project_id=?", (project_id,))


def resume_revoked_erasure(registry, ledger, row, consent):
    """A retained exact inode and revocation permit retry after manifest removal."""
    if json.loads(row["consent_json"]) != consent or row["revocation_json"] is None:
        raise InvalidTransitionError("删除重试必须匹配原确认及已记录的主机撤销回执。")
    from ..project_abandonment_contracts import AbandonmentPreview
    receipt = AbandonmentPreview.model_validate_json(row["revocation_json"])
    if not receipt.revoked or receipt.project_id != row["project_id"]:
        raise InvalidTransitionError("删除重试缺少精确主机撤销回执。")
    home = Path(row["home"])
    if home.is_symlink() or home.parent != registry.outputs_root.resolve():
        raise InvalidTransitionError("删除重试目录不再受当前存储根约束。")
    if not home.exists():
        ledger.finish(row["project_id"])
        return
    metadata = home.stat()
    if not home.is_dir() or (metadata.st_dev, metadata.st_ino) != (row["device"], row["inode"]):
        raise InvalidTransitionError("删除重试目录身份已变化；未删除任何替代目录。")
    lease = ProjectAccessLease.acquire(home, mode="exclusive")
    try:
        _erase_revoked_home(home, row, lease)
    finally:
        lease.close()
    ledger.finish(row["project_id"])


def _erase_revoked_home(home, row, lease):
    """Anchor every recursive deletion to the approved open directory inode."""
    if not shutil.rmtree.avoids_symlink_attacks or lease.mode != "exclusive" or lease.descriptor < 0:
        raise InvalidTransitionError("删除重试需要安全平台及精确项目的独占锁。")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(home.parent, flags)
    home_fd = -1
    try:
        home_fd = os.open(home.name, flags, dir_fd=parent_fd)
        approved = (row["device"], row["inode"])
        _assert_home_entry(parent_fd, home.name, approved)
        metadata = os.fstat(home_fd)
        if (metadata.st_dev, metadata.st_ino) != approved:
            raise InvalidTransitionError("删除重试目录身份已变化；未删除任何替代目录。")
        lock = os.stat(".project-operation.lock", dir_fd=home_fd, follow_symlinks=False)
        held = os.fstat(lease.descriptor)
        if (not stat.S_ISREG(lock.st_mode) or (lock.st_dev, lock.st_ino) != (held.st_dev, held.st_ino)):
            raise InvalidTransitionError("删除重试的目录锁已变化；未删除任何目录。")
        try:
            manifest_fd = os.open(PROJECT_MANIFEST_FILENAME, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=home_fd)
        except FileNotFoundError:
            pass
        else:
            with os.fdopen(manifest_fd, "r", encoding="utf-8") as source:
                original = parse_project_manifest(json.loads(row["manifest_json"]))
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode) or parse_project_manifest(json.load(source)) != original:
                    raise InvalidTransitionError("删除重试的项目清单身份已变化。")
            os.unlink(PROJECT_MANIFEST_FILENAME, dir_fd=home_fd)
        # Directory descriptors remain bound to the approved original even if
        # its pathname is moved. Never recurse through that pathname again.
        for name in os.listdir(home_fd):
            if name == ".project-operation.lock":
                continue
            _assert_home_entry(parent_fd, home.name, approved)
            entry = os.stat(name, dir_fd=home_fd, follow_symlinks=False)
            if stat.S_ISDIR(entry.st_mode):
                shutil.rmtree(name, dir_fd=home_fd)
            else:
                os.unlink(name, dir_fd=home_fd)
        _assert_home_entry(parent_fd, home.name, approved)
        os.unlink(".project-operation.lock", dir_fd=home_fd)
        os.rmdir(home.name, dir_fd=parent_fd)
    finally:
        if home_fd >= 0:
            os.close(home_fd)
        os.close(parent_fd)


def _assert_home_entry(parent_fd, name, approved):
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != approved:
        raise InvalidTransitionError("删除重试目录身份已变化；未删除任何替代目录。")
