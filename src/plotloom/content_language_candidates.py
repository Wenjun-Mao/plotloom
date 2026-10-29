"""Resolve generated candidates and edited proposals without inventing canon owners."""
from copy import deepcopy

from .content_language_contract import is_language_check
from .creative_handoff_contracts import CreativeHandoffRequest
from .exceptions import InvalidTransitionError, NotFoundError
from .persistence.project.creative_terminal import CANDIDATE_ROWS
from .persistence.schema import ProductionBridgeIntentJobRow


def candidate_row(session, stage, job_id):
    return session.get(ProductionBridgeIntentJobRow if stage.startswith("bridge-") else CANDIDATE_ROWS[stage], job_id)


def row_request(row):
    return CreativeHandoffRequest.model_validate(row.native_request if hasattr(row, "native_request") else row.request)


def candidate_value(row, stage):
    return getattr(row, {"outline": "outline", "branches": "outline", "characters": "cast", "art": "art",
                         "script": "script", "storyboard": "storyboard"}.get(stage, "candidate"))


def load_generated_candidate(store, stage, job_id, candidate=None):
    project_id = store.manifest.project_id
    with store.repository._read() as session:
        row = candidate_row(session, stage, job_id)
        if row is None or row.project_id != project_id:
            raise NotFoundError("生成候选任务不存在。")
        request = row_request(row)
        if request.stage != stage or request.job_id != job_id or is_language_check(request):
            raise InvalidTransitionError("检查任务不是可采用的创作候选。")
        value = deepcopy(candidate_value(row, stage))
        state = row.status
    if not stage.startswith("bridge-"):
        from .creative_commands import current_creative_candidate
        current_creative_candidate(store, stage, job_id, require_fresh=True)
        if state != "ready" or value is None:
            raise InvalidTransitionError("生成候选尚未完成结构验证；请先检查原任务交付。")
    elif value is None:
        from .native_bridge_intent_service import NativeBridgeIntentService
        from .native_bridge_presentation_service import NativeBridgePresentationService
        service = NativeBridgeIntentService if stage == "bridge-intent" else NativeBridgePresentationService
        # Manual native packages retain the same complete exchange contract.
        # Autopilot uses its exact completed attempt/receipt before calling ensure.
        delivery = service._delivery(store, request)
        if delivery is None:
            raise InvalidTransitionError("原生候选尚未完整交付。")
        value = delivery.candidate
    if stage.startswith("bridge-"):
        proposal = store.production_bridge_state().proposal
        if proposal is None:
            raise InvalidTransitionError("制作提案来源不可用。")
        context, _targets = store.repository.production_bridge_intent.source_context(project_id,
            expected_revision=proposal.revision, expected_hash=proposal.content_hash)
        original_context = {key: value for key, value in request.source.items() if key not in {"proposal", "intentPackage"}}
        if ({key: value for key, value in context.items() if key != "proposal"} != original_context
                or any(context["proposal"].get(key) != request.source["proposal"].get(key)
                       for key in ("inputs", "replacementTarget"))
                or "intentPackage" in request.source and request.source["intentPackage"] !=
                    proposal.intent_package.model_dump(mode="json", by_alias=True)):
            raise InvalidTransitionError("生成建议的原始来源或意图已改变；请重新准备候选，不能复用原检查。")
    if state in {"cancelled", "stale", "accepted"}:
        raise InvalidTransitionError("原生成候选已终止；原检查仅作为证据保留。")
    return request, deepcopy(candidate if candidate is not None else value)


def branch_candidate_from_mapping(mapping, prior):
    return {**prior, "nodes": [
        {"id": node.section_id, "title": node.title, "summary": node.summary} for node in mapping.sections],
        "choices": [{"nodeId": choice.section_id, "question": choice.prompt,
            "options": [{"id": item.outcome_id, "label": item.label, "consequence": item.consequence}
                        for item in choice.outcomes]} for choice in mapping.choices],
        "joins": [{"id": item.id, "reconciliation": mapping.join_reconciliations[item.id]} for item in mapping.topology.joins]}


def require_generated_bridge_edit(session, project_id, job_id, stage, candidate):
    if job_id is None:
        return  # Original hand authoring is separate from generated candidates.
    row = candidate_row(session, stage, job_id)
    if row is None or row.project_id != project_id or row.native_request is None:
        raise InvalidTransitionError("生成建议的原始来源不可用。")
    from .content_language_persistence import require_language_pass
    require_language_pass(session, row_request(row), candidate)
