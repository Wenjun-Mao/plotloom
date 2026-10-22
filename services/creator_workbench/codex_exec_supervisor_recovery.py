"""Explicit postmortem settlement; never resumes or replays frozen work."""
from __future__ import annotations

import json
import os
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorRecoveryMixin:
    def _record_cli_exit(self, attempt, process_id, group_id, birth_identity, exit_code):
        """Only the registered waiter may persist the native Popen.wait result."""
        if type(exit_code) is not int:
            raise CodexExecSupervisorError("CLI wait did not return an exit code")
        from plotloom.codex_exec_contracts import CodexExecAttempt
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            worker = (row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"])
            if (worker != (os.getpid(), *self._process_identity(os.getpid()))
                    or self._identity(current) != self._identity(attempt)
                    or (current.process_id, current.process_group_id, current.process_birth_identity)
                    != (process_id, group_id, birth_identity)):
                raise CodexExecSupervisorError("CLI exit witness changed its exact owner")
            evidence = json.dumps({"version": "plotloom.codex-exec.wait-result.v1",
                "attemptHash": sha256(row["attempt_json"].encode()).hexdigest(),
                "processId": process_id, "processGroupId": group_id, "processBirthIdentity": birth_identity,
                "workerIdentity": worker, "processExitCode": exit_code}, sort_keys=True, separators=(",", ":"))
            prior = connection.execute("SELECT evidence_json FROM exec_process_exits WHERE attempt_id=?",
                                       (str(attempt.attempt_id),)).fetchone()
            if prior is not None and prior[0] != evidence:
                raise CodexExecSupervisorError("CLI wait evidence cannot be replaced")
            connection.execute("INSERT OR IGNORE INTO exec_process_exits VALUES (?,?)", (str(attempt.attempt_id), evidence))
            connection.commit()

    def _require_recovery_quiescence(self, connection, row, current):
        if connection.execute("SELECT 1 FROM exec_validation_process WHERE attempt_id=?",
                              (str(current.attempt_id),)).fetchone() is not None:
            raise CodexExecSupervisorError("recovery has an unresolved validator owner")
        worker = (row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"])
        owners = (worker, (current.process_id, current.process_group_id, current.process_birth_identity))
        for pid, group, birth in owners:
            if not pid or group != pid or not birth or self._process_group_exists(group):
                raise CodexExecSupervisorError("recovery lacks positive owned-group quiescence")
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            raise CodexExecSupervisorError("recovery owner PID is present or reused")

    def recover_no_remote_dispatch(self, raw_attempt):
        """Settle one exact UNKNOWN snapshot from an exhaustive read-only turn."""
        from plotloom.codex_exec_contracts import (
            CodexExecAttempt,
            transition_exec_attempt,
        )
        from plotloom.codex_exec_files import (
            assert_empty_directory,
            read_confined_regular_file,
        )
        from plotloom.codex_exec_recovery import prove_no_remote_dispatch
        from plotloom.codex_exec_runtime import (
            frozen_package_snapshot,
            locate_exact_session,
            read_exec_events,
        )
        from plotloom.project_storage.project_home import find_project_home

        requested = CodexExecAttempt.model_validate(raw_attempt)
        self._namespace_assert_attempt(requested)
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM exec_attempts WHERE attempt_id=?", (str(requested.attempt_id),)).fetchone()
            if row is None:
                raise CodexExecSupervisorError("recovery has no retained host attempt")
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            original = CodexExecAttempt.model_validate_json(row["attempt_json"])
            self._assert_project_publication(connection, current.project_id)
            if (requested != current or self._identity(original) != self._identity(current)
                    or current.state != "outcome_unknown" or current.domain != "image"
                    or current.reserved_image_outputs != 1 or current.plotloom_code_revision is None
                    or current.process_exit_code is not None or row["receipt_json"] or row["manifest_json"]):
                raise CodexExecSupervisorError("recovery requires the exact current UNKNOWN image snapshot")
            self._require_recovery_quiescence(connection, row, current)
            home = find_project_home(self.outputs_root, str(current.project_id)).path
            job, private = Path(row["job_root"]), Path(row["private_dir"])
            if (str(home) != row["project_home"] or not job.is_relative_to(home / "runs")
                    or job.name != current.job_id or job.parent.name != "jobs"
                    or not job.parent.parent.name.endswith("__" + current.job_id)
                    or private != self.private_root / "attempts" / str(current.attempt_id)
                    or any(path.resolve(strict=True) != path for path in (home, job, private))):
                raise CodexExecSupervisorError("recovery evidence paths differ from the admitted project")
            package_hash, request_bytes = frozen_package_snapshot(job, max_total_bytes=2_000_000)
            request = json.loads(request_bytes)
            if (package_hash != current.package_hash or request.get("requestHash") != current.request_hash
                    or request.get("jobId") != current.job_id or request.get("packageVersion") != 8
                    or request.get("executorBackend") != "codex_exec" or request.get("executionContract") != "codex_exec.v1"
                    or request.get("specialistPreflight", {}).get("codeRevision") != current.plotloom_code_revision):
                raise CodexExecSupervisorError("recovery package differs from the immutable admitted request")
            assert_empty_directory(job, "delivery")
            if read_confined_regular_file(private, "stderr.log", max_bytes=2_000_000) != b"":
                raise CodexExecSupervisorError("recovery requires an empty native stderr stream")
            stream = read_exec_events(private / "stdout.jsonl", max_event_bytes=2_000_000, max_total_bytes=2_000_000)
            if current.session_id is not None and current.session_id != stream.session_id:
                raise CodexExecSupervisorError("recovery session conflicts with its retained identity")
            rollout = locate_exact_session(self.codex_home, stream.session_id)
            proof = prove_no_remote_dispatch(private / "stdout.jsonl", rollout, stream.session_id,
                                            job_root=job, source_root=self.source_root)
            # Recheck all mutable evidence under the same database launch fence.
            self._require_recovery_quiescence(connection, row, current)
            if frozen_package_snapshot(job, max_total_bytes=2_000_000)[0] != package_hash:
                raise CodexExecSupervisorError("recovery package changed during inspection")
            proof_again = prove_no_remote_dispatch(private / "stdout.jsonl", rollout, stream.session_id,
                                                  job_root=job, source_root=self.source_root)
            if proof_again != proof:
                raise CodexExecSupervisorError("recovery telemetry changed during inspection")
            assert_empty_directory(job, "delivery")
            if read_confined_regular_file(private, "stderr.log", max_bytes=2_000_000) != b"":
                raise CodexExecSupervisorError("recovery stderr changed during inspection")
            record = json.dumps({"version": proof.version, "attemptHash": sha256(row["attempt_json"].encode()).hexdigest(),
                "originalStatusHash": sha256(row["status_json"].encode()).hexdigest(),
                "packageHash": package_hash, "workerIdentity": [row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"]],
                "proof": proof.model_dump(mode="json", by_alias=True)}, sort_keys=True, separators=(",", ":"))
            settled = transition_exec_attempt(current, state="settled", session_id=stream.session_id,
                terminal_result="no_remote_dispatch", remote_tool_state="not_applicable",
                image_budget_state="released", evidence_hash=sha256(record.encode()).hexdigest())
            connection.execute("INSERT INTO exec_recovery_evidence VALUES (?,?,?)",
                               (str(current.attempt_id), row["status_json"], record))
            # BEGIN IMMEDIATE plus exact supplied snapshot is the status CAS.
            self._persist_status_in_transaction(connection, settled)
            connection.commit()
            return self._status(settled)
