"""One complete durable provider boundary with explicit delivery certainty."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from plotloom.generation.planning_contracts import GenerationWorkUnit

from plotloom.artifact_contracts import Artifact
from plotloom.run_contracts import AttemptStatus, GenerationAttempt, GenerationRun, WorkUnitFailureDisposition
from plotloom.provider_contracts import ProviderAuthMode, ProviderSnapshot
from .generation.contracts import (
    GenerationRequest,
    ProviderResponse,
    ReasoningMode,
    RequestExtension,
)
from .generation.exceptions import (
    ProviderCapabilityError,
    ProviderError,
    ProviderOutcomeUnknownError,
    ProviderRequestNotSentError,
    ProviderResponseError,
    ResponseExtractionError,
)
from .generation.providers import ProviderAdapter
from .generation.responses import (
    extract_assistant_text,
    redact_provider_boundary_evidence,
)
from .generation.work_unit_contracts import (
    CompiledWorkUnitRequest,
)
from .provider_profiles import TextProviderProfileSnapshot

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )

from .runtime_secrets import RunSecretLeaser
from .work_unit_evidence import provider_response_from_artifact


def exchange_provider_response(
    *,
    repository: "GenerationRunRepository",
    secrets: RunSecretLeaser,
    run: GenerationRun,
    attempt: GenerationAttempt,
    work_unit: GenerationWorkUnit,
    work_unit_id: str,
    compiled: CompiledWorkUnitRequest,
    adapter: ProviderAdapter,
    model: str,
    profile: ProviderSnapshot | TextProviderProfileSnapshot,
    request_extension: RequestExtension,
    reasoning_mode: ReasoningMode,
    response_artifact: Artifact | None,
) -> ProviderResponse:
    """Return a response only after required evidence commits; never retry."""
    if response_artifact is not None:
        provider_response = provider_response_from_artifact(
            response_artifact,
            attempt=attempt,
            compiled=compiled,
            fallback_provider=adapter.name,
            fallback_model=model,
        )
    else:
        try:
            provider_schema = provider_schema_for_request(compiled, adapter)
            lease = secrets.lease_for_run(
                run.id,
                auth_mode=ProviderAuthMode(profile.text_auth_mode),
                profile_id=profile.profile_id,
            )
        except Exception as error:
            repository.finish_attempt(
                attempt.id,
                AttemptStatus.FAILED,
                error=str(error),
                outcome_code="provider.preflight_failed",
                failure_disposition=WorkUnitFailureDisposition.FAILED,
            )
            raise

        # Commit immediately before the non-idempotent provider boundary.
        try:
            repository.mark_attempt_dispatched(attempt.id)
        except Exception as error:
            repository.finish_attempt(
                attempt.id,
                AttemptStatus.FAILED,
                error=str(error),
                outcome_code="provider.dispatch_not_started",
                failure_disposition=WorkUnitFailureDisposition.FAILED,
            )
            raise
        request = GenerationRequest(
            messages=compiled.rendered.messages,
            model=model,
            temperature=profile.text_temperature,
            max_output_tokens=min(
                work_unit.budget.max_output_tokens,
                profile.text_max_output_tokens,
            ),
            response_schema=provider_schema,
            response_schema_name=(
                _provider_schema_name(compiled.contract.schema_id)
                if provider_schema is not None
                else None
            ),
            metadata={
                "run_id": run.id,
                "attempt_id": attempt.id,
                "work_unit_id": work_unit_id,
                "prompt_hash": compiled.contract.rendered_hash,
            },
            request_extension=request_extension,
            reasoning_mode=reasoning_mode,
        )
        try:
            provider_response = adapter.generate(request, lease)
        except ProviderOutcomeUnknownError as error:
            repository.mark_attempt_outcome_unknown(
                attempt.id,
                error=redact_provider_boundary_evidence(str(error), secret_lease=lease),
            )
            raise
        except ProviderRequestNotSentError as error:
            repository.finish_attempt(
                attempt.id,
                AttemptStatus.FAILED,
                error=redact_provider_boundary_evidence(str(error), secret_lease=lease),
                outcome_code=error.code,
                failure_disposition=WorkUnitFailureDisposition.FAILED,
            )
            raise
        except ProviderResponseError as error:
            repository.finish_attempt(
                attempt.id,
                AttemptStatus.FAILED,
                error=redact_provider_boundary_evidence(str(error), secret_lease=lease),
                outcome_code=error.code,
                failure_disposition=WorkUnitFailureDisposition.FAILED,
            )
            raise
        except ProviderCapabilityError as error:
            # The built-in adapter checks typed extensions before its
            # HTTP call.  Persist the violated preflight contract
            # without inventing an ambiguous external side effect.
            repository.finish_attempt(
                attempt.id,
                AttemptStatus.FAILED,
                error="provider capability preflight failed",
                outcome_code="provider.request_not_sent",
                failure_disposition=WorkUnitFailureDisposition.FAILED,
            )
            raise
        except ProviderError as error:
            # Third-party adapters using only the historic base class
            # do not declare delivery certainty.  Preserve the safe,
            # conservative no-replay behavior.
            repository.mark_attempt_outcome_unknown(
                attempt.id,
                error=redact_provider_boundary_evidence(str(error), secret_lease=lease),
            )
            raise
        except Exception as error:
            repository.mark_attempt_outcome_unknown(
                attempt.id,
                error=f"unexpected provider boundary failure: {type(error).__name__}",
            )
            raise

        provider_response = provider_response.model_copy(
            update={
                "raw": redact_provider_boundary_evidence(
                    provider_response.raw,
                    secret_lease=lease,
                )
            }
        )
        # Canonical final content is always message.content. Normalize
        # adapters that omit the convenience field without ever
        # falling back to reasoning/reasoning_content.
        try:
            final_content = extract_assistant_text(provider_response)
        except ResponseExtractionError:
            final_content = None
        provider_response = provider_response.model_copy(
            update={
                "final_content": final_content,
                "outcome_code": (
                    provider_response.outcome_code
                    or (
                        None
                        if final_content is not None
                        else "response.missing_final_content"
                    )
                ),
            }
        )
        response_content = {
            # The unmodified envelope is durable before local extraction/parsing.
            # Reasoning remains here as evidence only and is never copied
            # into a correction prompt or canonical candidate.
            "rawResponse": provider_response.raw,
            "providerRequestId": provider_response.request_id,
            "finishReason": provider_response.finish_reason,
            "finalContentPresent": provider_response.final_content is not None,
            "reasoningPresent": provider_response.reasoning_present,
            "outcomeCode": provider_response.outcome_code,
            "usage": {
                "inputTokens": provider_response.usage.input_tokens,
                "outputTokens": provider_response.usage.output_tokens,
            },
            "contract": compiled.contract.snapshot_dump(),
        }
        try:
            repository.persist_attempt_response(
                attempt.id,
                response_content,
                provider_request_id=provider_response.request_id,
            )
        except Exception as error:
            # A provider response is already present in this process;
            # failure to persist it is a storage failure, not an
            # ambiguous provider outcome.  Do not replay or correct an
            # attempt whose required evidence could not be committed.
            repository.finish_attempt(
                attempt.id,
                AttemptStatus.FAILED,
                error="provider response persistence failed",
                outcome_code="storage.response_persist_failed",
                failure_disposition=WorkUnitFailureDisposition.FAILED,
            )
            raise ProviderError("provider response persistence failed") from error
    return provider_response


def provider_schema_for_request(
    compiled: CompiledWorkUnitRequest, adapter: ProviderAdapter
) -> dict[str, Any] | None:
    mode = compiled.rendered.output.structured_output_mode
    if mode == "none":
        return None
    if adapter.capabilities.json_schema:
        return compiled.response_schema
    if mode == "require":
        raise ProviderCapabilityError(
            f"Prompt {compiled.contract.prompt_id!r} requires native JSON Schema output, "
            f"but provider {adapter.name!r} does not advertise it"
        )
    return None


def _provider_schema_name(schema_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", schema_id).strip("_-")
    if not normalized or not normalized[0].isalpha():
        normalized = f"schema_{normalized}"
    return normalized[:64]
