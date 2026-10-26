"""Bounded host history erasure; permanent revocation survives collection."""
import os
import shutil
import stat
from contextlib import closing, contextmanager
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_capacity_contracts import CapacityRetirementRequest
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.codex_exec_gc_contracts import (
    ProjectGarbageCollectionPreview,
    ProjectGarbageCollectionRequest,
)
from plotloom.persistence.codec import stable_hash

# All current attempt-owned child tables. Unknown future ownership refuses via FK.
_CHILD_TABLES = ("exec_queue", "exec_process_exits", "exec_recovery_evidence", "exec_capacity_retirements")


def _physical(path, *, directory):
    metadata = path.lstat()
    if path.resolve(strict=True) != path:
        raise CodexExecSupervisorError("garbage collection physical path was replaced or symlinked")
    if (metadata.st_uid != os.getuid()
            or (not stat.S_ISDIR(metadata.st_mode) if directory else
                not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1)):
        raise CodexExecSupervisorError("garbage collection physical path is unsafe")
    return (metadata.st_dev, metadata.st_ino, metadata.st_uid, metadata.st_mode)


@contextmanager
def _attempt_parent(path):
    """Anchor the only permitted evidence parent without following links."""
    root = path.parent.parent
    expected = _physical(root, directory=True)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        observed = os.fstat(root_fd)
        if (observed.st_dev, observed.st_ino, observed.st_uid, observed.st_mode) != expected:
            raise CodexExecSupervisorError("private evidence root changed")
        try:
            parent_fd = os.open("attempts", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        except FileNotFoundError:
            yield None
            return
        try:
            if os.fstat(parent_fd).st_uid != os.getuid():
                raise CodexExecSupervisorError("foreign private evidence parent")
            yield parent_fd
        finally:
            os.close(parent_fd)
    finally:
        os.close(root_fd)


def _entry_identity(metadata):
    # Reading evidence may update atime. Access time is observational; preserve
    # every ownership/content identity field, including subsecond change times.
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_nlink,
            metadata.st_uid, metadata.st_gid, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def _private_tree(path):
    """Hash exact private evidence; child links are inert, never followed."""
    facts = []
    def walk(descriptor, relative):
        metadata = os.fstat(descriptor)
        facts.append((relative, metadata.st_dev, metadata.st_ino, metadata.st_mode,
                      metadata.st_size, metadata.st_mtime_ns, None))
        for name in sorted(os.listdir(descriptor)):
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if metadata.st_uid != os.getuid():
                raise CodexExecSupervisorError("foreign private evidence owner")
            entry = name if relative == "." else f"{relative}/{name}"
            common = (entry, metadata.st_dev, metadata.st_ino, metadata.st_mode,
                      metadata.st_size, metadata.st_mtime_ns)
            if stat.S_ISLNK(metadata.st_mode):
                facts.append((*common, {"link": os.readlink(name, dir_fd=descriptor)}))
            elif stat.S_ISDIR(metadata.st_mode) or (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1):
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (
                    os.O_DIRECTORY if stat.S_ISDIR(metadata.st_mode) else 0), dir_fd=descriptor)
                try:
                    if _entry_identity(os.fstat(child)) != _entry_identity(metadata):
                        raise CodexExecSupervisorError("private evidence changed during preview")
                    if stat.S_ISDIR(metadata.st_mode):
                        walk(child, entry)
                    else:
                        digest = sha256()
                        with os.fdopen(child, "rb", closefd=False) as stream:
                            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                digest.update(chunk)
                        if _entry_identity(os.fstat(child)) != _entry_identity(metadata):
                            raise CodexExecSupervisorError("private evidence changed during preview")
                        facts.append((*common, digest.hexdigest()))
                finally:
                    os.close(child)
            else:
                raise CodexExecSupervisorError("private evidence contains a hardlink or special file")
    with _attempt_parent(path) as parent:
        if parent is None:
            return None
        try:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        except FileNotFoundError:
            return None
        try:
            if os.fstat(descriptor).st_uid != os.getuid():
                raise CodexExecSupervisorError("foreign private evidence owner")
            walk(descriptor, ".")
        finally:
            os.close(descriptor)
    return facts


def _erase_private_tree(path):
    if not shutil.rmtree.avoids_symlink_attacks:
        raise CodexExecSupervisorError("garbage collection requires symlink-safe directory erasure")
    with _attempt_parent(path) as parent:
        if parent is not None:
            shutil.rmtree(path.name, dir_fd=parent)


class CodexExecSupervisorGarbageCollectionMixin:
    def _project_gc_context(self, connection, request):
        project_id = str(request.project_id)
        if self._namespace is not None:
            raise CodexExecSupervisorError("project garbage collection requires an ordinary installation")
        revocation = connection.execute("SELECT * FROM exec_project_revocations WHERE project_id=?", (project_id,)).fetchone()
        if revocation is None:
            raise CodexExecSupervisorError("garbage collection requires permanent project revocation")
        home = Path(revocation["project_home"])
        if not home.is_absolute() or home.parent != self.outputs_root or home.name in {"", ".", ".."}:
            raise CodexExecSupervisorError("revoked home is not an exact confined outputs child")
        if not self._retired_home_absent(home):
            raise CodexExecSupervisorError("revoked project home exists, was replaced or is a symlink")
        # A renamed/restored home with the same manifest is still a current project.
        from plotloom.project_storage.format import ProjectStorageError
        from plotloom.project_storage.project_home import find_project_home
        try:
            find_project_home(self.outputs_root, project_id)
        except ProjectStorageError as error:
            if str(error) != f"project not found in outputs root: {project_id}":
                raise
        else:
            raise CodexExecSupervisorError("revoked project is still present in outputs")
        roots = {"outputs": _physical(self.outputs_root, directory=True),
                 "private": _physical(self.private_root, directory=True),
                 "database": _physical(self.database, directory=False)}
        parent = self.private_root / "attempts"
        roots["attempts"] = _physical(parent, directory=True) if parent.exists() or parent.is_symlink() else None
        blockers, facts, paths, ids, count, links = [], [], [], [], 0, 0
        rows = connection.execute("SELECT * FROM exec_attempts WHERE project_id=? ORDER BY attempt_id", (project_id,)).fetchall()
        for row in rows:
            attempt_id = str(UUID(row["attempt_id"]))
            original = CodexExecAttempt.model_validate_json(row["attempt_json"])
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            if (self._identity(original) != self._identity(current) or str(original.project_id) != project_id
                    or str(original.attempt_id) != attempt_id or row["project_home"] != str(home)):
                raise CodexExecSupervisorError("garbage collection immutable project identity differs")
            path = parent / attempt_id
            if row["private_dir"] != str(path):
                raise CodexExecSupervisorError("foreign private evidence path")
            if connection.execute("SELECT 1 FROM exec_slot WHERE attempt_id=?", (attempt_id,)).fetchone():
                blockers.append(f"{attempt_id}: capacity slot remains")
            if connection.execute("SELECT 1 FROM exec_validation_process WHERE attempt_id=?", (attempt_id,)).fetchone():
                blockers.append(f"{attempt_id}: validator remains")
            child = {table: [dict(item) for item in connection.execute(
                f"SELECT * FROM {table} WHERE attempt_id=?", (attempt_id,))] for table in (*_CHILD_TABLES, "exec_slot", "exec_validation_process")}
            if any(item["enabled"] for item in child["exec_queue"]):
                blockers.append(f"{attempt_id}: enabled queue remains")
            worker = self._workers.get(attempt_id)
            if worker is not None and worker.poll() is None:
                blockers.append(f"{attempt_id}: active local worker remains")
            if current.state == "outcome_unknown":
                # Reuse immutable historical local retirement; never probe old PIDs.
                if not child["exec_capacity_retirements"]:
                    blockers.append(f"{attempt_id}: UNKNOWN lacks prior local capacity retirement")
                else:
                    self._capacity_retirement_context(connection, CapacityRetirementRequest(
                        project_id=request.project_id, attempt_id=attempt_id))
            elif current.state == "queued":
                if any(value is not None for value in (row["worker_pid"], row["worker_group_id"],
                        row["worker_birth_identity"], current.process_id, current.process_group_id,
                        current.process_birth_identity)) or not child["exec_queue"]:
                    blockers.append(f"{attempt_id}: queued launch ownership is unresolved")
            elif current.state not in {"completed", "failed", "settled"}:
                blockers.append(f"{attempt_id}: active execution state {current.state}")
            try:
                tree = _private_tree(path)
            except OSError as error:
                raise CodexExecSupervisorError("private evidence path is unsafe or changed") from error
            count += sum(isinstance(item[-1], str) for item in tree or [])
            links += sum(isinstance(item[-1], dict) for item in tree or [])
            facts.append({"attempt": dict(row), "children": child, "privateTree": tree})
            paths.append((path, tree))
            ids.append(attempt_id)
        digest = stable_hash({"projectId": project_id, "home": str(home), "roots": roots,
                              "revocation": dict(revocation), "attempts": facts})
        return ProjectGarbageCollectionPreview(project_id=request.project_id, preview_hash=digest,
            eligible=not blockers, blockers=blockers, attempt_ids=ids, private_file_count=count, private_symlink_count=links), paths

    def project_gc_preview(self, raw_request):
        request = ProjectGarbageCollectionRequest.model_validate(raw_request)
        with self._guard, self._abandonment_fence(request.project_id), closing(self._connect()) as connection:
            connection.execute("BEGIN")
            context, _paths = self._project_gc_context(connection, request)
            return context

    def collect_deleted_project(self, raw_request):
        request = ProjectGarbageCollectionRequest.model_validate(raw_request)
        if request.expected_preview_hash is None:
            raise CodexExecSupervisorError("garbage collection requires explicit current preview consent")
        with self._guard, self._abandonment_fence(request.project_id), closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                context, paths = self._project_gc_context(connection, request)
                if context.preview_hash != request.expected_preview_hash:
                    raise CodexExecSupervisorError("garbage collection preview changed; inspect again")
                if not context.eligible:
                    raise CodexExecSupervisorError("; ".join(context.blockers))
                # Resolve all FK ownership before erasing files. These deletes
                # remain uncommitted until the filesystem work succeeds.
                for attempt_id in context.attempt_ids:
                    for table in _CHILD_TABLES:
                        connection.execute(f"DELETE FROM {table} WHERE attempt_id=?", (str(attempt_id),))
                    connection.execute("DELETE FROM exec_attempts WHERE attempt_id=? AND project_id=?",
                        (str(attempt_id), str(request.project_id)))
                # No archive: interruption rolls rows back; a fresh preview
                # binds the remaining files before a deliberate retry.
                for path, tree in paths:
                    if _private_tree(path) != tree:
                        raise CodexExecSupervisorError("private evidence changed; inspect again")
                    if tree is not None:
                        _erase_private_tree(path)
                connection.commit()
                return context.model_copy(update={"applied": True})
            except BaseException:
                connection.rollback()
                raise
