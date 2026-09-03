"""One-attempt generation plus explicit, child-run JSON repair."""

from __future__ import annotations

import re
import threading
import uuid
from typing import Any, Mapping, Protocol, TypeVar, runtime_checkable

from .contracts import (
    AttemptKind,
    AttemptStatus,
    ExtractionPolicy,
    GenerationAttempt,
    GenerationRequest,
    GenerationResult,
    GenerationRun,
    QuarantineRecord,
    ReasoningMode,
    RenderedPrompt,
    RequestExtension,
    RunStatus,
    ValidationIssue,
    utc_now,
)
from .exceptions import (
    GenerationRunFailed,
    ProviderCapabilityError,
    ProviderError,
    ResponseExtractionError,
)
from .prompts import PromptRenderer, canonical_json, sha256_text
from .providers import ProviderAdapter
from .responses import (
    extract_assistant_text,
    parse_json_text,
    redact_provider_boundary_evidence,
)
from .secrets import SecretLease
from .validation import SemanticValidationContext, ValidationAdapter


T = TypeVar("T")


@runtime_checkable
class QuarantineStore(Protocol):
    def put(self, record: QuarantineRecord) -> None:
        ...

    def get(self, quarantine_id: str) -> QuarantineRecord | None:
        ...

    def list_for_run(self, run_id: str) -> tuple[QuarantineRecord, ...]:
        ...


@runtime_checkable
class AttemptLifecycleObserver(Protocol):
    """Durable hand-off points around one externally billed provider attempt.

    Observer failures are deliberately fatal. In particular,
    ``prompt_prepared`` runs before the provider boundary so a caller that
    cannot durably record the prompt cannot accidentally spend provider
    credits without provenance.
    """

    def prompt_prepared(self, attempt: GenerationAttempt) -> None:
        ...

    def response_extracted(self, attempt: GenerationAttempt) -> None:
        ...

    def validation_completed(
        self,
        attempt: GenerationAttempt,
        candidate: Any | None,
    ) -> None:
        ...


class InMemoryQuarantineStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, QuarantineRecord] = {}

    def put(self, record: QuarantineRecord) -> None:
        with self._lock:
            if record.quarantine_id in self._records:
                raise ValueError(f"Duplicate quarantine id: {record.quarantine_id}")
            self._records[record.quarantine_id] = record

    def get(self, quarantine_id: str) -> QuarantineRecord | None:
        with self._lock:
            return self._records.get(quarantine_id)

    def list_for_run(self, run_id: str) -> tuple[QuarantineRecord, ...]:
        with self._lock:
            return tuple(record for record in self._records.values() if record.run_id == run_id)


class GenerationOrchestrator:
    """Execute exactly one provider attempt per run.

    Invalid output is quarantined and returned as a failed run. Repair is never
    implicit: callers must select a quarantine record and invoke ``repair`` to
    create a separate child run.
    """

    def __init__(
        self,
        *,
        renderer: PromptRenderer,
        provider: ProviderAdapter,
        quarantine: QuarantineStore | None = None,
    ) -> None:
        self.renderer = renderer
        self.provider = provider
        self.quarantine = quarantine or InMemoryQuarantineStore()

    def generate(
        self,
        *,
        prompt_id: str,
        variables: Mapping[str, Any],
        validator: ValidationAdapter[T],
        model: str,
        secret: SecretLease | None,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
        extraction_policy: ExtractionPolicy | None = None,
        request_extension: RequestExtension = RequestExtension.NONE,
        reasoning_mode: ReasoningMode = ReasoningMode.PROVIDER_DEFAULT,
        validation_metadata: Mapping[str, Any] | None = None,
        observer: AttemptLifecycleObserver | None = None,
    ) -> GenerationResult:
        run = GenerationRun(
            run_id=f"run_{uuid.uuid4().hex}",
            stage=prompt_id,
            kind="generation",
            status=RunStatus.RUNNING,
        )
        schema = validator.json_schema()
        if "json_schema" in variables:
            return self._fail_before_attempt(
                run,
                ValueError("json_schema is supplied by the validation adapter, not the caller"),
                "Generation prompt variables are invalid",
            )
        try:
            rendered = self.renderer.render(
                prompt_id,
                {**dict(variables), "json_schema": schema},
            )
            run.stage = rendered.trace.stage
            self._assert_json_prompt(rendered, expected_schema_id=validator.schema_id)
        except Exception as exc:
            return self._fail_before_attempt(run, exc, "Generation prompt could not be prepared")

        return self._execute_one_attempt(
            run=run,
            rendered=rendered,
            kind=AttemptKind.PRIMARY,
            validator=validator,
            schema=schema,
            model=model,
            secret=secret,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            extraction_policy=extraction_policy or ExtractionPolicy(),
            request_extension=request_extension,
            reasoning_mode=reasoning_mode,
            validation_metadata=validation_metadata,
            observer=observer,
        )

    def repair(
        self,
        *,
        quarantine_id: str,
        parent_run_id: str,
        validator: ValidationAdapter[T],
        model: str,
        secret: SecretLease | None,
        instructions: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int | None = None,
        extraction_policy: ExtractionPolicy | None = None,
        request_extension: RequestExtension = RequestExtension.NONE,
        reasoning_mode: ReasoningMode = ReasoningMode.PROVIDER_DEFAULT,
        validation_metadata: Mapping[str, Any] | None = None,
        observer: AttemptLifecycleObserver | None = None,
    ) -> GenerationResult:
        """Explicitly repair a selected quarantined response in a child run."""

        source = self.quarantine.get(quarantine_id)
        if source is None:
            raise ValueError(f"Unknown quarantine record: {quarantine_id}")
        if source.run_id != parent_run_id:
            raise ValueError("The selected quarantine record does not belong to parent_run_id")
        if source.schema_id != validator.schema_id:
            raise ValueError(
                f"Quarantine schema {source.schema_id!r} does not match validator "
                f"{validator.schema_id!r}"
            )

        run = GenerationRun(
            run_id=f"run_{uuid.uuid4().hex}",
            stage=source.stage,
            kind="repair",
            parent_run_id=parent_run_id,
            source_quarantine_id=quarantine_id,
            status=RunStatus.RUNNING,
        )
        schema = validator.json_schema()
        try:
            rendered = self.renderer.render(
                "repair_json",
                {
                    "stage": source.stage,
                    "invalid_response": source.raw_response,
                    "validation_errors": [
                        issue.model_dump(mode="json", by_alias=True)
                        for issue in source.validation_issues
                    ],
                    "repair_instructions": instructions or "",
                    "json_schema": schema,
                },
            )
            self._assert_json_prompt(rendered)
        except Exception as exc:
            return self._fail_before_attempt(run, exc, "Repair prompt could not be prepared")

        return self._execute_one_attempt(
            run=run,
            rendered=rendered,
            kind=AttemptKind.REPAIR,
            validator=validator,
            schema=schema,
            model=model,
            secret=secret,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            extraction_policy=extraction_policy or ExtractionPolicy(),
            request_extension=request_extension,
            reasoning_mode=reasoning_mode,
            validation_metadata=validation_metadata,
            observer=observer,
        )

    def _execute_one_attempt(
        self,
        *,
        run: GenerationRun,
        rendered: RenderedPrompt,
        kind: AttemptKind,
        validator: ValidationAdapter[T],
        schema: dict[str, Any],
        model: str,
        secret: SecretLease | None,
        temperature: float,
        max_output_tokens: int | None,
        extraction_policy: ExtractionPolicy,
        request_extension: RequestExtension,
        reasoning_mode: ReasoningMode,
        validation_metadata: Mapping[str, Any] | None,
        observer: AttemptLifecycleObserver | None,
    ) -> GenerationResult:
        attempt = GenerationAttempt(
            attempt_id=f"attempt_{uuid.uuid4().hex}",
            number=1,
            kind=kind,
            status=AttemptStatus.RUNNING,
            prompt_trace=rendered.trace,
            rendered_messages=rendered.messages,
            schema_id=validator.schema_id,
            structured_output_mode=rendered.output.structured_output_mode,
            provider=self.provider.name,
            model=model,
        )
        run.attempts.append(attempt)
        try:
            provider_schema = self._provider_schema(rendered, schema)
            attempt.native_json_schema_used = provider_schema is not None
            request = GenerationRequest(
                messages=rendered.messages,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_schema=provider_schema,
                response_schema_name=(
                    _schema_name(validator.schema_id) if provider_schema is not None else None
                ),
                metadata={
                    "run_id": run.run_id,
                    "attempt_id": attempt.attempt_id,
                    "prompt_hash": rendered.trace.rendered_hash,
                },
                request_extension=request_extension,
                reasoning_mode=reasoning_mode,
            )
            if observer is not None:
                observer.prompt_prepared(attempt)
            provider_response = self.provider.generate(request, secret)
            provider_response = provider_response.model_copy(
                update={
                    "raw": redact_provider_boundary_evidence(
                        provider_response.raw,
                        secret_lease=secret,
                    )
                }
            )
            attempt.provider_request_id = provider_response.request_id
            attempt.finish_reason = provider_response.finish_reason
            attempt.usage = provider_response.usage
        except ProviderError as exc:
            return self._fail_attempt(
                run,
                attempt,
                exc,
                "Provider attempt failed",
                error_message=redact_provider_boundary_evidence(
                    str(exc), secret_lease=secret
                ),
            )
        except Exception as exc:
            return self._fail_attempt(
                run,
                attempt,
                exc,
                "Provider boundary failed",
                error_message=redact_provider_boundary_evidence(
                    str(exc), secret_lease=secret
                ),
            )

        raw_for_quarantine = canonical_json(provider_response.raw)
        try:
            raw_text = extract_assistant_text(provider_response)
        except ResponseExtractionError as exc:
            attempt.raw_response = raw_for_quarantine
            attempt.response_hash = attempt.response_hash or sha256_text(raw_for_quarantine)
            attempt.validation_issues = (
                ValidationIssue(code="response.extraction", message=str(exc)),
            )
            attempt.validation_accepted = False
            if observer is not None:
                observer.response_extracted(attempt)
                observer.validation_completed(attempt, None)
            self._quarantine(
                run,
                attempt,
                raw_for_quarantine,
                str(exc),
                schema_id=validator.schema_id,
            )
            raise GenerationRunFailed(
                "Generation output was quarantined after response extraction failed",
                run=run,
            ) from exc

        raw_for_quarantine = raw_text
        attempt.raw_response = raw_text
        attempt.response_hash = sha256_text(raw_text)
        if observer is not None:
            # Persist the returned assistant payload before JSON parsing or
            # validation. Those local boundaries can fail or be interrupted,
            # but the already-spent provider attempt must remain explainable.
            observer.response_extracted(attempt)

        try:
            extracted = parse_json_text(raw_text, policy=extraction_policy)
            attempt.transformations = extracted.transformations
        except ResponseExtractionError as exc:
            attempt.validation_issues = (
                ValidationIssue(code="response.extraction", message=str(exc)),
            )
            attempt.validation_accepted = False
            if observer is not None:
                observer.validation_completed(attempt, None)
            self._quarantine(
                run,
                attempt,
                raw_for_quarantine,
                str(exc),
                schema_id=validator.schema_id,
            )
            raise GenerationRunFailed(
                "Generation output was quarantined after response extraction failed",
                run=run,
            ) from exc

        context = SemanticValidationContext(
            stage=run.stage,
            metadata=dict(validation_metadata or {}),
        )
        try:
            report = validator.validate(extracted.value, context=context)
        except Exception as exc:
            self._mark_failed(run, attempt, exc)
            if observer is not None:
                observer.validation_completed(attempt, None)
            raise GenerationRunFailed(
                f"Local validation boundary failed: {type(exc).__name__}",
                run=run,
            ) from exc

        if not report.accepted:
            attempt.validation_accepted = False
            attempt.validation_issues = report.issues or (
                ValidationIssue(
                    code="validation.rejected_without_issue",
                    message=f"Validator {validator.schema_id!r} rejected the response",
                ),
            )
            if observer is not None:
                observer.validation_completed(attempt, None)
            self._quarantine(
                run,
                attempt,
                raw_text,
                f"Response failed schema/semantic validation for {validator.schema_id}",
                schema_id=validator.schema_id,
            )
            raise GenerationRunFailed(
                "Generation output was quarantined after local validation failed",
                run=run,
            )

        attempt.status = AttemptStatus.SUCCEEDED
        attempt.validation_accepted = True
        attempt.validation_issues = report.issues
        if observer is not None:
            observer.validation_completed(attempt, report.value)
        attempt.finished_at = utc_now()
        run.status = RunStatus.SUCCEEDED
        run.result_hash = sha256_text(canonical_json(report.value))
        run.finished_at = utc_now()
        return GenerationResult(run=run, value=report.value)

    def _provider_schema(
        self,
        rendered: RenderedPrompt,
        schema: dict[str, Any],
    ) -> dict[str, Any] | None:
        mode = rendered.output.structured_output_mode
        if mode == "none":
            return None
        if self.provider.capabilities.json_schema:
            return schema
        if mode == "require":
            raise ProviderCapabilityError(
                f"Prompt {rendered.trace.prompt_id!r} requires native JSON Schema output, "
                f"but provider {self.provider.name!r} does not advertise it"
            )
        # In prefer mode the identical schema remains embedded in the rendered
        # prompt and is still enforced by the local validation adapter.
        return None

    @staticmethod
    def _assert_json_prompt(
        rendered: RenderedPrompt,
        *,
        expected_schema_id: str | None = None,
    ) -> None:
        if rendered.output.format != "json":
            raise ValueError("GenerationOrchestrator requires a JSON-output prompt")
        if rendered.output.schema_id is None:
            raise ValueError("JSON generation prompts must declare a schema_id")
        if (
            expected_schema_id is not None
            and rendered.output.schema_id != expected_schema_id
        ):
            raise ValueError(
                f"Prompt schema {rendered.output.schema_id!r} does not match validator "
                f"{expected_schema_id!r}"
            )

    @staticmethod
    def _fail_before_attempt(
        run: GenerationRun,
        error: Exception,
        message: str,
    ) -> GenerationResult:
        run.status = RunStatus.FAILED
        run.finished_at = utc_now()
        raise GenerationRunFailed(f"{message}: {type(error).__name__}", run=run) from error

    @staticmethod
    def _fail_attempt(
        run: GenerationRun,
        attempt: GenerationAttempt,
        error: Exception,
        message: str,
        *,
        error_message: str | None = None,
    ) -> GenerationResult:
        GenerationOrchestrator._mark_failed(
            run, attempt, error, error_message=error_message
        )
        raise GenerationRunFailed(f"{message}: {type(error).__name__}", run=run) from error

    @staticmethod
    def _mark_failed(
        run: GenerationRun,
        attempt: GenerationAttempt,
        error: Exception,
        *,
        error_message: str | None = None,
    ) -> None:
        attempt.status = AttemptStatus.FAILED
        attempt.error_type = type(error).__name__
        attempt.error_message = error_message if error_message is not None else str(error)
        attempt.finished_at = utc_now()
        run.status = RunStatus.FAILED
        run.finished_at = utc_now()

    def _quarantine(
        self,
        run: GenerationRun,
        attempt: GenerationAttempt,
        raw_response: str,
        reason: str,
        *,
        schema_id: str,
    ) -> None:
        attempt.status = AttemptStatus.QUARANTINED
        attempt.finished_at = utc_now()
        response_hash = attempt.response_hash or sha256_text(raw_response)
        attempt.response_hash = response_hash
        record = QuarantineRecord(
            quarantine_id=f"quarantine_{uuid.uuid4().hex}",
            run_id=run.run_id,
            attempt_id=attempt.attempt_id,
            stage=run.stage,
            schema_id=schema_id,
            reason=reason,
            response_hash=response_hash,
            raw_response=raw_response,
            validation_issues=attempt.validation_issues,
        )
        self.quarantine.put(record)
        run.quarantine_ids.append(record.quarantine_id)
        run.status = RunStatus.QUARANTINED
        run.finished_at = utc_now()


def _schema_name(schema_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", schema_id).strip("_-")
    if not normalized or not normalized[0].isalpha():
        normalized = f"schema_{normalized}"
    return normalized[:64]
