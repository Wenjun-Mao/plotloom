"""Controller checkpoint: real semantic review precedes all generated adoption."""
from .autopilot_contracts import OperationScope
from .content_language_service import ContentLanguageService
from .creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES
from .image_job_contracts import ImageJobError
from .text_correction_contracts import automatic_correction_limit


def ensure_content_language(controller, store, view, claim, request, candidate, checkpoint):
    service = ContentLanguageService(controller.registry)
    scope = OperationScope.INSTALL if request.stage.startswith("bridge-") else OperationScope.TEXT
    with controller.command(store, view, claim, scope):
        job = service.prepare(store, request, candidate, code_revision=view.policy.code_revision, run_id=view.id)
    checked = service.advance(store, job)
    if checked["verdict"] == "pass":
        return True
    if checked["verdict"] == "reject":
        used = store.repository.autopilot.automatic_corrections_used(view.id, request.stage)
        if used >= automatic_correction_limit(view.policy, request.stage):
            raise ImageJobError("text_content_rejected", "原生语言检查拒绝了候选；已保留完整检查回执与失败位置，请修正候选。")
        from .codex_exec_files import read_confined_regular_file
        from .content_language_rejection import rejection_for_check
        root = store.creative_handoff_exchange().root / "jobs" / request.job_id
        prior = read_confined_regular_file(root, "delivery/" + CREATIVE_CANDIDATE_FILENAMES[request.stage], max_bytes=500_000)
        attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
        rejection = rejection_for_check(store, request, attempt, job, prior)
        with controller.command(store, view, claim, OperationScope.TEXT):
            corrective = store.repository.autopilot.prepare_text_correction(request, rejection, prior.decode())
        controller.publish_prepared_package(store, view, corrective, view.policy.execution_pins[request.stage])
    elif checked["verdict"] == "uncertain":
        raise ImageJobError("text_language_uncertain", "原生语言检查无法确定内容语言；保留原候选与检查，不会自动通过或重复提交。")
    elif checked.get("executionPending"):
        raise ImageJobError("content_language_check_pending", "语言检查正在核对原尝试；本地工作未确认停止前不会重试，请等待。")
    elif checked["state"] in {"failed", "settled", "outcome_unknown", "cancel_requested"}:
        raise ImageJobError("content_language_check_blocked", "原生语言检查失败或结果不确定；保留原尝试，不会重发或归为内容拒绝。")
    return False
