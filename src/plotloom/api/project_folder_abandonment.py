"""Explicit consent and durable retry routes for one revoked project."""
from fastapi import status

from ..project_storage.abandonment import abandon_and_delete, preview_abandonment
from .contracts import ProjectAbandonDeleteRequest, ProjectDeletionStopRequest


def register_abandonment_routes(app, storage, specialists):
    from ..project_abandonment_contracts import PriorAbandonmentCandidate
    from ..project_storage.abandonment_catalog import prior_abandonment_candidates
    from ..project_storage.deletion_preparation import prepare_deletion, assert_deletion_scope

    @app.get("/api/v2/projects/{project_id}/deletion-preview")
    def deletion_preview(project_id: str):
        return prepare_deletion(storage.projects, project_id, specialists)

    @app.post("/api/v2/projects/{project_id}/stop-for-deletion")
    def stop_for_deletion(project_id: str, body: ProjectDeletionStopRequest):
        from ..autopilot_contracts import RunControlRequest
        from ..exceptions import InvalidTransitionError
        preview = prepare_deletion(storage.projects, project_id, specialists)
        if preview["mode"] != "stop" or preview["scopeHash"] != body.scope_hash:
            raise InvalidTransitionError("当前任务不支持此停止删除请求；请重新核对项目。")
        result = app.state.autopilot_service.control(project_id,
            RunControlRequest(expected_revision=body.expected_run_revision, action="cancel"),
            expected_run_id=body.expected_run_id, guard=lambda store: assert_deletion_scope(store, body))
        # The requesting browser suspends project reads until erasure settles.
        # Reinspect here after the control transaction closed; observation cannot
        # resume work, and its failure must not conceal acknowledged cancellation.
        try:
            fresh = prepare_deletion(storage.projects, project_id, specialists)
        except Exception:
            return {"runId": result.id, "state": result.state, "deletionPreview": None,
                "blocker": "自动运行已取消后续派发，但删除条件未能重新确认；请重新核对项目。"}
        return {"runId": result.id, "state": result.state, "deletionPreview": fresh}

    @app.get("/api/v2/project-abandonment-candidates", response_model=list[PriorAbandonmentCandidate])
    def abandonment_candidates():
        return prior_abandonment_candidates(storage.projects, storage.application.abandonment)

    @app.get("/api/v2/projects/{project_id}/abandonment-preview")
    def abandonment_preview(project_id: str):
        return preview_abandonment(storage.projects, project_id, specialists)

    @app.get("/api/v2/project-deletions")
    def pending_project_deletions():
        return storage.application.abandonment.pending()

    @app.post("/api/v2/projects/{project_id}/abandon-and-delete", status_code=status.HTTP_204_NO_CONTENT)
    def explicitly_abandon_and_delete(project_id: str, body: ProjectAbandonDeleteRequest):
        abandon_and_delete(storage.projects, storage.application, project_id, body, specialists)
