"""One durable admitted run; existing stage/media owners remain authoritative."""
from sqlalchemy import and_, func, or_, select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, MachineDecision, OperationScope, ProvisionalFrame, RunView, POLICY_VERSION
from ...codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
    transition_exec_attempt,
)
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..codec import stable_hash
from ..schema import AutopilotCheckpointRow, AutopilotDecisionRow, AutopilotExecAttemptRow, AutopilotFrameRow, AutopilotRunRow
from .autopilot_closure import material_closure

from .autopilot_freshness import assert_fresh


class AutopilotPersistence:
    def __init__(self, access):
        self.access = access
        self.recovered_run_ids = lambda: set()

    @staticmethod
    def row(session, project_id):
        return session.scalar(select(AutopilotRunRow).where(AutopilotRunRow.project_id == project_id))

    def start(self, project_id, *, expected_brief_revision, policy: LaunchPolicy):
        if policy.version != POLICY_VERSION:
            raise InvalidTransitionError("new runs require the current frozen launch policy")
        with self.access.leases.lifecycle_write() as session:
            project = self.access.rows.project(session, project_id)
            self.access.guards.active(project)
            existing = self.row(session, project_id)
            if existing is not None:
                return self.view_in_session(session, existing)
            if project.revision != expected_brief_revision:
                raise RevisionConflictError("Brief", expected_brief_revision, project.revision)
            if policy.brief != project.brief:
                raise InvalidTransitionError("launch policy must bind the exact saved Brief")
            assert_fresh(session, project_id)
            frozen = policy.model_dump(mode="json", by_alias=True)
            now = utc_now()
            row = AutopilotRunRow(id=new_id(), project_id=project_id, revision=1,
                lifecycle_revision=project.lifecycle_revision, brief_revision=project.revision,
                brief_hash=stable_hash(project.brief), policy=frozen, policy_hash=stable_hash(frozen),
                state="running", phase="source", claim=None, expected_closure=material_closure(session, project_id),
                blocker=None, bundle=None, bundle_hash=None, handoff=None, created_at=now, updated_at=now)
            session.add(row)
            session.flush()
            return self.view_in_session(session, row)

    def current(self, project_id):
        with self.access.leases.read() as session:
            row = self.row(session, project_id)
            return self.view_in_session(session, row) if row else None

    def controller_execution_eligible(self, project_id):
        """Admission follows durable terminal state, independently of UI currentness."""
        with self.access.leases.read() as session:
            row = self.row(session, project_id)
            return row is not None and row.state != "handed_off" and row.id not in self.recovered_run_ids()

    def view_in_session(self, session, row):
        checkpoints = session.scalars(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == row.id)
            .order_by(AutopilotCheckpointRow.created_at, AutopilotCheckpointRow.operation_key)).all()
        frames = session.scalars(select(AutopilotFrameRow).where(AutopilotFrameRow.run_id == row.id).order_by(AutopilotFrameRow.shot_id)).all()
        stale = row.expected_closure != material_closure(session, row.project_id)
        return RunView(id=row.id, project_id=row.project_id, revision=row.revision,
            state="stale" if stale and row.state not in {"cancelled", "taken_over", "stale"} else row.state,
            phase=row.phase, policy=LaunchPolicy.model_validate(row.policy),
            blocker={"code": "material_changed", "message": "项目素材已改变，请接管并继续手动编辑。"} if stale else row.blocker,
            checkpoints=[{"id": item.id, "operationKey": item.operation_key, "revision": item.revision,
                "state": item.state, "evidence": CheckpointEvidence.model_validate(item.evidence).model_dump(mode="json", by_alias=True)} for item in checkpoints],
            frames=[ProvisionalFrame.model_validate(item.frame) for item in frames],
            bundle=row.bundle, bundle_hash=row.bundle_hash, handoff=row.handoff, created_at=row.created_at, updated_at=row.updated_at)

    def control(self, project_id, *, expected_revision, action):
        with self.access.leases.lifecycle_write() as session:
            row = self.row(session, project_id)
            if row is None:
                raise InvalidTransitionError("project has no admitted autopilot run")
            if row.revision != expected_revision:
                raise RevisionConflictError("autopilot", expected_revision, row.revision)
            if action == "resume":
                if row.policy.get("version") != POLICY_VERSION:
                    raise InvalidTransitionError("retired frozen policies cannot resume automatic work")
                if row.id in self.recovered_run_ids():
                    raise InvalidTransitionError("portable restored autopilot identities cannot resume native dispatch")
                if row.state not in {"paused", "waiting", "blocked"} or row.expected_closure != material_closure(session, project_id):
                    raise InvalidTransitionError("only an unchanged paused run can resume its original jobs")
                row.state = "running"
            else:
                if row.state in {"cancelled", "handed_off", "taken_over", "stale"}:
                    raise InvalidTransitionError("run is no longer automatically controllable")
                row.state = {"pause": "paused", "cancel": "cancelled", "takeover": "taken_over"}[action]
            row.revision += 1
            row.updated_at = utc_now()
            return self.view_in_session(session, row)

    def claim(self, project_id, claim):
        """Caller must hold the application reconciler's process lease."""
        with self.access.leases.lifecycle_write() as session:
            row = self.row(session, project_id)
            if row is None:
                raise InvalidTransitionError("cannot claim a missing autopilot run")
            if row.id in self.recovered_run_ids():
                raise InvalidTransitionError("portable restored autopilot run cannot acquire a native controller claim")
            if row.state == "handed_off":
                raise InvalidTransitionError("completed human handoff cannot acquire a controller claim")
            if row.claim != claim:
                row.claim = claim
                row.revision += 1
                row.updated_at = utc_now()
            return self.view_in_session(session, row)

    def validate_command(self, session, authority):
        row = session.get(AutopilotRunRow, authority.run_id)
        if row is None or (authority.scope != OperationScope.HANDOFF and row.claim != authority.claim):
            raise InvalidTransitionError("autopilot command claim changed")
        if row.id in self.recovered_run_ids() and authority.scope not in {OperationScope.EVIDENCE, OperationScope.HANDOFF}:
            raise InvalidTransitionError("portable restored autopilot identities cannot dispatch")
        project = self.access.rows.project(session, row.project_id)
        self.access.guards.active(project)
        if authority.scope == OperationScope.HANDOFF:
            if row.state not in {"awaiting_review", "taken_over", "cancelled", "stale", "handed_off"}:
                raise InvalidTransitionError("stop automatic work before reviewing current material")
        elif authority.scope != OperationScope.EVIDENCE:
            if row.state not in {"running", "waiting"} and not (authority.scope == OperationScope.HANDOFF and row.state in {"awaiting_review", "taken_over"}):
                raise InvalidTransitionError("run does not admit a new automatic operation")
            if (row.brief_revision != project.revision or row.lifecycle_revision != project.lifecycle_revision
                    or row.brief_hash != stable_hash(project.brief) or row.expected_closure != material_closure(session, row.project_id)):
                raise InvalidTransitionError("autopilot frozen authority or dependency closure changed")
        policy = LaunchPolicy.model_validate(row.policy)
        if policy.version != POLICY_VERSION and authority.scope not in {OperationScope.EVIDENCE, OperationScope.HANDOFF}:
            raise InvalidTransitionError("retired frozen policies admit only reconciliation or human handoff")
        if row.policy_hash != stable_hash(row.policy):
            raise InvalidTransitionError("autopilot policy hash changed")
        return row

    def checkpoint(self, operation_key, *, state, evidence: CheckpointEvidence, expected_revision=0):
        authority = self.access.authority()
        if authority is None:
            raise InvalidTransitionError("checkpoint requires a trusted run command")
        if evidence.owner == "geometry-preparation" and (authority.scope != OperationScope.GEOMETRY or evidence.geometry_preparation is None
                or evidence.geometry_preparation.claim != authority.claim or evidence.geometry_preparation.run_id != authority.run_id):
            raise InvalidTransitionError("geometry checkpoint requires its exact preparation claim and scope")
        if state == "adopted":
            expected_scope = (OperationScope.SOURCE if evidence.owner == "source"
                else OperationScope.INSTALL if evidence.owner in {"installation", "bridge-proposal", "bridge-intent", "bridge-presentation"}
                else OperationScope.GEOMETRY if evidence.owner == "geometry-preparation"
                else OperationScope.SELECT if evidence.owner in {"bundle", "image", "character-reference", "art-reference"}
                else OperationScope.TEXT)
            if authority.scope != expected_scope:
                raise InvalidTransitionError("checkpoint adoption requires its exact machine scope")
        with self.access.leases.lifecycle_write() as session:
            run = session.get(AutopilotRunRow, authority.run_id)
            checkpoint = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id, AutopilotCheckpointRow.operation_key == operation_key))
            payload = evidence.model_dump(mode="json", by_alias=True)
            from .autopilot_bindings import assert_checkpoint_binding
            from .autopilot_checkpoints import assert_checkpoint_update
            assert_checkpoint_update(checkpoint, expected_revision, state, evidence)
            session.flush()
            try:
                assert_checkpoint_binding(session.connection().connection.driver_connection, run.project_id, state,
                    evidence, run_id=run.id, operation_key=operation_key)
            except (ValueError, TypeError, KeyError) as error:
                raise InvalidTransitionError(str(error)) from error
            now = utc_now()
            if checkpoint is None:
                checkpoint = AutopilotCheckpointRow(id=new_id(), run_id=run.id, project_id=run.project_id,
                    operation_key=operation_key, revision=1, state=state, evidence=payload, created_at=now, updated_at=now)
                session.add(checkpoint)
            else:
                if checkpoint.state != state or checkpoint.evidence != payload:
                    checkpoint.state, checkpoint.evidence = state, payload
                    checkpoint.revision += 1
                    checkpoint.updated_at = now
            session.flush()
            return checkpoint

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
            if (policy.executor_binding.contract_version in {"plotloom.codex-exec.v5", "plotloom.codex-exec.v6"}
                    and attempt.plotloom_code_revision != policy.code_revision):
                raise InvalidTransitionError("CLI attempt Plotloom source revision differs from its frozen launch")
            if (policy.executor_binding.contract_version == "plotloom.codex-exec.v6"
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
                AutopilotCheckpointRow.state != "adopted",
            ).limit(1))
            if pending is not None:
                raise InvalidTransitionError("serial CLI execution cannot pass an unadopted project attempt")

            checkpoint_evidence = CheckpointEvidence.model_validate(
                evidence.model_dump(mode="python") | {"executor_attempt_id": attempt.attempt_id}
            )
            from .autopilot_checkpoints import assert_checkpoint_update
            from .autopilot_bindings import assert_checkpoint_binding
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
        authority = self.access.authority()
        if authority is None:
            raise InvalidTransitionError("CLI spawn intent requires exact text or image machine authority")
        with self.access.leases.lifecycle_write() as session:
            run = self.validate_command(session, authority)
            row = session.get(AutopilotExecAttemptRow, str(attempt_id))
            if row is None or row.run_id != run.id or row.project_id != run.project_id:
                raise InvalidTransitionError("CLI attempt identity is not owned by this project run")
            attempt = CodexExecAttempt.model_validate(row.snapshot)
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
            from .autopilot_checkpoints import assert_checkpoint_update
            from .autopilot_bindings import assert_checkpoint_binding
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
            from .autopilot_checkpoints import assert_checkpoint_update
            from .autopilot_bindings import assert_checkpoint_binding
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

    def decide(self, checkpoint, *, subject, selected_assets=None, rationale):
        authority = self.access.authority()
        if authority is None or authority.scope in {OperationScope.EVIDENCE, OperationScope.HANDOFF}:
            raise InvalidTransitionError("this command cannot grant machine adoption")
        with self.access.leases.lifecycle_write() as session:
            run = session.get(AutopilotRunRow, authority.run_id)
            if checkpoint.run_id != run.id or checkpoint.project_id != run.project_id:
                raise InvalidTransitionError("decision checkpoint belongs to a different run")
            facts = MachineDecision(scope=authority.scope, policy_hash=run.policy_hash, subject=subject,
                upstream_hash=run.expected_closure, evidence=CheckpointEvidence.model_validate(checkpoint.evidence),
                selected_assets=selected_assets or [], rationale=rationale)
            row = AutopilotDecisionRow(id=new_id(), run_id=run.id, project_id=run.project_id,
                checkpoint_id=checkpoint.id, scope=authority.scope.value,
                decision=facts.model_dump(mode="json", by_alias=True), created_at=utc_now())
            session.add(row)
            session.flush()
            return row.id

    def blocker(self, project_id, *, code, message, waiting=False):
        with self.access.leases.lifecycle_write() as session:
            row = self.row(session, project_id)
            if row is None or row.state not in {"running", "waiting"}:
                return
            blocker = {"code": code, "message": message[:2000]}
            state = "waiting" if waiting else "blocked"
            if row.state == state and row.blocker == blocker:
                return
            row.state = state
            row.blocker = blocker
            row.revision += 1
            row.updated_at = utc_now()

    def select_frame(self, frame: ProvisionalFrame, *, decision_id):
        from .autopilot_authority import require_machine_scope
        from .autopilot_bindings import assert_frame_binding
        authority = require_machine_scope(self.access, OperationScope.SELECT)
        with self.access.leases.lifecycle_write() as session:
            run = session.get(AutopilotRunRow, authority.run_id)
            session.flush()
            try:
                assert_frame_binding(session.connection().connection.driver_connection, run.id, run.project_id, decision_id, frame)
            except (ValueError, TypeError, KeyError) as error:
                raise InvalidTransitionError(str(error)) from error
            payload = frame.model_dump(mode="json", by_alias=True)
            existing = session.scalar(select(AutopilotFrameRow).where(AutopilotFrameRow.run_id == run.id, AutopilotFrameRow.shot_id == frame.shot_id))
            if existing is not None:
                if existing.frame != payload or existing.decision_id != decision_id:
                    raise InvalidTransitionError("provisional frame selection is immutable")
                return existing.id
            row = AutopilotFrameRow(id=new_id(), run_id=run.id, project_id=run.project_id,
                shot_id=frame.shot_id, job_id=frame.job_id, asset_id=frame.asset_id, decision_id=decision_id,
                frame=payload, created_at=utc_now())
            session.add(row)
            session.flush()
            return row.id

    def progress(self, phase):
        authority = self.access.authority()
        if authority is None or authority.scope == OperationScope.EVIDENCE:
            raise InvalidTransitionError("receipt reconciliation cannot advance automatic progress")
        with self.access.leases.lifecycle_write() as session:
            row = session.get(AutopilotRunRow, authority.run_id)
            row.phase = phase
            row.blocker = None
            if row.state == "waiting":
                row.state = "running"
