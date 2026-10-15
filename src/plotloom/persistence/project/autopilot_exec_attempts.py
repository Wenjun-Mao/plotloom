"""Immutable CLI job reservations and receipt settlement in the run owner."""
from sqlalchemy import and_, func, or_, select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, OperationScope
from ...codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
    transition_exec_attempt,
)
from ...domain import utc_now
from ...exceptions import InvalidTransitionError
from ..schema import AutopilotCheckpointRow, AutopilotExecAttemptRow


class AutopilotExecPersistence:
    def exec_attempt_for_operation(self, run_id, operation_key):
        with self.access.leases.read() as session:
            row = session.scalar(select(AutopilotExecAttemptRow).where(
                AutopilotExecAttemptRow.run_id == run_id,
                AutopilotExecAttemptRow.operation_key == operation_key,
            ))
            return CodexExecAttempt.model_validate(row.snapshot) if row is not None else None

    def exec_attempt_evidence_for_operation(self, run_id, operation_key):
        """Return the current typed attempt and its immutable successful receipt."""
        with self.access.leases.read() as session:
            row = session.scalar(select(AutopilotExecAttemptRow).where(
                AutopilotExecAttemptRow.run_id == run_id,
                AutopilotExecAttemptRow.operation_key == operation_key,
            ))
            if row is None:
                return None, None
            attempt = CodexExecAttempt.model_validate(row.snapshot)
            receipt = CodexExecReceipt.model_validate(row.receipt) if row.receipt is not None else None
            return attempt, receipt

    def reserve_exec_attempt(self, attempt: CodexExecAttempt, *, expected_checkpoint_revision: int):
        """Atomically bind one immutable job to its project attempt and image budget."""
        authority = self.access.authority()
        if authority is None:
            raise InvalidTransitionError("CLI attempt reservation requires exact text or image machine authority")
        if attempt.state != "reserved":
            raise InvalidTransitionError("new project attempts must begin reserved")
        expected_scope = (
            OperationScope.IMAGE if attempt.domain == "image"
            else OperationScope.INSTALL if attempt.operation_key in {"bridge-intent", "bridge-presentation"}
            else OperationScope.TEXT
        )
        if authority.scope != expected_scope:
            raise InvalidTransitionError("CLI attempt domain does not match its machine scope")
        with self.access.leases.lifecycle_write() as session:
            run = self.validate_command(session, authority)
            policy = LaunchPolicy.model_validate(run.policy)
            if policy.version != "plotloom.pre-video.v4" or policy.executor_binding is None:
                raise InvalidTransitionError("only a frozen CLI executor launch can reserve this attempt")
            if attempt.profile_hash != policy.executor_binding.profile_hash:
                raise InvalidTransitionError("CLI attempt profile differs from its frozen launch")
            if (policy.executor_binding.contract_version in {"plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
                    and attempt.plotloom_code_revision != policy.code_revision):
                raise InvalidTransitionError("CLI attempt Plotloom source revision differs from its frozen launch")
            if (policy.executor_binding.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
                    and attempt.domain == "text" and attempt.validation_plan_hash is None):
                raise InvalidTransitionError("fresh text CLI attempts require their frozen trusted validation plan")
            if str(attempt.run_id) != run.id or str(attempt.project_id) != run.project_id:
                raise InvalidTransitionError("CLI attempt belongs to another frozen project run")
            checkpoint = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id,
                AutopilotCheckpointRow.operation_key == attempt.operation_key,
            ))
            if checkpoint is None or checkpoint.state != "prepared":
                raise InvalidTransitionError("CLI reservation requires its exact prepared stage checkpoint")
            evidence = CheckpointEvidence.model_validate(checkpoint.evidence)
            if (evidence.job_id != attempt.job_id or evidence.request_hash != attempt.request_hash
                    or evidence.executor_attempt_id is not None):
                raise InvalidTransitionError("CLI attempt does not match the unattempted frozen job")

            existing = session.scalar(select(AutopilotExecAttemptRow).where(
                or_(AutopilotExecAttemptRow.id == str(attempt.attempt_id),
                    and_(AutopilotExecAttemptRow.run_id == run.id,
                         AutopilotExecAttemptRow.operation_key == attempt.operation_key))
            ))
            job_owner = session.scalar(select(AutopilotExecAttemptRow).where(
                AutopilotExecAttemptRow.project_id == run.project_id,
                AutopilotExecAttemptRow.job_id == attempt.job_id,
            ))
            if existing is not None or job_owner is not None:
                if (existing is not None and existing.id == str(attempt.attempt_id)
                        and existing.run_id == run.id and existing.project_id == run.project_id
                        and existing.operation_key == attempt.operation_key and existing.job_id == attempt.job_id
                        and CodexExecAttempt.model_validate(existing.snapshot).model_dump(mode="json", by_alias=True)
                            == attempt.model_dump(mode="json", by_alias=True)):
                    return CodexExecAttempt.model_validate(existing.snapshot)
                raise InvalidTransitionError("a frozen CLI job already owns its one initial attempt")

            if attempt.domain == "image":
                reserved = session.scalar(select(func.coalesce(func.sum(AutopilotExecAttemptRow.reserved_image_outputs), 0)).where(
                    AutopilotExecAttemptRow.run_id == run.id,
                    AutopilotExecAttemptRow.domain == "image",
                    AutopilotExecAttemptRow.image_budget_state.in_({"reserved", "consumed"}),
                )) or 0
                if reserved + attempt.reserved_image_outputs > policy.max_images:
                    raise InvalidTransitionError("CLI image reservation exceeds the frozen run image budget")
            pending = session.scalar(select(AutopilotExecAttemptRow.id).join(
                AutopilotCheckpointRow,
                and_(AutopilotCheckpointRow.run_id == AutopilotExecAttemptRow.run_id,
                     AutopilotCheckpointRow.operation_key == AutopilotExecAttemptRow.operation_key),
            ).where(
                AutopilotExecAttemptRow.run_id == run.id,
                AutopilotExecAttemptRow.domain == "text",
                AutopilotCheckpointRow.state != "adopted",
            ).limit(1))
            if attempt.domain == "text" and pending is not None:
                raise InvalidTransitionError("dependent text execution cannot pass an unadopted text attempt")

            checkpoint_evidence = CheckpointEvidence.model_validate(
                evidence.model_dump(mode="python") | {"executor_attempt_id": attempt.attempt_id}
            )
            from .autopilot_bindings import assert_checkpoint_binding
            from .autopilot_checkpoints import assert_checkpoint_update
            assert_checkpoint_update(checkpoint, expected_checkpoint_revision, "prepared", checkpoint_evidence)
            now = utc_now()
            row = AutopilotExecAttemptRow(id=str(attempt.attempt_id), run_id=run.id, project_id=run.project_id,
                operation_key=attempt.operation_key, job_id=attempt.job_id, domain=attempt.domain, state=attempt.state,
                image_budget_state=attempt.image_budget_state, reserved_image_outputs=attempt.reserved_image_outputs,
                revision=1, snapshot=attempt.model_dump(mode="json", by_alias=True), created_at=now, updated_at=now)
            session.add(row)
            session.flush()
            try:
                assert_checkpoint_binding(session.connection().connection.driver_connection, run.project_id,
                    "prepared", checkpoint_evidence, run_id=run.id, operation_key=attempt.operation_key)
            except (ValueError, TypeError, KeyError) as error:
                raise InvalidTransitionError(str(error)) from error
            checkpoint.evidence = checkpoint_evidence.model_dump(mode="json", by_alias=True)
            checkpoint.revision += 1
            checkpoint.updated_at = now
            session.flush()
            return attempt

    def mark_exec_spawn_intent(self, attempt_id, *, expected_checkpoint_revision: int):
        return self._mark_exec_spawn_intent(attempt_id,
            expected_checkpoint_revision=expected_checkpoint_revision)

    def consume_reserved_exec_attempt_once(self, expected_attempt: CodexExecAttempt, *,
            expected_checkpoint_revision: int, expected_run_revision: int):
        """Spend one exact reservation atomically; never recover an old intent."""
        if expected_attempt.state != "reserved":
            raise InvalidTransitionError("strict CLI consumption requires a reserved snapshot")
        return self._mark_exec_spawn_intent(expected_attempt.attempt_id,
            expected_checkpoint_revision=expected_checkpoint_revision,
            expected_attempt=expected_attempt, expected_run_revision=expected_run_revision)

    def _mark_exec_spawn_intent(self, attempt_id, *, expected_checkpoint_revision,
            expected_attempt=None, expected_run_revision=None):
        authority = self.access.authority()
        if authority is None:
            raise InvalidTransitionError("CLI spawn intent requires exact text or image machine authority")
        with self.access.leases.lifecycle_write() as session:
            run = self.validate_command(session, authority)
            row = session.get(AutopilotExecAttemptRow, str(attempt_id))
            if row is None or row.run_id != run.id or row.project_id != run.project_id:
                raise InvalidTransitionError("CLI attempt identity is not owned by this project run")
            attempt = CodexExecAttempt.model_validate(row.snapshot)
            if expected_attempt is not None:
                if run.revision != expected_run_revision:
                    raise InvalidTransitionError("strict CLI consumption run revision changed")
                if attempt != expected_attempt or attempt.state != "reserved":
                    raise InvalidTransitionError("strict CLI reservation changed or was already spent")
            expected_scope = (
                OperationScope.IMAGE if attempt.domain == "image"
                else OperationScope.INSTALL if attempt.operation_key in {"bridge-intent", "bridge-presentation"}
                else OperationScope.TEXT
            )
            if authority.scope != expected_scope:
                raise InvalidTransitionError("CLI attempt scope changed before spawn intent")
            if attempt.state == "spawn_intent":
                return attempt
            if attempt.state != "reserved":
                raise InvalidTransitionError("only an unused project reservation can enter spawn intent")
            updated = transition_exec_attempt(attempt, state="spawn_intent")
            checkpoint = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id,
                AutopilotCheckpointRow.operation_key == attempt.operation_key,
            ))
            evidence = CheckpointEvidence.model_validate(checkpoint.evidence)
            if evidence.executor_attempt_id != attempt.attempt_id:
                raise InvalidTransitionError("stage checkpoint lost its exact CLI attempt binding")
            next_evidence = CheckpointEvidence.model_validate(
                evidence.model_dump(mode="python") | {"result": evidence.result | {"dispatchAttempted": True}}
            )
            from .autopilot_bindings import assert_checkpoint_binding
            from .autopilot_checkpoints import assert_checkpoint_update
            assert_checkpoint_update(checkpoint, expected_checkpoint_revision, "sent", next_evidence)
            now = utc_now()
            row.state = updated.state
            row.revision += 1
            row.snapshot = updated.model_dump(mode="json", by_alias=True)
            row.updated_at = now
            checkpoint.state = "sent"
            checkpoint.evidence = next_evidence.model_dump(mode="json", by_alias=True)
            checkpoint.revision += 1
            checkpoint.updated_at = now
            session.flush()
            try:
                assert_checkpoint_binding(session.connection().connection.driver_connection, run.project_id,
                    "sent", next_evidence, run_id=run.id, operation_key=attempt.operation_key)
            except (ValueError, TypeError, KeyError) as error:
                raise InvalidTransitionError(str(error)) from error
            return updated

    def update_exec_attempt(self, attempt_id, *, receipt: CodexExecReceipt | None = None, **changes):
        """Reconcile host-owned facts without restoring dispatch authority."""
        authority = self.access.authority()
        if authority is None or authority.scope != OperationScope.EVIDENCE:
            raise InvalidTransitionError("CLI attempt reconciliation requires receipt-only authority")
        with self.access.leases.lifecycle_write() as session:
            run = self.validate_command(session, authority)
            row = session.get(AutopilotExecAttemptRow, str(attempt_id))
            if row is None or row.run_id != run.id or row.project_id != run.project_id:
                raise InvalidTransitionError("CLI attempt identity is not owned by this project run")
            attempt = CodexExecAttempt.model_validate(row.snapshot)
            updated = transition_exec_attempt(attempt, **changes)
            parsed_receipt = CodexExecReceipt.model_validate(receipt) if receipt is not None else None
            existing_receipt = CodexExecReceipt.model_validate(row.receipt) if row.receipt is not None else None
            if parsed_receipt is not None:
                assert_receipt_matches_attempt(updated, parsed_receipt)
                if existing_receipt is not None and existing_receipt != parsed_receipt:
                    raise InvalidTransitionError("a settled CLI receipt cannot be replaced")
            if existing_receipt is not None and not (
                updated.state in {"completed", "settled"} and updated.terminal_result == "success"
            ):
                raise InvalidTransitionError("a successful CLI receipt cannot be detached from its terminal attempt")
            if updated.state in {"completed", "settled"} and updated.terminal_result == "success" and parsed_receipt is None:
                if existing_receipt is None:
                    raise InvalidTransitionError("successful CLI attempts require their typed receipt")
                assert_receipt_matches_attempt(updated, existing_receipt)
            if updated == attempt and parsed_receipt == existing_receipt:
                return attempt
            checkpoint = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id,
                AutopilotCheckpointRow.operation_key == attempt.operation_key,
            ))
            evidence = CheckpointEvidence.model_validate(checkpoint.evidence)
            if evidence.executor_attempt_id != attempt.attempt_id:
                raise InvalidTransitionError("stage checkpoint lost its exact CLI attempt binding")
            checkpoint_state = checkpoint.state
            receipt_hash = updated.evidence_hash if updated.state in {"completed", "failed", "settled"} else None
            if (checkpoint_state in {"prepared", "sent", "outcome_unknown"}
                    and updated.state in {"failed", "settled"}
                    and updated.terminal_result in {"failure", "not_started"}):
                checkpoint_state = "failed"
            elif checkpoint_state == "sent" and updated.state == "outcome_unknown":
                checkpoint_state = "outcome_unknown"
            evidence_update = {"executor_receipt_hash": receipt_hash}
            if updated.state == "outcome_unknown":
                evidence_update["result"] = evidence.result | {"dispatchOutcomeUnknown": True}
            next_evidence = CheckpointEvidence.model_validate(
                evidence.model_dump(mode="python") | evidence_update
            )
            from .autopilot_bindings import assert_checkpoint_binding
            from .autopilot_checkpoints import assert_checkpoint_update
            assert_checkpoint_update(checkpoint, checkpoint.revision, checkpoint_state, next_evidence)
            now = utc_now()
            row.state = updated.state
            row.image_budget_state = updated.image_budget_state
            row.revision += 1
            row.snapshot = updated.model_dump(mode="json", by_alias=True)
            if parsed_receipt is not None:
                row.receipt = parsed_receipt.model_dump(mode="json", by_alias=True)
            row.updated_at = now
            checkpoint.state = checkpoint_state
            checkpoint.evidence = next_evidence.model_dump(mode="json", by_alias=True)
            checkpoint.revision += 1
            checkpoint.updated_at = now
            session.flush()
            try:
                assert_checkpoint_binding(session.connection().connection.driver_connection, run.project_id,
                    checkpoint_state, next_evidence, run_id=run.id, operation_key=attempt.operation_key)
            except (ValueError, TypeError, KeyError) as error:
                raise InvalidTransitionError(str(error)) from error
            return updated
