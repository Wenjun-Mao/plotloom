"""New future authority with exact, validated historical material origins."""
from sqlalchemy import select

from ...provider_budgets import exceeds_budget
from ...autopilot_contracts import POLICY_VERSION, CheckpointEvidence, LaunchPolicy
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..codec import stable_hash
from ..schema import (
    AutopilotCheckpointRow,
    AutopilotExecAttemptRow,
    AutopilotFrameRow,
    AutopilotInheritanceRow,
    AutopilotRunRow,
)
from .autopilot_closure import material_closure


def project_job_counts(session, project_id):
    checkpoints = session.scalars(select(AutopilotCheckpointRow).where(
        AutopilotCheckpointRow.project_id == project_id)).all()
    jobs = {row.evidence["jobId"] for row in checkpoints if row.evidence.get("jobId")}
    images = {row.evidence["jobId"] for row in checkpoints if row.evidence.get("jobId")
              and row.evidence["owner"] in {"image", "character-reference", "art-reference"}}
    return len(jobs), len(images)


def continuation_preview(owner, session, project_id):
    run = owner.row(session, project_id)
    if run is None:
        raise InvalidTransitionError("项目没有可继续的自动素材运行。")
    closure = material_closure(session, project_id)
    blockers = []
    if run.state != "cancelled":
        blockers.append("请先明确取消原自动运行，再授权新的剩余素材工作。")
    if run.id in owner.recovered_run_ids():
        blockers.append("恢复副本不能继承原主机的自动执行权限。")
    if run.expected_closure != closure:
        blockers.append("当前素材与原运行不一致；请先检查手动修改，不能自动覆盖。")
    checkpoints = session.scalars(select(AutopilotCheckpointRow).where(
        AutopilotCheckpointRow.run_id == run.id)).all()
    reusable = [row for row in checkpoints if row.state == "adopted"]
    for checkpoint in checkpoints:
        if checkpoint.state == "adopted":
            continue
        attempt = session.scalar(select(AutopilotExecAttemptRow).where(
            AutopilotExecAttemptRow.run_id == run.id,
            AutopilotExecAttemptRow.operation_key == checkpoint.operation_key))
        if attempt is not None and attempt.state in {"failed", "settled"} and attempt.snapshot.get("terminalResult") in {"failure", "not_started", "no_remote_dispatch"}:
            continue
        blockers.append(f"原任务 {checkpoint.evidence.get('jobId', checkpoint.operation_key)} 尚未完成采用；"
                        "请保留并核对原交付/终止证据，不会重复发送。")
    jobs, images = project_job_counts(session, project_id)
    return {"runId": run.id, "runRevision": run.revision, "materialClosure": closure,
            "eligible": not blockers, "blockers": blockers, "inheritedOperations": len(reusable),
            "lifetimeJobs": jobs, "lifetimeImages": images}


class AutopilotContinuationPersistence:
    def continuation_context(self, project_id):
        with self.access.leases.read() as session:
            return continuation_preview(self, session, project_id)

    def continue_material(self, project_id, *, request, policy):
        with self.access.leases.lifecycle_write() as session:
            project = self.access.rows.project(session, project_id)
            self.access.guards.active(project)
            context = continuation_preview(self, session, project_id)
            parent = self.row(session, project_id)
            if parent.id != request.expected_run_id:
                raise InvalidTransitionError("原运行身份已变化；请重新核对继续条件，不能重用祖先运行的确认。")
            if parent.revision != request.expected_run_revision:
                raise RevisionConflictError("autopilot", request.expected_run_revision, parent.revision)
            if context["materialClosure"] != request.expected_material_closure:
                raise InvalidTransitionError("素材已变化；请重新核对继续条件。")
            if project.revision != request.expected_brief_revision:
                raise RevisionConflictError("Brief", request.expected_brief_revision, project.revision)
            if not context["eligible"]:
                raise InvalidTransitionError("；".join(context["blockers"]))
            if policy.version != POLICY_VERSION or policy.brief != project.brief:
                raise InvalidTransitionError("继续必须绑定当前已保存简报和新的冻结执行权限。")
            if exceeds_budget(context["lifetimeJobs"] + 1, policy.max_jobs) or exceeds_budget(context["lifetimeImages"], policy.max_images):
                raise InvalidTransitionError("新的项目总上限必须涵盖原任务和剩余素材。")
            previous_policy = LaunchPolicy.model_validate(parent.policy)
            if (policy.image_width, policy.image_height, policy.effective_style_authority,
                policy.render_style, policy.art_render_style) != (
                previous_policy.image_width, previous_policy.image_height, previous_policy.effective_style_authority,
                previous_policy.render_style, previous_policy.art_render_style):
                raise InvalidTransitionError("继续保留原素材画风和画幅；不能隐式改变已完成素材。")
            now = utc_now()
            frozen = policy.model_dump(mode="json", by_alias=True)
            child = AutopilotRunRow(id=new_id(), project_id=project_id, predecessor_run_id=parent.id,
                revision=1, lifecycle_revision=project.lifecycle_revision, brief_revision=project.revision,
                brief_hash=stable_hash(project.brief), policy=frozen, policy_hash=stable_hash(frozen),
                state="running", phase=parent.phase, claim=None, expected_closure=context["materialClosure"],
                blocker=None, bundle=None, bundle_hash=None, handoff=None, created_at=now, updated_at=now)
            session.add(child)
            session.flush()
            from .autopilot_bindings import assert_retained_checkpoint_provenance
            for original in session.scalars(select(AutopilotCheckpointRow).where(
                    AutopilotCheckpointRow.run_id == parent.id, AutopilotCheckpointRow.state == "adopted")).all():
                assert_retained_checkpoint_provenance(session.connection().connection.driver_connection,
                    project_id, original.state, CheckpointEvidence.model_validate(original.evidence),
                    run_id=parent.id, operation_key=original.operation_key)
                session.add(AutopilotInheritanceRow(id=new_id(), project_id=project_id, run_id=child.id,
                    operation_key=original.operation_key, origin_checkpoint_id=original.id,
                    evidence_hash=stable_hash(original.evidence)))
                session.add(AutopilotCheckpointRow(id=new_id(), project_id=project_id, run_id=child.id,
                    operation_key=original.operation_key, revision=1, state="adopted", evidence=original.evidence,
                    created_at=now, updated_at=now))
            for original in session.scalars(select(AutopilotFrameRow).where(AutopilotFrameRow.run_id == parent.id)).all():
                session.add(AutopilotFrameRow(id=new_id(), run_id=child.id, project_id=project_id,
                    shot_id=original.shot_id, job_id=original.job_id, asset_id=original.asset_id,
                    decision_id=original.decision_id, frame=original.frame, created_at=now))
            session.flush()
            child.expected_closure = material_closure(session, project_id)
            return self.view_in_session(session, child)


def inherited_origin(connection, run_id, operation_key, evidence, *, visited=()):
    if run_id in visited:
        raise ValueError("cyclic autopilot inheritance")
    link = connection.execute("SELECT origin_checkpoint_id,evidence_hash,project_id FROM v2_autopilot_inheritance "
        "WHERE run_id=? AND operation_key=?", (run_id, operation_key)).fetchone()
    if link is None:
        return None
    original = connection.execute("SELECT run_id,project_id,operation_key,state,evidence FROM v2_autopilot_checkpoints WHERE id=?", (link[0],)).fetchone()
    parent = connection.execute("SELECT predecessor_run_id,project_id FROM v2_autopilot_runs WHERE id=?", (run_id,)).fetchone()
    import json
    if (original is None or parent is None or original[:4] != (parent[0], parent[1], operation_key, "adopted")
            or link[2] != parent[1] or stable_hash(json.loads(original[4])) != link[1]
            or stable_hash(evidence.model_dump(mode="json", by_alias=True)) != link[1]):
        raise ValueError("inherited checkpoint differs from exact adopted predecessor evidence")
    ancestor = inherited_origin(connection, original[0], operation_key, evidence, visited=(*visited, run_id))
    return ancestor or original[0]


def assert_continuation_lineage(connection):
    from .autopilot_lineage import current_run_id
    projects = {}
    for identifier, project, parent in connection.execute("SELECT id,project_id,predecessor_run_id FROM v2_autopilot_runs"):
        projects.setdefault(project, []).append((identifier, parent))
    for links in projects.values():
        current_run_id(links)
    for run_id, project, key in connection.execute("SELECT run_id,project_id,operation_key FROM v2_autopilot_inheritance"):
        child = connection.execute("SELECT state,evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND project_id=? AND operation_key=?", (run_id, project, key)).fetchone()
        if child is None or child[0] != "adopted":
            raise ValueError("inheritance has no exact adopted successor checkpoint")
        inherited_origin(connection, run_id, key, CheckpointEvidence.model_validate_json(child[1]))
