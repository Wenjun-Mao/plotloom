"""Explicit production operators, separate from bounded QA authority."""
from .delegated_qa import project_scope
from .delegated_qa_contracts import AgentQaAttribution
from .exceptions import InvalidTransitionError
from .operator_attribution import CodexTaskAttribution


def production_actor(project_id, qa_actor, operator):
    """Attribution identifies an authorized caller; it creates no authority."""
    if operator is not None:
        if qa_actor is not None or project_scope(project_id) is not None:
            raise InvalidTransitionError("Codex operator cannot replace bounded QA authorization")
        return operator.model_dump(mode="json", by_alias=True)
    return qa_actor or {"kind": "unnamed_creator"}


def retained_production_actor(project_id, execution):
    actor, qa_actor = execution.get("intentReviewActor"), execution.get("reviewAttribution")
    if qa_actor is not None:
        expected = AgentQaAttribution.model_validate(qa_actor).model_dump(mode="json", by_alias=True)
        if expected != qa_actor or actor != expected:
            raise ValueError("generation authorization actor changed")
        return actor
    if isinstance(actor, dict) and actor.get("kind") == "codex_task":
        parsed = CodexTaskAttribution.model_validate(actor)
        if parsed.model_dump(mode="json", by_alias=True) != actor:
            raise ValueError("Codex production operator must be canonical")
        if project_scope(project_id) is not None:
            raise ValueError("Codex operator cannot replace bounded QA authorization")
        return actor
    if actor != {"kind": "unnamed_creator"}:
        raise ValueError("generation authorization actor changed")
    return actor


def intent_authorization(project_id, execution, brief_hash):
    actor = retained_production_actor(project_id, execution)
    result = {"version": "production-intent.v2", "briefHash": brief_hash}
    if actor["kind"] == "codex_task":
        result["operator"] = actor
    return result


def assert_authorization_operator(project_id, execution, authorization):
    from .video_fidelity_contracts import IntentAuthorization
    parsed = IntentAuthorization.model_validate(authorization)
    if authorization != intent_authorization(project_id, execution, parsed.brief_hash):
        raise ValueError("generation authorization operator changed")
