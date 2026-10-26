"""Durable prompt/validation evidence and provider-response decoding."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from .domain import (
    Artifact,
    ArtifactKind,
    GenerationAttempt,
    GenerationRun,
)
from .generation.contracts import (
    ProviderResponse,
    ProviderUsage,
    ValidationIssue,
)
from .generation.exceptions import (
    ResponseExtractionError,
)
from .generation.providers import ProviderAdapter
from .generation.repair_facts import (
    SemanticRepairFact,
    serialize_semantic_repair_fact,
)
from .generation.responses import (
    extract_assistant_text,
)
from .generation.work_unit_contracts import (
    CompiledWorkUnitRequest,
)
from .persistence.codec import stable_hash

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )

from .correction_execution_contracts import CorrectionSourceContractError


def persist_prompt(
    repository: "GenerationRunRepository",
    run: GenerationRun,
    attempt: GenerationAttempt,
    work_unit_id: str,
    compiled: CompiledWorkUnitRequest,
    adapter: ProviderAdapter,
    model: str,
) -> None:
    assert_correction_audit_selection(compiled)
    content = {
        "trace": compiled.rendered.trace.model_dump(mode="json"),
        "messages": [
            message.model_dump(mode="json") for message in compiled.rendered.messages
        ],
        "schemaId": compiled.contract.schema_id,
        "structuredOutputMode": compiled.rendered.output.structured_output_mode,
        "provider": adapter.name,
        "model": model,
        "attemptKind": attempt.attempt_kind.value,
        "sourceAttemptId": attempt.source_attempt_id,
        "contract": compiled.contract.snapshot_dump(),
    }
    if compiled.audit_issue_selection is not None:
        content["correctionIssueSelection"] = compiled.audit_issue_selection
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=work_unit_id,
            stage=compiled.contract.stage,
            kind=ArtifactKind.PROMPT,
            content=content,
            content_hash=stable_hash(content),
        )
    )


def assert_attempt_prompt_contract(
    artifact: Artifact,
    attempt: GenerationAttempt,
    compiled: CompiledWorkUnitRequest,
) -> None:
    """Verify that a resumed attempt still means exactly the same request."""

    assert_correction_audit_selection(compiled)
    content = artifact.content if isinstance(artifact.content, Mapping) else {}
    expected_contract = compiled.contract.snapshot_dump()
    if (
        artifact.attempt_id != attempt.id
        or content.get("contract") != expected_contract
        or content.get("attemptKind") != attempt.attempt_kind.value
        or content.get("sourceAttemptId") != attempt.source_attempt_id
        or content.get("correctionIssueSelection") != compiled.audit_issue_selection
        or ("correctionIssueSelection" in content)
        != (compiled.audit_issue_selection is not None)
    ):
        raise ValueError(
            "recoverable attempt prompt evidence does not match its frozen execution contract"
        )


def assert_correction_audit_selection(
    compiled: CompiledWorkUnitRequest,
) -> None:
    """Fail closed before persistence if audit evidence and contract diverge."""

    selection = compiled.audit_issue_selection
    selection_hash = compiled.contract.correction_issue_selection_hash
    is_correction = compiled.contract.correction_ordinal is not None
    if is_correction != (selection is not None) or is_correction != (
        selection_hash is not None
    ):
        raise CorrectionSourceContractError(
            "correction audit selection presence does not match its contract"
        )
    if selection is not None and stable_hash(selection) != selection_hash:
        raise CorrectionSourceContractError(
            "correction audit selection does not match its contract hash"
        )


def provider_response_from_artifact(
    artifact: Artifact,
    *,
    attempt: GenerationAttempt,
    compiled: CompiledWorkUnitRequest,
    fallback_provider: str,
    fallback_model: str,
) -> ProviderResponse:
    """Rehydrate a durable response for local-only post-crash processing."""

    content = artifact.content if isinstance(artifact.content, Mapping) else {}
    raw = content.get("rawResponse")
    if not isinstance(raw, dict):
        raise ValueError("durable provider response has no object envelope")
    expected_contract = compiled.contract.snapshot_dump()
    if content.get("contract") != expected_contract:
        raise ValueError(
            "durable provider response does not match the frozen prompt contract"
        )
    try:
        final_content = extract_assistant_text(raw)
    except ResponseExtractionError:
        final_content = None
    usage = content.get("usage")
    usage_data = usage if isinstance(usage, Mapping) else {}
    outcome_code = content.get("outcomeCode")
    return ProviderResponse(
        provider=attempt.provider or fallback_provider,
        model=attempt.model or fallback_model,
        raw=raw,
        request_id=(
            str(content["providerRequestId"])
            if content.get("providerRequestId") is not None
            else attempt.provider_request_id
        ),
        finish_reason=(
            str(content["finishReason"])
            if content.get("finishReason") is not None
            else None
        ),
        usage=ProviderUsage(
            input_tokens=_optional_non_negative_int(usage_data.get("inputTokens")),
            output_tokens=_optional_non_negative_int(usage_data.get("outputTokens")),
        ),
        final_content=final_content,
        reasoning_present=bool(content.get("reasoningPresent")),
        outcome_code=(
            str(outcome_code)
            if outcome_code is not None
            else (
                None if final_content is not None else "response.missing_final_content"
            )
        ),
    )


def persist_validation(
    repository: "GenerationRunRepository",
    run: GenerationRun,
    attempt_id: str,
    work_unit_id: str,
    compiled: CompiledWorkUnitRequest,
    *,
    accepted: bool,
    issues: tuple[ValidationIssue, ...],
    transformations: tuple[str, ...],
    error: str | None = None,
    repair_facts: tuple[SemanticRepairFact, ...] = (),
) -> None:
    content = {
        "accepted": accepted,
        "issues": [issue.model_dump(mode="json") for issue in issues],
        "transformations": list(transformations),
        "error": error,
        "repairFacts": [serialize_semantic_repair_fact(fact) for fact in repair_facts],
        "contract": compiled.contract.snapshot_dump(),
    }
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt_id,
            work_unit_id=work_unit_id,
            stage=compiled.contract.stage,
            kind=ArtifactKind.VALIDATION,
            content=content,
            content_hash=stable_hash(content),
        )
    )


def assert_prior_prompt_contract(
    repository: "GenerationRunRepository",
    run_id: str,
    work_unit_id: str,
    compiled: CompiledWorkUnitRequest,
) -> None:
    """Refuse an undispatched recovery when its prompt/schema changed."""

    expected = compiled.contract.snapshot_dump()
    previous_prompts = [
        artifact
        for artifact in repository.get_run_trace(run_id).artifacts
        if artifact.work_unit_id == work_unit_id
        and artifact.kind == ArtifactKind.PROMPT
    ]
    if not previous_prompts:
        return
    prior = previous_prompts[-1].content
    prior_contract = prior.get("contract") if isinstance(prior, Mapping) else None
    if prior_contract != expected:
        raise ValueError(
            "work-unit prompt contract changed after durable prompt evidence; "
            "the undispatched unit must not be resent"
        )


def _optional_non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None
