"""One durable admitted run; existing stage/media owners remain authoritative."""
from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, MachineDecision, OperationScope, ProvisionalFrame, RunView, POLICY_VERSION
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..codec import stable_hash
from ..schema import AutopilotCheckpointRow, AutopilotDecisionRow, AutopilotFrameRow, AutopilotRunRow
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
                assert_checkpoint_binding(session.connection().connection.driver_connection, run.project_id, state, evidence, run_id=run.id)
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
