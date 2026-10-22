"""Finite admission, HALT and start fences inside the existing owner transactions."""
import json
import time
from contextlib import closing
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.codex_exec_qualification_contracts import (
    IMAGE_PREFIXES, TEXT_OPERATIONS, QualificationActivation, QualificationProject,
)


class CodexExecSupervisorQualificationAdmissionMixin:
    def _qualification_check_role(self, connection, attempt):
        row = connection.execute("SELECT * FROM exec_qualification_project WHERE project_id=?",
            (str(attempt.project_id),)).fetchone()
        if row is None:
            raise CodexExecSupervisorError("qualification attempt has no designated project role")
        project = QualificationProject.model_validate_json(row["registration_json"])
        self._qualification_project_files(project)
        if (str(attempt.run_id) != str(project.run_id)
                or attempt.profile_hash != self._namespace.profile.profile_hash
                or attempt.plotloom_code_revision != self._namespace.source_revision):
            raise CodexExecSupervisorError("qualification run/profile/source identity differs")
        if project.role == "sidecar" and (attempt.domain != "text" or attempt.operation_key != "outline"):
            raise CodexExecSupervisorError("qualification sidecar permits only its original Outline")
        if attempt.domain == "text":
            if attempt.operation_key not in TEXT_OPERATIONS or attempt.validation_plan_hash is None:
                raise CodexExecSupervisorError("qualification text operation is outside production scope")
        elif not attempt.operation_key.startswith(IMAGE_PREFIXES):
            raise CodexExecSupervisorError("qualification image operation is outside production scope")
        return project

    def _qualification_budget(self, connection, candidate=None):
        attempts = [CodexExecAttempt.model_validate_json(row[0]) for row in
            connection.execute("SELECT attempt_json FROM exec_qualification_attempt")]
        if candidate is not None:
            if any(item.attempt_id == candidate.attempt_id for item in attempts):
                return
            if any((item.project_id, item.job_id) == (candidate.project_id, candidate.job_id)
                    or (item.project_id, item.operation_key) == (candidate.project_id, candidate.operation_key)
                    for item in attempts):
                raise CodexExecSupervisorError("qualification job/operation already owns its original attempt")
            attempts.append(candidate)
        text = sum(item.domain == "text" for item in attempts)
        images = sum(item.reserved_image_outputs for item in attempts if item.domain == "image")
        if text > 9 or images > 32:
            raise CodexExecSupervisorError("qualification arm text/image-output ceiling exceeded")
        for role_row in connection.execute("SELECT * FROM exec_qualification_project"):
            owned = [item for item in attempts if str(item.project_id) == role_row["project_id"]]
            max_text, max_outputs, max_jobs = (8, 32, 40) if role_row["role"] == "primary" else (1, 0, 1)
            if (sum(item.domain == "text" for item in owned) > max_text
                    or sum(item.reserved_image_outputs for item in owned) > max_outputs
                    or len(owned) > max_jobs):
                raise CodexExecSupervisorError("qualification project role ceiling exceeded")

    def _qualification_owner_snapshot(self, project, attempt, *, require_spent=False):
        with closing(self._namespace_read_database(Path(project.database.path), require_private=False)) as database:
            run = database.execute("SELECT * FROM v2_autopilot_runs WHERE id=? AND project_id=?",
                (str(project.run_id), str(project.project_id))).fetchone()
            row = database.execute("SELECT snapshot FROM v2_autopilot_exec_attempts WHERE id=?",
                (str(attempt.attempt_id),)).fetchone()
        if (run is None or run["claim"] != project.claim or run["policy_hash"] != project.policy_hash
                or row is None or self._identity(CodexExecAttempt.model_validate(json.loads(row[0]))) != self._identity(attempt)):
            raise CodexExecSupervisorError("qualification attempt lacks its exact current project reservation")
        if require_spent and CodexExecAttempt.model_validate(json.loads(row[0])).state!='spawn_intent':
            raise CodexExecSupervisorError('qualification initial admission requires the consumed project intent')
        from plotloom.persistence.codec import stable_hash
        policy=json.loads(run['policy'])
        if (stable_hash(policy)!=project.policy_hash or policy['codeRevision']!=self._namespace.source_revision
                or policy['executorBinding']!=self._namespace.profile.model_dump(mode='json',by_alias=True)):
            raise CodexExecSupervisorError('qualification current frozen project policy differs')
        return run

    def _qualification_new_work(self, connection, attempt=None):
        if not self._finite_qualification:
            return True
        self._qualification_controls()
        row = connection.execute("SELECT * FROM exec_qualification_arm WHERE identity=1").fetchone()
        if row["halt_reason"] is not None or row["activation_json"] is None:
            return False
        self._qualification_budget(connection)
        activation = QualificationActivation.model_validate_json(row["activation_json"])
        wall = (time.time_ns() - activation.started_wall_ns) / 1_000_000_000
        monotonic = (time.monotonic_ns() - activation.started_monotonic_ns) / 1_000_000_000
        reason = None
        if min(wall, monotonic) < 0 or abs(wall - monotonic) > 5:
            reason = "qualification_clock_discontinuity"
        elapsed = max(wall, monotonic)
        if elapsed >= self._namespace.max_wall_seconds:
            reason = reason or "qualification_original_deadline"
        for current in connection.execute("SELECT status_json FROM exec_attempts"):
            status = CodexExecAttempt.model_validate_json(current[0])
            if status.state in {"failed", "outcome_unknown", "cancel_requested"} or (
                    status.state == "settled" and status.terminal_result != "success"):
                reason = reason or "qualification_original_attempt_unsafe"
        if attempt is not None:
            project=self._qualification_check_role(connection,attempt)
            run=self._qualification_owner_snapshot(project,attempt)
            if run['state'] not in {'running','waiting'}:
                reason=reason or 'qualification_owner_stopped_new_work'
            # Current trusted plans have exactly validate+render; the existing
            # validation owner gives each step 300 seconds. Reserve settlement
            # separately, within the original 90+10 minute arm envelope.
            validation = 2 * self.STEP_TIMEOUT_SECONDS if attempt.domain == "text" else 0
            required = self._namespace.profile.max_runtime_seconds + validation + self._namespace.max_settlement_seconds
            envelope = self._namespace.max_wall_seconds + self._namespace.max_settlement_seconds
            if elapsed + required > envelope:
                reason = reason or "qualification_insufficient_original_time"
        if reason is not None:
            connection.execute("UPDATE exec_qualification_arm SET halt_reason=COALESCE(halt_reason,?) WHERE identity=1", (reason,))
            return False
        return True

    def _qualification_admission(self, connection, attempt, *, enabled):
        if not self._finite_qualification:
            return True
        project=self._qualification_check_role(connection, attempt)
        self._qualification_owner_snapshot(project,attempt,require_spent=enabled)
        frozen = connection.execute("SELECT attempt_json FROM exec_qualification_attempt WHERE attempt_id=?",
            (str(attempt.attempt_id),)).fetchone()
        if frozen is None or self._identity(CodexExecAttempt.model_validate_json(frozen[0])) != self._identity(attempt):
            raise CodexExecSupervisorError("qualification original attempt was not frozen before admission")
        self._qualification_budget(connection)
        # Disabled insertion is the existing negative authorization fence. It
        # cannot enable work and remains usable to park retained uncertain intent.
        return not enabled or self._qualification_new_work(connection, attempt)
