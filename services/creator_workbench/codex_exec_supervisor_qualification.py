"""Durable finite-arm registrations; ordinary and one-attempt owners are unchanged."""
import json
import time
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.codex_exec_qualification_contracts import (
    CodexExecQualificationBinding, QualificationActivation, QualificationProject,
)


class CodexExecSupervisorQualificationMixin:
    @property
    def _finite_qualification(self):
        return isinstance(self._namespace, CodexExecQualificationBinding)

    def _qualification_initialize(self, connection):
        if not self._finite_qualification:
            return
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS exec_qualification_arm (
                identity INTEGER PRIMARY KEY CHECK(identity=1),
                activation_json TEXT, halt_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS exec_qualification_project (
                role TEXT PRIMARY KEY CHECK(role IN ('primary','sidecar')),
                project_id TEXT NOT NULL UNIQUE, run_id TEXT NOT NULL UNIQUE,
                registration_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exec_qualification_attempt (
                attempt_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                job_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                attempt_json TEXT NOT NULL, UNIQUE(project_id,job_id),
                UNIQUE(project_id,operation_key)
            );
            INSERT OR IGNORE INTO exec_qualification_arm(identity) VALUES(1);
        """)

    def _qualification_controls(self):
        binding = self._namespace
        root = Path(binding.controls_root.path)
        self._qualification_path(binding.controls_root, directory=True)
        # Code-only controls precede allocation, avoiding a binding hash cycle.
        control = root / "pair-controls.json"
        self._namespace_regular_file(control)
        raw = self._read_regular(control,max_bytes=1_000_000)
        if sha256(raw).hexdigest() != binding.controls_sha256:
            raise CodexExecSupervisorError("qualification source controls changed")
        controls = json.loads(raw)
        for name, expected in controls["files"].items():
            if Path(name).name != name:
                raise CodexExecSupervisorError("qualification controls contain a foreign path")
            path = root / name
            self._namespace_regular_file(path)
            if sha256(self._read_regular(path,max_bytes=1_000_000)).hexdigest() != expected:
                raise CodexExecSupervisorError("qualification executable controls changed")

    def _qualification_path(self, expected, *, directory=False):
        import os
        import stat
        path = Path(expected.path)
        info = path.lstat()
        if (not path.is_absolute() or path.resolve(strict=True) != path or path.is_symlink()
                or (info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode)) !=
                   (expected.device, expected.inode, expected.uid, expected.mode)
                or info.st_uid != os.getuid()
                or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
            raise CodexExecSupervisorError("qualification physical identity changed")
        if not directory and info.st_nlink != 1:
            raise CodexExecSupervisorError("qualification file has multiple owners")

    def _qualification_project_files(self, project):
        self._qualification_path(project.home, directory=True)
        self._qualification_path(project.database)
        home = Path(project.home.path)
        if (home.parent != self.outputs_root or Path(project.database.path) != home / "project.sqlite3"
                or sha256((home / "project.json").read_bytes()).hexdigest() != project.manifest_sha256):
            raise CodexExecSupervisorError("qualification project home/manifest differs")
        from plotloom.project_storage.project_home import find_project_home
        if find_project_home(self.outputs_root, str(project.project_id)).path != home:
            raise CodexExecSupervisorError("qualification project catalog differs")

    def register_qualification_project(self, raw_project):
        """The fixed trusted driver registers actual created IDs, never placeholders."""
        if not self._finite_qualification:
            raise CodexExecSupervisorError("finite qualification registration requires its namespace")
        project = QualificationProject.model_validate(raw_project)
        self._qualification_project_files(project)
        with closing(self._namespace_read_database(Path(project.database.path), require_private=False)) as database:
            row = database.execute("SELECT * FROM v2_autopilot_runs WHERE id=? AND project_id=?",
                (str(project.run_id), str(project.project_id))).fetchone()
            if (row is None or row["claim"] != project.claim or row["policy_hash"] != project.policy_hash):
                raise CodexExecSupervisorError("qualification registration lacks its actual claimed run")
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute("SELECT * FROM exec_qualification_project WHERE role=?", (project.role,)).fetchone()
            raw = project.model_dump_json(by_alias=True)
            if prior is not None:
                if prior["registration_json"] != raw:
                    raise CodexExecSupervisorError("qualification role cannot be replaced")
            else:
                if connection.execute('SELECT 1 FROM exec_qualification_project WHERE project_id=? OR run_id=?',
                        (str(project.project_id),str(project.run_id))).fetchone():
                    raise CodexExecSupervisorError('qualification project/run already owns another role')
                if connection.execute("SELECT 1 FROM exec_attempts WHERE project_id=?", (str(project.project_id),)).fetchone():
                    raise CodexExecSupervisorError("qualification role must precede first dispatch")
                connection.execute("INSERT INTO exec_qualification_project VALUES(?,?,?,?)",
                    (project.role, str(project.project_id), str(project.run_id), raw))
            connection.commit()
        return project

    def activate_qualification(self, *, prior_serial_receipt_sha256=None,
            started_wall_ns=None, started_monotonic_ns=None):
        if not self._finite_qualification:
            raise CodexExecSupervisorError("finite qualification activation requires its namespace")
        self._namespace_assert_attempt(check_profile=True)
        self._qualification_controls()
        if (self._namespace.arm == "parallel") != (prior_serial_receipt_sha256 is not None):
            raise CodexExecSupervisorError("qualification activation must follow serial success")
        activation = QualificationActivation(startedWallNs=started_wall_ns if started_wall_ns is not None else time.time_ns(),
            startedMonotonicNs=started_monotonic_ns if started_monotonic_ns is not None else time.monotonic_ns(),
            priorSerialReceiptSha256=prior_serial_receipt_sha256)
        if activation.started_wall_ns>time.time_ns() or activation.started_monotonic_ns>time.monotonic_ns():
            raise CodexExecSupervisorError('qualification original start cannot be in the future')
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM exec_qualification_arm WHERE identity=1").fetchone()
            if row["activation_json"] is not None or row["halt_reason"] is not None:
                raise CodexExecSupervisorError("qualification arm activation is one-shot")
            if not connection.execute("SELECT 1 FROM exec_qualification_project WHERE role='primary'").fetchone():
                raise CodexExecSupervisorError("qualification primary identity must precede activation")
            connection.execute("UPDATE exec_qualification_arm SET activation_json=? WHERE identity=1",
                (activation.model_dump_json(by_alias=True),))
            connection.commit()
        return activation

    def halt_qualification(self, reason):
        if not self._finite_qualification:
            return
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE exec_qualification_arm SET halt_reason=COALESCE(halt_reason,?) WHERE identity=1",
                (str(reason)[:200],))
            connection.commit()

    def freeze_qualification_attempt(self, raw_attempt, *, settlement_only=False):
        """Retain the actual current-owner reservation before the host admit call."""
        if not self._finite_qualification:
            raise CodexExecSupervisorError("finite qualification freeze requires its namespace")
        attempt = CodexExecAttempt.model_validate(raw_attempt)
        self._namespace_assert_attempt(check_profile=True)
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT attempt_json FROM exec_qualification_attempt WHERE attempt_id=?",
                (str(attempt.attempt_id),)).fetchone()
            if existing is not None:
                if self._identity(CodexExecAttempt.model_validate_json(existing[0])) != self._identity(attempt):
                    raise CodexExecSupervisorError("qualification frozen attempt identity changed")
                return
            project = self._qualification_check_role(connection, attempt)
            self._qualification_owner_snapshot(project, attempt)
            if not settlement_only and attempt.state not in {'reserved','spawn_intent'}:
                raise CodexExecSupervisorError('qualification freeze requires its original unstarted reservation')
            if not settlement_only and not self._qualification_new_work(connection, attempt):
                connection.commit()
                raise CodexExecSupervisorError("qualification arm held before new authorization")
            self._qualification_budget(connection, attempt)
            connection.execute("INSERT INTO exec_qualification_attempt VALUES(?,?,?,?,?)",
                (str(attempt.attempt_id), str(attempt.project_id), attempt.job_id,
                 attempt.operation_key, attempt.model_dump_json(by_alias=True)))
            connection.commit()

    def _qualification_requested(self, attempt=None, *, attempt_id=None):
        if attempt is None and attempt_id is None:
            return
        with closing(self._namespace_read_database(self.private_root / "supervisor.sqlite3")) as connection:
            key = str(attempt.attempt_id if attempt is not None else attempt_id)
            row = connection.execute("SELECT attempt_json FROM exec_qualification_attempt WHERE attempt_id=?", (key,)).fetchone()
            if row is None or (attempt is not None and self._identity(attempt) !=
                    self._identity(CodexExecAttempt.model_validate_json(row[0]))):
                raise CodexExecSupervisorError("foreign or unfrozen qualification attempt")

    def _qualification_connection(self, connection):
        # Integrity checks only. Time/HALT must never make settlement inaccessible.
        for name in ('exec_qualification_arm','exec_qualification_project','exec_qualification_attempt'):
            if not self._namespace_table_exists(connection,name):
                raise CodexExecSupervisorError('qualification registration/activation metadata disappeared')
        arms=connection.execute('SELECT * FROM exec_qualification_arm').fetchall()
        if len(arms)!=1 or arms[0]['identity']!=1:
            raise CodexExecSupervisorError('qualification original activation metadata disappeared')
        if arms[0]['activation_json'] is not None:
            QualificationActivation.model_validate_json(arms[0]['activation_json'])
        elif any(connection.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone() is not None
                for table in ('exec_qualification_attempt','exec_attempts')):
            # Empty setup precedes activation. An original authorization must
            # retain its activation, including after HALT or time expiry.
            raise CodexExecSupervisorError('qualification original activation disappeared after authorization')
        for row in connection.execute('SELECT * FROM exec_qualification_project'):
            project=QualificationProject.model_validate_json(row['registration_json'])
            if (row['role'],row['project_id'],row['run_id'])!=(project.role,str(project.project_id),str(project.run_id)):
                raise CodexExecSupervisorError('qualification role registration columns differ')
        for row in connection.execute('SELECT * FROM exec_qualification_attempt'):
            frozen=CodexExecAttempt.model_validate_json(row['attempt_json'])
            if (row['attempt_id'],row['project_id'],row['job_id'],row['operation_key'])!=(
                    str(frozen.attempt_id),str(frozen.project_id),frozen.job_id,frozen.operation_key):
                raise CodexExecSupervisorError('qualification frozen authorization columns differ')
            self._qualification_check_role(connection,frozen)
        self._qualification_budget(connection)
        for row in connection.execute("SELECT * FROM exec_attempts"):
            frozen = connection.execute("SELECT attempt_json FROM exec_qualification_attempt WHERE attempt_id=?",
                (row["attempt_id"],)).fetchone()
            if frozen is None:
                raise CodexExecSupervisorError("foreign qualification ledger attempt")
            expected = CodexExecAttempt.model_validate_json(frozen[0])
            role = connection.execute("SELECT registration_json FROM exec_qualification_project WHERE project_id=?",
                (str(expected.project_id),)).fetchone()
            if role is None:
                raise CodexExecSupervisorError("qualification ledger has no registered project")
            project = QualificationProject.model_validate_json(role[0])
            if expected.run_id != project.run_id:
                raise CodexExecSupervisorError("qualification ledger run differs from registered role")
            self._qualification_check_role(connection,expected)
            self._namespace_assert_ledger_row(connection, row, expected, project_home=Path(project.home.path))
        for table in ("exec_queue", "exec_slot", "exec_validation_process", "exec_process_exits", "exec_recovery_evidence"):
            if connection.execute(f"SELECT 1 FROM {table} x LEFT JOIN exec_attempts a ON a.attempt_id=x.attempt_id "
                    "WHERE a.attempt_id IS NULL LIMIT 1").fetchone():
                raise CodexExecSupervisorError("foreign qualification queue/slot/validator")
        for row in connection.execute("SELECT s.domain,a.attempt_json FROM exec_slot s JOIN exec_attempts a ON a.attempt_id=s.attempt_id"):
            if row["domain"] != CodexExecAttempt.model_validate_json(row["attempt_json"]).domain:
                raise CodexExecSupervisorError("qualification slot domain differs")

    def _qualification_terminal(self, connection, attempt):
        if self._finite_qualification and (attempt.state in {"failed", "outcome_unknown", "cancel_requested"}
                or (attempt.state == "settled" and attempt.terminal_result != "success")):
            connection.execute("UPDATE exec_qualification_arm SET halt_reason=COALESCE(halt_reason,?) WHERE identity=1",
                ("attempt_" + attempt.state,))
