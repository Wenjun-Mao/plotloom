"""Explicit specialist handoffs over existing frozen creative packages."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Path

from ..creative_handoff_contracts import JOB_ID_PATTERN, CreativeHandoffError
from ..specialist_settings import SpecialistRegistry, SpecialistSettings
from .project_folder_image_terminal import register_image_terminal_routes

Stage = Literal["outline", "branches", "characters", "art", "script", "storyboard"]
# Existing stage repositories remain the sole owners of currentness and admission.
METHODS = {
    "branches": ("branch_state", "branch_candidate_request", "admit_branch_delivery"),
    "outline": ("source_outline_state", "outline_candidate_request", "admit_outline_delivery"),
    "characters": ("cast_state", "cast_candidate_request", "admit_cast_delivery"),
    "art": ("art_state", "art_candidate_request", "admit_art_delivery"),
    "script": ("script_state", "script_candidate_request", "admit_script_delivery"),
    "storyboard": ("storyboard_review_state", "storyboard_review_candidate_request", "admit_storyboard_review_delivery"),
}


def register_specialist_routes(app: FastAPI, opened_project: Callable[[str], Any], registry: SpecialistRegistry):
    register_image_terminal_routes(app, opened_project, registry)
    @app.get("/api/v2/specialists")
    def settings():
        return registry.view()

    @app.put("/api/v2/specialists")
    def save_settings(body: SpecialistSettings):
        return registry.save(body)

    def current(store, stage, job_id, *, require_fresh=False):
        state = getattr(store, METHODS[stage][0])()
        candidate = state.candidate
        if candidate is None or candidate.job_id != job_id:
            raise HTTPException(409, "该任务不再是当前提案，请刷新页面。")
        if require_fresh and getattr(state, "stale_reasons", []):
            raise HTTPException(409, "任务上下文已过期，请取消后重新准备。")
        return candidate

    @app.get("/api/v2/projects/{project_id}/specialist-tasks/{stage}/{job_id}")
    def task_status(project_id: str, stage: Stage, job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            candidate = current(store, stage, job_id)
            result = registry.status(job_id)
            return result | {"candidateStatus": candidate.status, "configured": bool(registry.view()["text"]["taskId"])}

    @app.post("/api/v2/projects/{project_id}/specialist-tasks/{stage}/{job_id}/send")
    def send(project_id: str, stage: Stage, job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            candidate = current(store, stage, job_id, require_fresh=True)
            if candidate.status != "prepared":
                raise HTTPException(409, "只有尚未交付的当前提案可以发送。")
            request = getattr(store, METHODS[stage][1])(job_id)
            paths = store.creative_handoff_exchange().verified_package_paths(request, store.creative_handoff_execution_pin(request))
            registry.dispatch(
                "text", job_id=job_id, package_path=paths["packagePath"], delivery_path=paths["deliveryPath"],
                context={"projectId": project_id, "stage": stage},
                assignment=(
                    f"Execute one frozen Plotloom {stage} assignment ({job_id}). "
                    "Read the project-local plotloom-shuohao-specialist skill, then "
                    f"{paths['packagePath']}/request.json and COPY_ASSIGNMENT.txt. "
                    "The package alone is authoritative; do not use previous chat assignments as project context. "
                    f"Write only the requested delivery files under {paths['deliveryPath']}. "
                    "Do not modify code, packages, project canon, selections or approvals. "
                    "Do not generate images or videos. Validate with the pinned package instructions."
                ),
            )
            return registry.status(job_id)

    @app.post("/api/v2/projects/{project_id}/specialist-tasks/{stage}/{job_id}/check")
    def check(project_id: str, stage: Stage, job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            registry.assert_creative_task_identity(job_id, project_id=project_id, stage=stage)
            candidate = getattr(store, METHODS[stage][0])().candidate
            is_current = candidate is not None and candidate.job_id == job_id
            if is_current and candidate.status in {"ready", "accepted"}:
                registry.complete_creative_task(job_id, project_id=project_id, stage=stage)
                return {"state": "completed"}
            request = getattr(store, METHODS[stage][1])(job_id) if is_current and candidate.status == "prepared" else store.terminal_creative_request(stage, job_id)
            try:
                delivery = store.creative_handoff_exchange().read_delivery(request, store.creative_handoff_execution_pin(request))
            except CreativeHandoffError as error:
                if error.code == "delivery_partial":
                    return registry.status(job_id)
                raise
            if delivery is None:
                return registry.status(job_id)
            if not is_current or candidate.status != "prepared":
                # A cancelled/replaced proposal can finish without becoming current.
                registry.complete_creative_task(job_id, project_id=project_id, stage=stage)
                return {"state": "completed", "candidateStatus": "discarded"}
            # Admission validates source binding/schema/report/hash; it is not creative acceptance.
            result = getattr(store, METHODS[stage][2])(delivery)
            registry.complete_creative_task(job_id, project_id=project_id, stage=stage)
            return {"state": "completed", "candidateStatus": result.status}
