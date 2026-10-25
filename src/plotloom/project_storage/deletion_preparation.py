"""Passive deletion choices and exact-scope admission for an explicit local stop."""
from contextlib import closing

from ..exceptions import InvalidTransitionError
from ..persistence.codec import stable_hash
from ..persistence.project.autopilot_closure import material_closure
from .abandonment import _context
from .operational_state import close_blockers

STOPPED = {"cancelled", "taken_over", "stale", "handed_off"}


def explain_blocker(blocker):
    for code, explanation in (
        ("local process identity is unresolved", "本地任务进程身份未确认；请核对原自动任务，不能推断其已经结束"),
        ("local process group is not proven absent", "本地任务进程仍存在或未确认退出；请核对原任务结束状态后重新删除"),
        ("validator ownership is unresolved", "验证进程的归属或退出状态未确认；请核对原任务后重新删除"),
        ("native_specialist_execution_unresolved", "其他原生助手任务尚未确认结束；请先核对该项目的原生任务记录"),
    ):
        if code in blocker:
            return f"{explanation}（{blocker}）"
    return blocker


def deletion_scope(store):
    """Cancellation may change transport state, never the consented material/work set."""
    project_id = store.manifest.project_id
    with store.repository._read() as session:
        material = material_closure(session, project_id, include_cancellations=False)
        work = {}
        for table, key in (
            ("v2_autopilot_runs", "id"), ("v2_autopilot_exec_attempts", "id"),
            ("v2_generation_runs", "id"), ("v2_media_tasks", "id"),
            ("v2_video_jobs", "id"), ("v2_video_batches", "id"),
            ("v2_image_jobs", "id"), ("v2_character_reference_proposals", "id"),
            ("v2_art_reference_proposals", "id"), ("v2_production_bridge_intent_jobs", "id"),
            *((table, "job_id") for table in ("v2_source_outline_candidates", "v2_cast_candidates",
                "v2_art_candidates", "v2_script_candidates", "v2_storyboard_review_candidates")),
        ):
            work[table] = sorted(row[0] for row in session.connection().exec_driver_sql(
                f"SELECT {key} FROM {table} WHERE project_id=?", (project_id,)))
    inode = store.home.stat()
    return stable_hash({"material": material, "work": work,
        "home": [inode.st_dev, inode.st_ino]})


def prepare_deletion(registry, project_id, native):
    with closing(registry.inspect(project_id, passive=True)) as store:
        project = store.project()
        scope = deletion_scope(store)
        with store.repository._read() as session:
            run = store.repository.autopilot.row(session, project_id)
            active = {"id": run.id, "revision": run.revision, "state": run.state} if run and run.state not in STOPPED else None
            retained_attempts = session.connection().exec_driver_sql(
                "SELECT 1 FROM v2_autopilot_exec_attempts WHERE project_id=? LIMIT 1", (project_id,)).first() is not None
        blockers = close_blockers(store) + registry.native_blockers(store)
        base = {"projectId": project_id, "expectedProjectRevision": project.revision,
            "expectedLifecycleRevision": project.lifecycle_revision, "confirmationTitle": store.display_title(),
            "scopeHash": scope, "run": active, "unknownAttemptIds": [], "blockers": [], "mode": "ordinary"}
        if not active and not blockers and not retained_attempts:
            return base
        # Automatic publication is handled only by the existing exact-host contract.
        context = _context(registry, project_id, native, preparing_stop=True)[2]
        if active and context["activeRuns"] != [active]:
            context["stopBlockers"].append("存在其他尚未停止的自动运行；请逐一核对，不能合并停止。")
        base.update(unknownAttemptIds=context["unknownAttemptIds"], previewHash=context["previewHash"])
        blockers = context["stopBlockers"] if active else context["blockers"]
        if blockers:
            return base | {"mode": "blocked", "blockers": [explain_blocker(item) for item in blockers]}
        if active:
            if project.lifecycle_status.value != "active" or store.repository.operational_state()[0] != "open":
                return base | {"mode": "blocked", "blockers": ["自动运行尚未停止，但项目已归档或冻结；请先恢复归档或解除冻结，再明确停止自动运行。"]}
            return base | {"mode": "stop", "stopWarnings": [explain_blocker(item) for item in context["hostBlockers"]]}
        if context["attemptIds"]:
            return base | {"mode": "abandon"}
        return base | {"mode": "blocked", "blockers": [f"项目占用：{item}；请在相应任务中核对并结束。" for item in blockers]}


def assert_deletion_scope(store, request):
    project = store.project()
    if (project.revision != request.expected_project_revision
            or project.lifecycle_revision != request.expected_lifecycle_revision
            or store.display_title() != request.confirmation_title
            or deletion_scope(store) != request.scope_hash):
        raise InvalidTransitionError("项目内容或任务范围已改变；未继续删除，请重新核对。")
