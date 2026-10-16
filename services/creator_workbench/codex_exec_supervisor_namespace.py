"""Persisted confinement for a single externally pinned supervisor identity.

Ordinary installations are unbound. A binding file or persisted ledger pin makes
the pin mandatory, including after bridge restart and worker reconstruction.
"""
import os
import sqlite3
import stat
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorNamespaceMixin:
    def _configure_namespace(self, expected_sha256):
        self._namespace = None
        self._namespace_sha256 = expected_sha256
        self._namespace_database_identity = None
        self._namespace_initializing = False
        binding_file = self.private_root / "namespace-binding.json"
        database = self.private_root / "supervisor.sqlite3"
        if expected_sha256 is None:
            if binding_file.exists() or binding_file.is_symlink():
                raise CodexExecSupervisorError("one-attempt namespace pin is required")
            if database.exists():
                with closing(self._namespace_read_database(database, require_private=False)) as connection:
                    if any(self._namespace_table_exists(connection,name) for name in
                            ('exec_namespace_configuration','exec_qualification_arm','exec_qualification_project','exec_qualification_attempt')):
                        raise CodexExecSupervisorError("persisted namespace cannot become unbound")
            return
        from plotloom.codex_exec_namespace_contracts import CodexExecNamespaceBinding
        self._namespace_file_identity = self._namespace_regular_file(binding_file)
        raw = binding_file.read_bytes()
        if sha256(raw).hexdigest() != expected_sha256:
            raise CodexExecSupervisorError("one-attempt namespace binding hash differs")
        try:
            import json
            from plotloom.codex_exec_qualification_contracts import CodexExecQualificationBinding
            model = (CodexExecQualificationBinding if json.loads(raw).get("version") ==
                "plotloom.exec-qualification-arm.v1" else CodexExecNamespaceBinding)
            self._namespace = model.model_validate_json(raw)
        except ValueError as error:
            raise CodexExecSupervisorError("invalid one-attempt namespace binding") from error
        self._namespace_assert_files()
        limits = self._namespace.limits
        if self._requested_pool_limits is not None:
            from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
            if CodexExecPoolLimits.model_validate(self._requested_pool_limits) != limits:
                raise CodexExecSupervisorError("namespace pool limits differ")
        self._requested_pool_limits = limits
        self._namespace_assert_profile()
        if database.exists() or database.is_symlink():
            self._namespace_database_identity = self._namespace_regular_file(database)
            with closing(self._namespace_read_database(database)) as connection:
                if self._namespace_table_exists(connection, "exec_namespace_configuration"):
                    self._namespace_assert_connection(connection)
                else:
                    if any(self._namespace_table_exists(connection,name) for name in
                            ('exec_qualification_arm','exec_qualification_project','exec_qualification_attempt')):
                        raise CodexExecSupervisorError('qualification ledger cannot be rebound after binding loss')
                    # Binding is allowed only before any identity has entered a
                    # current empty ledger. Never convert an occupied/legacy pool.
                    for table in ("exec_attempts", "exec_queue", "exec_slot", "exec_validation_process"):
                        if not self._namespace_table_exists(connection, table) or connection.execute(
                                f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None:
                            raise CodexExecSupervisorError("namespace requires a fresh empty ledger")
                    schema = connection.execute("PRAGMA table_info(exec_slot)").fetchall()
                    if "slot_id" in {row["name"] for row in schema}:
                        raise CodexExecSupervisorError("namespace cannot convert a legacy ledger")
                    self._namespace_assert_pool(connection)
        self._namespace_initializing = True

    @staticmethod
    def _namespace_regular_file(path):
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_nlink != 1):
            raise CodexExecSupervisorError("unsafe one-attempt namespace file")
        return metadata.st_dev, metadata.st_ino, metadata.st_uid

    @staticmethod
    def _namespace_read_database(database, *, require_private=True):
        if require_private:
            CodexExecSupervisorNamespaceMixin._namespace_regular_file(database)
        else:
            metadata = database.lstat()
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or metadata.st_nlink != 1):
                raise CodexExecSupervisorError("Codex Exec supervisor database is unsafe")
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _namespace_table_exists(connection, name):
        return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    def _namespace_assert_files(self):
        binding = self._namespace
        if binding is None:
            if (self.private_root / "namespace-binding.json").exists():
                raise CodexExecSupervisorError("unbound supervisor encountered a namespace binding")
            return
        path = self.private_root / "namespace-binding.json"
        if (self._namespace_regular_file(path) != self._namespace_file_identity
                or sha256(path.read_bytes()).hexdigest() != self._namespace_sha256):
            raise CodexExecSupervisorError("one-attempt namespace binding changed")
        expected_database = binding.database
        database = self.private_root / "supervisor.sqlite3"
        if (expected_database.path != str(database)
                or expected_database.mode != 0o600
                or self._namespace_regular_file(database) != (
                    expected_database.device, expected_database.inode, expected_database.uid)):
            raise CodexExecSupervisorError("namespace ledger physical identity changed")
        actual_roots = {"source_root": self.source_root, "outputs_root": self.outputs_root,
            "private_root": self.private_root, "executable": self.executable}
        for name in ("application_root", "outputs_root", "private_root", "source_root", "executable"):
            expected = getattr(binding, name)
            path = Path(expected.path)
            if not path.is_absolute() or path.resolve(strict=True) != path or path.is_symlink():
                raise CodexExecSupervisorError("namespace physical path changed")
            if name in actual_roots and path != actual_roots[name]:
                raise CodexExecSupervisorError("supervisor roots differ from its namespace")
            metadata = path.lstat()
            if (metadata.st_dev, metadata.st_ino, metadata.st_uid, stat.S_IMODE(metadata.st_mode)) != (
                    expected.device, expected.inode, expected.uid, expected.mode):
                raise CodexExecSupervisorError("namespace physical identity changed")
            if metadata.st_uid != os.getuid():
                raise CodexExecSupervisorError("namespace paths must belong to this user")
            if name == "executable":
                if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                        or metadata.st_mode & 0o022 or not metadata.st_mode & 0o111
                        or metadata.st_size != expected.size or sha256(path.read_bytes()).hexdigest() != expected.sha256):
                    raise CodexExecSupervisorError("namespace executable changed")
            elif not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o022:
                raise CodexExecSupervisorError("namespace root is unsafe")
            elif name != "source_root" and expected.mode != 0o700:
                raise CodexExecSupervisorError("namespace data roots must be private")
        if self._finite_qualification:
            if Path(binding.application_database.path) != Path(binding.application_root.path)/'application.sqlite3':
                raise CodexExecSupervisorError('qualification application database differs')
            self._qualification_path(binding.application_database)

    def _namespace_assert_profile(self):
        if self._namespace is not None:
            from plotloom.codex_exec_profile import build_codex_exec_profile
            profile = build_codex_exec_profile(self.executable, source_root=self.source_root,
                pool_limits=self._namespace.limits)
            if profile != self._namespace.profile:
                raise CodexExecSupervisorError("namespace source or execution profile changed")

    def _namespace_assert_attempt(self, attempt=None, *, attempt_id=None, check_profile=False):
        self._namespace_assert_files()
        if self._namespace is None:
            return
        if self._finite_qualification:
            self._qualification_requested(attempt, attempt_id=attempt_id)
            if check_profile:
                self._namespace_assert_profile()
            return
        expected = self._namespace.attempt
        if attempt_id is not None and str(attempt_id) != str(expected.attempt_id):
            raise CodexExecSupervisorError("foreign attempt outside one-attempt namespace")
        if attempt is not None and self._identity(attempt) != self._identity(expected):
            raise CodexExecSupervisorError("foreign identity outside one-attempt namespace")
        if check_profile:
            self._namespace_assert_profile()

    def _namespace_before_connect(self):
        self._namespace_assert_files()
        if self._namespace is None or self._namespace_initializing:
            return
        if self._namespace_regular_file(self.database) != self._namespace_database_identity:
            raise CodexExecSupervisorError("namespace ledger physical identity changed")
        with closing(self._namespace_read_database(self.database)) as connection:
            self._namespace_assert_connection(connection)

    def _namespace_assert_connection(self, connection):
        if self._namespace is None:
            if any(self._namespace_table_exists(connection,name) for name in
                    ('exec_namespace_configuration','exec_qualification_arm','exec_qualification_project','exec_qualification_attempt')):
                raise CodexExecSupervisorError("persisted namespace cannot become unbound")
            return
        self._namespace_assert_files()
        saved = connection.execute("SELECT * FROM exec_namespace_configuration").fetchall()
        if len(saved) != 1 or saved[0]["identity"] != 1 or saved[0]["binding_sha256"] != self._namespace_sha256:
            raise CodexExecSupervisorError("namespace ledger binding differs")
        self._namespace_assert_pool(connection)
        if self._finite_qualification:
            self._qualification_connection(connection)
            return
        expected = self._namespace.attempt
        for row in connection.execute("SELECT * FROM exec_attempts"):
            self._namespace_assert_ledger_row(connection, row, expected)
        for table in ("exec_queue", "exec_slot", "exec_validation_process"):
            for row in connection.execute(f"SELECT * FROM {table}"):
                if row["attempt_id"] != str(expected.attempt_id):
                    raise CodexExecSupervisorError("foreign namespace queue, slot or validator")
                if connection.execute("SELECT 1 FROM exec_attempts WHERE attempt_id=?", (row["attempt_id"],)).fetchone() is None:
                    raise CodexExecSupervisorError("orphan namespace queue, slot or validator")
                if table == "exec_slot" and row["domain"] != expected.domain:
                    raise CodexExecSupervisorError("namespace slot domain differs")

    def _namespace_assert_ledger_row(self, connection, row, expected, *, project_home=None):
        """Shared integrity for exact-attempt and finite registered namespaces."""
        from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReceipt, assert_receipt_matches_attempt
        original = CodexExecAttempt.model_validate_json(row["attempt_json"])
        current = CodexExecAttempt.model_validate_json(row["status_json"])
        if not self._finite_qualification:
            self._namespace_assert_attempt(original)
            self._namespace_assert_attempt(current)
        if any(self._identity(item) != self._identity(expected) for item in (original, current)) or (
                row["attempt_id"], row["project_id"], row["job_id"]) != (
                str(expected.attempt_id), str(expected.project_id), expected.job_id):
            raise CodexExecSupervisorError("foreign namespace ledger row")
        tombstone = self._namespace_cancel_tombstone(connection, row, original, current)
        if original.state != "spawn_intent" and not tombstone:
            raise CodexExecSupervisorError("namespace ledger lacks its admitted snapshot")
        if not tombstone:
            home, job = Path(row["project_home"]), Path(row["job_root"])
            private = self.private_root / "attempts" / str(expected.attempt_id)
            if (Path(row["private_dir"]) != private or not home.is_relative_to(self.outputs_root)
                    or (project_home is not None and home != project_home)):
                raise CodexExecSupervisorError("namespace ledger paths differ")
            if not job.is_relative_to(home) or home.resolve(strict=True)!=home or job.resolve(strict=True)!=job:
                raise CodexExecSupervisorError("namespace job escapes its project")
        if row["receipt_json"] is not None:
            assert_receipt_matches_attempt(current, CodexExecReceipt.model_validate_json(row["receipt_json"]))

    def _namespace_assert_pool(self, connection):
        from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
        pool = connection.execute("SELECT * FROM exec_pool_configuration").fetchall()
        if (len(pool) != 1 or pool[0]["version"] != "plotloom.exec-pool.v1"
                or CodexExecPoolLimits.model_validate_json(pool[0]["limits_json"]) != self._namespace.limits):
            raise CodexExecSupervisorError("namespace ledger pool differs")

    @staticmethod
    def _namespace_cancel_tombstone(connection, row, original, current):
        """Classify only the missing-host snapshots written by control.cancel.

        Cancellation can prove no start or conservatively hold unknown work;
        neither shape is an admitted delivery area or permission to launch.
        """
        if not all(row[name] == "" for name in ("private_dir", "project_home", "job_root")):
            return False
        from plotloom.codex_exec_contracts import transition_exec_attempt
        if any(row[name] is not None for name in (
                "worker_pid", "worker_group_id", "worker_birth_identity", "receipt_json", "manifest_json")):
            raise CodexExecSupervisorError("namespace cancellation tombstone has execution artifacts")
        if original.state in {"reserved", "queued", "spawn_intent"}:
            expected = transition_exec_attempt(original, state="settled", terminal_result="not_started",
                remote_tool_state="not_applicable",
                evidence_hash=sha256(f"plotloom.codex-exec.not-started.v1:{original.attempt_id}".encode()).hexdigest(),
                image_budget_state="released" if original.domain == "image" else "none")
            slot = None
        elif original.state in {"running", "validating", "outcome_unknown", "cancel_requested"}:
            expected = transition_exec_attempt(original, state="outcome_unknown")
            slot = original.domain
        else:
            raise CodexExecSupervisorError("namespace cancellation tombstone has invalid original state")
        held = connection.execute("SELECT domain FROM exec_slot WHERE attempt_id=?", (str(original.attempt_id),)).fetchone()
        if current != expected or (held[0] if held is not None else None) != slot:
            raise CodexExecSupervisorError("namespace cancellation tombstone facts or capacity differ")
        for table in ("exec_queue", "exec_validation_process"):
            if connection.execute(f"SELECT 1 FROM {table} WHERE attempt_id=?", (str(original.attempt_id),)).fetchone() is not None:
                raise CodexExecSupervisorError("namespace cancellation tombstone has queued or validator work")
        return True

    def _namespace_finish_initialization(self, connection):
        if self._namespace is None:
            return
        connection.execute("CREATE TABLE IF NOT EXISTS exec_namespace_configuration "
            "(identity INTEGER PRIMARY KEY CHECK(identity=1), binding_sha256 TEXT NOT NULL)")
        saved = connection.execute("SELECT binding_sha256 FROM exec_namespace_configuration WHERE identity=1").fetchone()
        if saved is None:
            connection.execute("INSERT INTO exec_namespace_configuration VALUES(1,?)", (self._namespace_sha256,))
        self._qualification_initialize(connection)
        self._namespace_assert_connection(connection)
        self._namespace_database_identity = self._namespace_regular_file(self.database)
        self._namespace_initializing = False
