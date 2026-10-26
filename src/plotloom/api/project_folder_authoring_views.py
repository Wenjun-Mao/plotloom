from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, status

from plotloom.api.approval_views import _approval_closure_view
from plotloom.api.contracts import (
    ApprovalClosureView,
    ProjectMediaTasksResponse,
    ProjectRunsResponse,
    StoryboardApprovalRequest,
    StoryboardReviewResponse,
)
from plotloom.gate_contracts import GateEvaluation
from plotloom.stage_contracts import StageName

from ..exceptions import (
    NotFoundError,
)
from ..project_storage import (
    ProjectFolderStorage,
)
from ..validation import STORYBOARD_GATE_SET_VERSION


def register_project_authoring_view_routes(
    app: FastAPI, storage: ProjectFolderStorage, opened_project: Callable
) -> None:
    @app.get("/api/v2/projects/{project_id}/runs", response_model=ProjectRunsResponse)
    def get_project_runs(project_id: str) -> ProjectRunsResponse:
        with opened_project(project_id) as store:
            return ProjectRunsResponse(runs=store.generation_runs())

    @app.get(
        "/api/v2/projects/{project_id}/storyboard-review",
        response_model=StoryboardReviewResponse,
    )
    def get_project_storyboard_review(project_id: str) -> StoryboardReviewResponse:
        with opened_project(project_id) as store:
            repository = store.authoring
            head = repository.get_stage_head(project_id, StageName.STORYBOARD)
            gate_evaluation: GateEvaluation | None = None
            if head.entity_revision_id is not None:
                try:
                    gate_evaluation = repository.get_gate_evaluation(
                        head.entity_revision_id, STORYBOARD_GATE_SET_VERSION
                    )
                except NotFoundError:
                    pass
            decisions = [
                _approval_closure_view(repository.get_approval_closure(item.id))
                for item in repository.list_approval_decisions(project_id)
            ]
            active = next(
                (
                    item.decision
                    for item in reversed(decisions)
                    if item.active and item.decision.decision == "approve"
                ),
                None,
            )
            return StoryboardReviewResponse(
                head=head,
                gate_evaluation=gate_evaluation,
                decisions=decisions,
                active_approval=active,
            )

    @app.post(
        "/api/v2/projects/{project_id}/storyboard-approval",
        response_model=ApprovalClosureView,
        status_code=status.HTTP_201_CREATED,
    )
    def decide_project_storyboard_approval(
        project_id: str, body: StoryboardApprovalRequest
    ) -> ApprovalClosureView:
        from ..project_storage.delegated_qa_grants import qa_command

        with (
            opened_project(project_id) as store,
            qa_command(store, storage.application, body.attribution),
        ):
            decision = store.authoring.decide_storyboard_approval(
                project_id,
                expected_revision=body.expected_revision,
                expected_content_hash=body.content_hash,
                decision=body.decision,
                reviewer=body.attribution,
                gate_set_version=body.gate_set_version,
            )
            return _approval_closure_view(
                store.authoring.get_approval_closure(decision.id)
            )

    @app.get(
        "/api/v2/projects/{project_id}/media-tasks",
        response_model=ProjectMediaTasksResponse,
    )
    def get_project_media_tasks(project_id: str) -> ProjectMediaTasksResponse:
        with opened_project(project_id):
            return ProjectMediaTasksResponse(tasks=[])
