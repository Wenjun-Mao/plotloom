"""Narrow assistant checking surface, with no creative approval side effects."""
from typing import Any, Literal

from fastapi import Path
from pydantic import Field

from ..content_language_candidates import load_generated_candidate
from ..content_language_service import ContentLanguageService
from ..creative_handoff_contracts import JOB_ID_PATTERN
from ..domain_base import CamelModel
from ..generation_retry_policy import ManualExecutionRetry

Stage = Literal["outline", "branches", "characters", "art", "script", "storyboard",
                "bridge-intent", "bridge-presentation"]


class LanguageCheckBody(CamelModel):
    automatic_retry_limit: int = Field(default=1, strict=True, ge=0)
    candidate: dict[str, Any] | None = None


def register_content_language_routes(app, opened_project, registry):
    service = ContentLanguageService(registry)

    @app.post("/api/v2/projects/{project_id}/content-language/{stage}/{candidate_job_id}/check")
    def check(project_id: str, stage: Stage, candidate_job_id: str = Path(pattern=JOB_ID_PATTERN),
              body: LanguageCheckBody | None = None):
        with opened_project(project_id) as store:
            original, candidate = load_generated_candidate(store, stage, candidate_job_id, body.candidate if body else None)
            return service.ensure(store, original, candidate, automatic_retry_limit=body.automatic_retry_limit if body else 1)

    @app.get("/api/v2/projects/{project_id}/content-language/{stage}/{candidate_job_id}")
    def status(project_id: str, stage: Stage, candidate_job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            original, candidate = load_generated_candidate(store, stage, candidate_job_id)
            job = store.repository.content_language.find(original, candidate)
            if job is None:
                return {"candidateJobId": candidate_job_id, "state": "required", "verdict": None,
                        "checkJobId": None, "blocker": "生成候选尚未完成当前内容语言检查。"}
            return service.status(store, job)

    @app.get("/api/v2/projects/{project_id}/content-language-checks/{check_job_id}")
    def exact_status(project_id: str, check_job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            return service.status(store, check_job_id)

    @app.post("/api/v2/projects/{project_id}/content-language-checks/{check_job_id}/reconcile")
    def reconcile(project_id: str, check_job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            return service.advance(store, check_job_id, allow_admission=False)

    @app.post("/api/v2/projects/{project_id}/content-language-checks/{check_job_id}/retry")
    def retry(project_id: str, check_job_id: str, body: ManualExecutionRetry):
        with opened_project(project_id) as store:
            return service.retry(store, check_job_id, body)

    @app.post("/api/v2/projects/{project_id}/content-language-checks/{check_job_id}/cancel")
    def cancel(project_id: str, check_job_id: str = Path(pattern=JOB_ID_PATTERN)):
        with opened_project(project_id) as store:
            from ..codex_exec_contracts import CodexExecAttempt
            request, data = store.repository.content_language.cancel_execution(project_id, check_job_id)
            current_job = request.job_id
            attempt = CodexExecAttempt.model_validate(data["attempt"])
            if attempt.state not in {"completed", "failed", "settled"}:
                status = registry.codex_exec_cancel(attempt)
                if status.attempt is not None:
                    store.repository.content_language.observe(project_id, current_job,
                        attempt=status.attempt, receipt=status.receipt)
            return service.advance(store, check_job_id, allow_admission=False)
