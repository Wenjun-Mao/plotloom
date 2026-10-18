"""Explicit destruction reads exact current/prior layouts without reviving them."""
import json
import sqlite3
from contextlib import closing

from ..codex_exec_contracts import CodexExecAttempt
from ..exceptions import InvalidTransitionError, RevisionConflictError
from ..persistence.codec import stable_hash
from ..project_abandonment_contracts import AbandonmentPacket
from .current_schema import assert_current_review_bindings
from .deletion import remove_owned_home
from .operational_state import ProjectAccessLease, ProjectBusyError
from .schema_upgrade import (
    assert_integrity_identity,
    assert_prior_database,
    classify_layout,
)
from .snapshot_files import _safe_regular


def _context(registry, project_id, native):
    home = registry._project_home(project_id)
    manifest = home.manifest
    _safe_regular(home.path / manifest.database_path, label="abandonment project database")
    with closing(sqlite3.connect(f"{(home.path / manifest.database_path).as_uri()}?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("BEGIN")
        layout = classify_layout(connection)
        if layout == "pre_continuation":
            assert_prior_database(connection, project_id, layout=layout)
        elif layout == "current":
            assert_integrity_identity(connection, project_id)
            assert_current_review_bindings(connection)
        else:
            raise InvalidTransitionError("放弃删除只支持当前或直接前一版项目合同。")
        revision, lifecycle, brief = connection.execute("SELECT revision,lifecycle_revision,brief FROM v2_projects WHERE id=?", (project_id,)).fetchone()
        snapshots = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts WHERE project_id=? ORDER BY id", (project_id,)).fetchall()
        attempts = [CodexExecAttempt.model_validate_json(row[0]) for row in snapshots]
        jobs = {attempt.job_id for attempt in attempts}
        blockers = []
        for run_id, state in connection.execute("SELECT id,state FROM v2_autopilot_runs WHERE project_id=? AND state NOT IN ('cancelled','taken_over','stale','handed_off')", (project_id,)):
            blockers.append(f"{run_id}: 自动运行仍为 {state}，请先明确取消或接管，再核对放弃删除。")
        if not attempts:
            blockers.append("没有可明确放弃的 Codex Exec 自动素材任务；请使用普通永久删除。")
        for table, column, terminal in (
            ("v2_generation_runs", "status", "'succeeded','failed','cancelled','quarantined'"),
            ("v2_media_tasks", "status", "'succeeded','failed','cancelled'"),
            ("v2_video_jobs", "state", "'ingested','cancelled','failed'"),
        ):
            if connection.execute(f"SELECT 1 FROM {table} WHERE project_id=? AND {column} NOT IN ({terminal}) LIMIT 1", (project_id,)).fetchone():
                blockers.append(f"{table}: 其他工作仍未结束，不能通过自动素材放弃绕过。")
        for table, key, column, states in (
            ("v2_image_jobs", "id", "state", "'prepared','exported'"),
            ("v2_character_reference_proposals", "id", "state", "'prepared','exported'"),
            ("v2_art_reference_proposals", "id", "state", "'prepared','exported'"),
            *((table, "job_id", "status", "'prepared'") for table in (
                "v2_source_outline_candidates", "v2_cast_candidates", "v2_art_candidates", "v2_script_candidates", "v2_storyboard_review_candidates")),
            ("v2_production_bridge_intent_jobs", "id", "status", "'queued','dispatched','outcome_unknown'"),
        ):
            for (job,) in connection.execute(f"SELECT {key} FROM {table} WHERE project_id=? AND {column} IN ({states})", (project_id,)):
                if job not in jobs:
                    blockers.append(f"{job}: 非当前 Codex Exec 自动任务仍可发布，不能放弃删除。")
        if registry._native_ownership is not None:
            blockers.extend(registry._native_ownership(project_id, jobs))
        packet = AbandonmentPacket(project_id=project_id, project_home=str(home.path), attempts=attempts)
        host = native.codex_exec_abandonment(packet)
        blockers.extend(host.blockers)
        digest = stable_hash({"projectId": project_id, "revision": revision, "lifecycleRevision": lifecycle,
            "brief": json.loads(brief), "hostPreview": host.preview_hash})
        return home, packet, {"projectId": project_id, "expectedProjectRevision": revision,
            "expectedLifecycleRevision": lifecycle, "confirmationTitle": json.loads(brief)["title"],
            "previewHash": digest, "hostPreviewHash": host.preview_hash, "eligible": not blockers,
            "blockers": blockers, "unknownAttemptIds": host.unknown_attempt_ids,
            "remoteOutcomes": "preserved", "revoked": host.revoked}


def preview_abandonment(registry, project_id, native):
    home = registry._project_home(project_id)
    with closing(ProjectAccessLease.acquire(home.path, mode="shared")):
        return _context(registry, project_id, native)[2]


def abandon_and_delete(registry, application, project_id, request, native):
    consent = request.model_dump(mode="json", by_alias=True)
    existing = application.abandonment.current(project_id)
    if existing is not None and existing["revocation_json"] is not None:
        from .abandonment_ledger import resume_revoked_erasure
        return resume_revoked_erasure(registry, application.abandonment, existing, consent)
    home = registry._project_home(project_id)
    lease = ProjectAccessLease.acquire(home.path, mode="exclusive")
    try:
        home, packet, context = _context(registry, project_id, native)
        for owner, expected, actual in (
            ("project", request.expected_project_revision, context["expectedProjectRevision"]),
            ("project-lifecycle", request.expected_lifecycle_revision, context["expectedLifecycleRevision"]),
        ):
            if expected != actual:
                raise RevisionConflictError(owner, expected, actual)
        if request.confirmation_title != context["confirmationTitle"] or request.preview_hash != context["previewHash"]:
            raise InvalidTransitionError("删除确认与当前项目预览不同，请重新核对。")
        if not request.acknowledge_unknown_remote:
            raise InvalidTransitionError("必须明确确认远程结果可能仍然未知。")
        if not context["eligible"]:
            raise ProjectBusyError("project_busy: " + "; ".join(context["blockers"]))
        application.abandonment.prepare(home, project_id, consent)
        receipt = native.codex_exec_abandonment(packet.model_copy(update={"expected_preview_hash": context["hostPreviewHash"]}), revoke=True)
        if not receipt.revoked or receipt.project_id != project_id or receipt.preview_hash != context["hostPreviewHash"]:
            raise InvalidTransitionError("主机未确认精确项目发布权限已撤销；项目保留。")
        application.abandonment.acknowledge(project_id, receipt)
        remove_owned_home(home.path, outputs_root=registry.outputs_root, manifest=home.manifest,
            lease=lease, close_repository=lambda: None)
        application.abandonment.finish(project_id)
    except OSError as error:
        if application.abandonment.current(project_id) is not None:
            raise InvalidTransitionError("项目删除尚未完成；已确认的主机发布撤销会保留。请从项目目录的待完成删除中重试。") from error
        raise
    finally:
        lease.close()
