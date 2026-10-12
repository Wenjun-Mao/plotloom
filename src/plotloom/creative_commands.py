"""Repository-bound creative transport seams shared by UI and autopilot."""
from pathlib import Path

from .creative_handoff_contracts import CreativeHandoffError

CREATIVE_METHODS = {
    "branches": ("branch_state", "branch_candidate_request", "admit_branch_delivery"),
    "outline": ("source_outline_state", "outline_candidate_request", "admit_outline_delivery"),
    "characters": ("cast_state", "cast_candidate_request", "admit_cast_delivery"),
    "art": ("art_state", "art_candidate_request", "admit_art_delivery"),
    "script": ("script_state", "script_candidate_request", "admit_script_delivery"),
    "storyboard": ("storyboard_review_state", "storyboard_review_candidate_request", "admit_storyboard_review_delivery"),
}


def current_creative_candidate(store, stage, job_id, *, require_fresh=False):
    state = getattr(store, CREATIVE_METHODS[stage][0])()
    candidate = state.candidate
    if candidate is None or candidate.job_id != job_id:
        raise CreativeHandoffError("delivery_stale", "该任务不再是当前提案，请刷新页面。")
    if require_fresh and getattr(state, "stale_reasons", []):
        raise CreativeHandoffError("delivery_stale", "任务上下文已过期，请取消后重新准备。")
    return candidate


def send_creative_candidate(store, registry, stage, job_id, *, before_send=None, expected_task_id=None, expected_bindings=None):
    candidate = current_creative_candidate(store, stage, job_id, require_fresh=True)
    if candidate.status != "prepared":
        raise CreativeHandoffError("delivery_stale", "只有尚未交付的当前提案可以发送。")
    request = getattr(store, CREATIVE_METHODS[stage][1])(job_id)
    exchange = store.creative_handoff_exchange()
    pin = store.creative_handoff_execution_pin(request)
    if pin != exchange.current_execution_pin(stage):
        raise CreativeHandoffError("execution_pin_mismatch", "当前执行版本与冻结任务不同；未发送。")
    paths = exchange.write_package(request, pin)
    if Path(paths["deliveryPath"]).exists():
        raise CreativeHandoffError("delivery_conflict", "已有交付目录；请检查原任务，不要重复发送。")
    execution_root = Path(__file__).resolve().parents[2]
    registry.dispatch("text", job_id=job_id, package_path=paths["packagePath"], delivery_path=paths["deliveryPath"],
        context={"projectId": request.project_id, "stage": stage}, before_send=before_send, expected_task_id=expected_task_id, expected_bindings=expected_bindings,
        assignment=(f"Execute one frozen Plotloom {stage} assignment ({job_id}). "
            f"Use execution checkout {execution_root}; do not infer it from this chat's working directory. "
            f"Read {execution_root}/.agents/skills/plotloom-shuohao-specialist/SKILL.md, then "
            f"{paths['packagePath']}/request.json and COPY_ASSIGNMENT.txt. "
            "The package alone is authoritative; do not use previous chat assignments as project context. "
            f"Write only the requested delivery files under {paths['deliveryPath']}. "
            "Do not modify code, packages, project canon, selections or approvals. "
            "Do not generate images or videos. Validate with the pinned package instructions."))


def read_creative_delivery(store, request):
    try:
        return store.creative_handoff_exchange().read_delivery(request, store.creative_handoff_execution_pin(request))
    except CreativeHandoffError as error:
        if error.code == "delivery_partial":
            return None
        raise
