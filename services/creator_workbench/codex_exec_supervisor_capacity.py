"""Explicit retirement of dead local capacity, never UNKNOWN settlement."""
import json
import os
import stat
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_capacity_contracts import (
    CapacityRetirementPreview,
    CapacityRetirementReceipt,
    CapacityRetirementRequest,
    LocalCapacityReadiness,
)
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.contract_identity import new_id, utc_now
from plotloom.persistence.codec import stable_hash


class CodexExecSupervisorCapacityMixin:
    def local_capacity_readiness(self):
        """Observe local holds only; never admit, drain, retire or settle work."""
        from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
        with closing(self._connect()) as connection:
            connection.execute("BEGIN")
            counts = self._capacity_counts(connection)
            saved = connection.execute("SELECT limits_json FROM exec_pool_configuration WHERE identity=1").fetchone()
            limits = CodexExecPoolLimits.model_validate_json(saved[0])
            revoked = connection.execute("""SELECT a.attempt_id FROM exec_slot s
                JOIN exec_attempts a ON a.attempt_id=s.attempt_id
                JOIN exec_project_revocations v ON v.project_id=a.project_id
                WHERE s.domain='image' AND json_extract(a.status_json,'$.state')='outcome_unknown'
                ORDER BY a.attempt_id""").fetchall()
            retired = connection.execute("""SELECT COUNT(*) FROM exec_capacity_retirements r
                JOIN exec_attempts a ON a.attempt_id=r.attempt_id
                WHERE json_extract(a.status_json,'$.domain')='image'
                AND json_extract(a.status_json,'$.state')='outcome_unknown'""").fetchone()[0]
            blocked = counts["image"] >= limits.max_image_processes and len(revoked) == counts["image"]
            return LocalCapacityReadiness(limits=limits, held_text=counts["text"], held_image=counts["image"],
                revoked_unknown_image_attempt_ids=[row[0] for row in revoked], retired_unknown_image_holds=retired,
                image_lane_blocked=blocked, operator_action="exec-capacity-retirement-preview" if blocked else None)

    def _capacity_retirement_facts(self, connection, request):
        row = connection.execute("SELECT * FROM exec_attempts WHERE attempt_id=?", (str(request.attempt_id),)).fetchone()
        if row is None:
            raise CodexExecSupervisorError("capacity retirement has no exact retained attempt")
        original = CodexExecAttempt.model_validate_json(row["attempt_json"])
        current = self._held_attempt(row)
        if (str(current.project_id) != str(request.project_id) or current.domain != "image"
                or current.state != "outcome_unknown" or self._identity(original) != self._identity(current)):
            raise CodexExecSupervisorError("capacity retirement requires the exact UNKNOWN image identity")
        self._namespace_assert_attempt(current, check_profile=False)
        revocation = connection.execute("SELECT * FROM exec_project_revocations WHERE project_id=?", (str(request.project_id),)).fetchone()
        if revocation is None or not row["project_home"] or row["project_home"] != revocation["project_home"]:
            raise CodexExecSupervisorError("capacity retirement requires permanent exact project revocation")
        home = Path(row["project_home"])
        if not home.is_absolute() or home.parent != self.outputs_root or home.name in {"", ".", ".."}:
            raise CodexExecSupervisorError("revoked home is not one exact confined outputs child")
        metadata = self.database.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_nlink != 1 or metadata.st_uid != os.getuid()):
            raise CodexExecSupervisorError("capacity retirement ledger identity is unsafe")
        slot = connection.execute("SELECT * FROM exec_slot WHERE attempt_id=?", (str(request.attempt_id),)).fetchone()
        validator = connection.execute("SELECT * FROM exec_validation_process WHERE attempt_id=?", (str(request.attempt_id),)).fetchone()
        queue = connection.execute("SELECT * FROM exec_queue WHERE attempt_id=?", (str(request.attempt_id),)).fetchone()
        pool = connection.execute("SELECT * FROM exec_pool_configuration WHERE identity=1").fetchone()
        def directory(path):
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
                raise CodexExecSupervisorError("capacity retirement installation directory changed")
            return {"path": str(path), "device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid}
        return {"installation": {"database": str(self.database), "device": metadata.st_dev,
                    "inode": metadata.st_ino, "uid": metadata.st_uid,
                    "outputs": directory(self.outputs_root), "private": directory(self.private_root)},
                "attempt": dict(row), "revocation": dict(revocation), "slot": dict(slot) if slot else None,
                "validator": dict(validator) if validator else None, "queue": dict(queue) if queue else None,
                "poolConfiguration": dict(pool) if pool else None}

    @staticmethod
    def _retired_home_absent(home):
        try:
            Path(home).lstat()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        return False

    def _capacity_absence_proofs(self, facts):
        row = facts["attempt"]
        current = CodexExecAttempt.model_validate_json(row["status_json"])
        blockers, proofs = [], []
        observed_at = utc_now().isoformat()
        home_absent = self._retired_home_absent(row["project_home"])
        if not home_absent:
            blockers.append("original revoked project home is not positively absent (replacement, symlink or access uncertainty)")
        proofs.append({"role": "project_home", "path": row["project_home"], "absent": home_absent, "observedAt": observed_at})
        owners = [("worker", row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"]),
                  ("cli", current.process_id, current.process_group_id, current.process_birth_identity)]
        validator = facts["validator"]
        if validator is not None:
            if validator["spawn_state"] != "running":
                blockers.append("validator spawn ownership is unresolved")
            owners.append(("validator", validator["process_id"], validator["process_group_id"], validator["process_birth_identity"]))
        for role, pid, group, birth in owners:
            absent = bool(pid and group == pid and birth and self._prove_group_absent(pid, group, birth))
            proofs.append({"role": role, "pid": pid, "processGroupId": group, "birthIdentity": birth,
                           "pidAndWholeGroupAbsent": absent, "observedAt": observed_at})
            if not absent:
                blockers.append(f"{role} PID and whole process group are not positively absent")
        return blockers, proofs

    def _capacity_retirement_context(self, connection, request):
        facts = self._capacity_retirement_facts(connection, request)
        current = CodexExecAttempt.model_validate_json(facts["attempt"]["status_json"])
        budget = {"image_budget_state": current.image_budget_state, "reserved_image_outputs": current.reserved_image_outputs}
        prior = connection.execute("SELECT * FROM exec_capacity_retirements WHERE attempt_id=?", (str(request.attempt_id),)).fetchone()
        if prior is not None:
            raw = json.loads(prior["receipt_json"])
            receipt = CapacityRetirementReceipt.model_validate(raw)
            retained = receipt.retained_facts
            if (stable_hash(raw) != prior["receipt_hash"] or str(receipt.project_id) != str(request.project_id)
                    or str(receipt.attempt_id) != str(request.attempt_id)
                    or stable_hash(retained) != receipt.preview_hash
                    or {key: value for key, value in facts.items() if key != "slot"}
                    != {key: value for key, value in retained.items() if key != "slot"}
                    or facts["slot"] is not None):
                raise CodexExecSupervisorError("retirement facts changed or a retired slot was restored")
            # An exact readback returns the original observation, never claims
            # fresh absence for numeric PIDs that may have been reused later.
            if not self._retired_home_absent(facts["attempt"]["project_home"]):
                raise CodexExecSupervisorError("retired project home was restored or its absence is uncertain")
            return CapacityRetirementPreview(project_id=request.project_id, attempt_id=request.attempt_id,
                preview_hash=receipt.preview_hash, eligible=True, blockers=[], local_capacity_state="retired",
                already_retired=True, receipt=receipt, **budget), facts, []
        blockers, proofs = self._capacity_absence_proofs(facts)
        if facts["slot"] is None or facts["slot"]["domain"] != "image":
            blockers.append("the exact original image capacity slot is missing or changed")
        if facts["queue"] is not None and facts["queue"]["enabled"] != 0:
            blockers.append("revoked queue authorization is not disabled")
        return CapacityRetirementPreview(project_id=request.project_id, attempt_id=request.attempt_id,
            preview_hash=stable_hash(facts), eligible=not blockers, blockers=blockers, local_capacity_state="held", **budget), facts, proofs

    def capacity_retirement_preview(self, raw_request):
        request = CapacityRetirementRequest.model_validate(raw_request)
        with closing(self._connect()) as connection:
            context, _facts, _proofs = self._capacity_retirement_context(connection, request)
            return context

    def retire_local_capacity(self, raw_request):
        request = CapacityRetirementRequest.model_validate(raw_request)
        if request.expected_preview_hash is None or not request.reason:
            raise CodexExecSupervisorError("capacity retirement requires exact preview consent and an operator reason")
        with self._guard, self._abandonment_fence(request.project_id), closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                context, facts, proofs = self._capacity_retirement_context(connection, request)
                if context.preview_hash != request.expected_preview_hash:
                    raise CodexExecSupervisorError("capacity retirement preview changed; inspect again")
                if not context.eligible:
                    raise CodexExecSupervisorError("; ".join(context.blockers))
                if context.already_retired:
                    if context.receipt.reason != request.reason:
                        raise CodexExecSupervisorError("retained capacity retirement reason differs")
                    connection.commit()
                    return context
                # Recheck positive OS absence immediately at the mutation fence.
                blockers, proofs = self._capacity_absence_proofs(facts)
                if blockers:
                    raise CodexExecSupervisorError("; ".join(blockers))
                receipt = CapacityRetirementReceipt(id=new_id(), project_id=request.project_id,
                    attempt_id=request.attempt_id, preview_hash=context.preview_hash, reason=request.reason,
                    created_at=utc_now(), retained_facts=facts, absence_proofs=proofs,
                    maintenance_source_root=str(self.source_root), maintenance_code_hash=sha256(Path(__file__).read_bytes()).hexdigest())
                raw = receipt.model_dump(mode="json", by_alias=True)
                connection.execute("INSERT INTO exec_capacity_retirements VALUES (?,?,?)",
                    (str(request.attempt_id), json.dumps(raw, sort_keys=True, separators=(",", ":")), stable_hash(raw)))
                self._retire_exact_slot_in_transaction(connection, request.attempt_id)
                connection.commit()
                return context.model_copy(update={"already_retired": True, "local_capacity_state": "retired", "receipt": receipt})
            except BaseException:
                connection.rollback()
                raise

    @staticmethod
    def _retire_exact_slot_in_transaction(connection, attempt_id):
        cursor = connection.execute("DELETE FROM exec_slot WHERE attempt_id=? AND domain='image'", (str(attempt_id),))
        if cursor.rowcount != 1:
            raise CodexExecSupervisorError("exact capacity slot changed during retirement")
