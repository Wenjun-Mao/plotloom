"""Explicit consent and durable retry routes for one revoked project."""
from fastapi import status

from ..project_storage.abandonment import abandon_and_delete, preview_abandonment
from .contracts import ProjectAbandonDeleteRequest


def register_abandonment_routes(app, storage, specialists):
    @app.get("/api/v2/projects/{project_id}/abandonment-preview")
    def abandonment_preview(project_id: str):
        return preview_abandonment(storage.projects, project_id, specialists)

    @app.get("/api/v2/project-deletions")
    def pending_project_deletions():
        return storage.application.abandonment.pending()

    @app.post("/api/v2/projects/{project_id}/abandon-and-delete", status_code=status.HTTP_204_NO_CONTENT)
    def explicitly_abandon_and_delete(project_id: str, body: ProjectAbandonDeleteRequest):
        abandon_and_delete(storage.projects, storage.application, project_id, body, specialists)
