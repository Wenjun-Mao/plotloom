"""Project revocation without inventing terminal remote outcomes."""
import fcntl
import os
import stat
import time
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import UUID

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.persistence.codec import stable_hash
from plotloom.project_abandonment_contracts import AbandonmentPacket, AbandonmentPreview


class CodexExecSupervisorAbandonmentMixin:
    @contextmanager
    def _abandonment_fence(self, project_id):
        descriptor = os.open(self.private_root / f".project-{UUID(str(project_id))}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise CodexExecSupervisorError("unsafe project publication fence")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise CodexExecSupervisorError("host publication or admission is in progress; retry after it finishes") from error
            yield
        finally:
            os.close(descriptor)

    def _publication_revoked(self, project_id):
        with closing(self._connect()) as connection:
            return connection.execute("SELECT 1 FROM exec_project_revocations WHERE project_id=?", (str(project_id),)).fetchone() is not None

    @staticmethod
    def _assert_project_publication(connection, project_id):
        if connection.execute("SELECT 1 FROM exec_project_revocations WHERE project_id=?", (str(project_id),)).fetchone():
            raise CodexExecSupervisorError("project dispatch and publication were explicitly revoked")

    def _prove_group_absent(self, pid, group, birth):
        if pid is None or group is None or not birth:
            return False
        # ESRCH for the whole group is positive absence. Permission failures,
        # reused leaders and unknown identities never establish quiescence.
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except OSError:
                return False
        except OSError:
            return False
        return False

    def _abandonment_context(self, connection, packet):
        project_id = str(packet.project_id)
        home = Path(packet.project_home)
        if home.is_symlink() or not home.is_dir() or home.parent.resolve() != self.outputs_root.resolve():
            raise CodexExecSupervisorError("abandonment requires one confined existing project home")
        from plotloom.project_storage.project_home import find_project_home
        if find_project_home(self.outputs_root, project_id).path != home:
            raise CodexExecSupervisorError("abandonment project and manifest identity differ")
        rows = connection.execute("SELECT * FROM exec_attempts WHERE project_id=? ORDER BY attempt_id", (project_id,)).fetchall()
        expected = {str(attempt.attempt_id): attempt for attempt in packet.attempts}
        if len(expected) != len(packet.attempts) or set(expected) != {row["attempt_id"] for row in rows}:
            raise CodexExecSupervisorError("abandonment must bind every exact project host attempt")
        blockers, unknown, facts = [], [], []
        for row in rows:
            original = CodexExecAttempt.model_validate_json(row["attempt_json"])
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            if (str(original.project_id) != project_id or self._identity(original) != self._identity(expected[row["attempt_id"]])
                    or self._identity(current) != self._identity(original)
                    or (row["project_home"] and Path(row["project_home"]) != home)):
                raise CodexExecSupervisorError("abandonment immutable attempt or project-home identity differs")
            self._namespace_assert_attempt(original, check_profile=False)
            if current.state not in {"completed", "failed", "settled"}:
                unknown.append(row["attempt_id"])
            identities = [(row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"]),
                          (current.process_id, current.process_group_id, current.process_birth_identity)]
            for identity in identities:
                if identity == (None, None, None):
                    # A durable unregistered spawn intent cannot prove absence.
                    if current.state in {"spawn_intent", "running", "validating", "outcome_unknown", "cancel_requested"}:
                        blockers.append(f"{current.job_id}: local process identity is unresolved")
                elif not self._prove_group_absent(*identity):
                    blockers.append(f"{current.job_id}: local process group is not proven absent")
            validator = connection.execute("SELECT * FROM exec_validation_process WHERE attempt_id=?", (row["attempt_id"],)).fetchone()
            if validator is not None and (validator["spawn_state"] != "running" or not self._prove_group_absent(
                    validator["process_id"], validator["process_group_id"], validator["process_birth_identity"])):
                blockers.append(f"{current.job_id}: validator ownership is unresolved")
            facts.append((row["attempt_id"], row["status_json"], row["worker_pid"], row["worker_group_id"],
                          row["worker_birth_identity"], tuple(validator) if validator else None))
        revoked = connection.execute("SELECT preview_hash FROM exec_project_revocations WHERE project_id=?", (project_id,)).fetchone()
        digest = stable_hash({"projectId": project_id, "projectHome": str(home), "attempts": facts})
        return AbandonmentPreview(project_id=project_id, preview_hash=revoked[0] if revoked else digest,
            eligible=not blockers, revoked=revoked is not None, blockers=sorted(set(blockers)), unknown_attempt_ids=unknown)

    def abandonment_preview(self, raw_packet):
        packet = AbandonmentPacket.model_validate(raw_packet)
        with closing(self._connect()) as connection:
            return self._abandonment_context(connection, packet)

    def revoke_project(self, raw_packet):
        packet = AbandonmentPacket.model_validate(raw_packet)
        if packet.expected_preview_hash is None:
            raise CodexExecSupervisorError("revocation requires explicit current preview consent")
        with self._guard, self._abandonment_fence(packet.project_id), closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                context = self._abandonment_context(connection, packet)
                if context.preview_hash != packet.expected_preview_hash:
                    raise CodexExecSupervisorError("abandonment preview changed; inspect again")
                if not context.eligible:
                    raise CodexExecSupervisorError("; ".join(context.blockers))
                if not context.revoked:
                    connection.execute("INSERT INTO exec_project_revocations VALUES (?,?,?,?)",
                        (packet.project_id, packet.project_home, context.preview_hash, time.time()))
                connection.execute("UPDATE exec_queue SET enabled=0 WHERE attempt_id IN "
                    "(SELECT attempt_id FROM exec_attempts WHERE project_id=?)", (packet.project_id,))
                # No status/receipt/budget/slot mutation: uncertainty stays held.
                connection.commit()
                return context.model_copy(update={"revoked": True})
            except BaseException:
                connection.rollback()
                raise
