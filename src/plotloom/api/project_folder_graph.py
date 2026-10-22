"""Shared graph authoring capability; commands never install or dispatch."""
from fastapi import FastAPI

from ..domain import AuthoringDraft
from ..graph_commands import GraphCommandApplyRequest, GraphCommandPreview, GraphCommandRequest
from ..persistence.project.graph_workbench import GraphDraftRebaseRequest, GraphWorkbenchState


def register_project_folder_graph_routes(app: FastAPI, opened_project) -> None:
    @app.get("/api/v2/projects/{project_id}/graph-workbench", response_model=GraphWorkbenchState)
    def graph_workbench(project_id: str):
        with opened_project(project_id) as store:
            return store.graph_workbench_state()

    @app.post("/api/v2/projects/{project_id}/graph-workbench/preview", response_model=GraphCommandPreview)
    def preview_graph_command(project_id: str, body: GraphCommandRequest):
        with opened_project(project_id) as store:
            return store.preview_graph_command(body)

    @app.post("/api/v2/projects/{project_id}/graph-workbench/apply", response_model=AuthoringDraft)
    def apply_graph_command(project_id: str, body: GraphCommandApplyRequest):
        with opened_project(project_id) as store:
            return store.apply_graph_command(body)

    @app.post("/api/v2/projects/{project_id}/graph-workbench/recover", response_model=AuthoringDraft)
    def recover_graph_draft(project_id: str, body: GraphDraftRebaseRequest):
        with opened_project(project_id) as store:
            return store.rebase_graph_draft(body)
