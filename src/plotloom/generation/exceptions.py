"""Typed failures for the standalone Plotloom generation boundary.

The generation subsystem never turns a malformed provider response into a
successful result.  Callers can use these exception types to decide whether a
run should be shown to a user, retried, or retained for inspection.
"""

from __future__ import annotations


class GenerationError(RuntimeError):
    """Base class for all Plotloom generation failures."""


class PromptSpecError(GenerationError):
    """A prompt source is missing, malformed, or violates the versioned contract."""


class PromptRenderError(GenerationError):
    """A versioned prompt could not be rendered with the supplied variables."""


class ProviderError(GenerationError):
    """The upstream model provider rejected or failed a request."""


class ProviderRequestNotSentError(ProviderError):
    """The adapter can prove that no provider request crossed the boundary."""

    code = "provider.request_not_sent"


class ProviderOutcomeUnknownError(ProviderError):
    """The transport cannot prove whether the provider completed the request."""

    code = "provider.outcome_unknown"


class ProviderResponseError(ProviderError):
    """A provider response was received but cannot be used as a completion.

    Only bounded, public metadata is retained on the exception.  Remote bodies,
    headers other than a request ID, URLs, and credentials never become part of
    its string representation or durable run error.
    """

    def __init__(
        self,
        code: str,
        *,
        status_code: int,
        request_id: str | None = None,
    ) -> None:
        if not code.startswith("provider."):
            raise ValueError("provider response error code must be stable and namespaced")
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(f"{code} (HTTP {status_code})")


class ProviderCapabilityError(ProviderError):
    """A request requires a provider capability that is not advertised."""


class ResponseExtractionError(GenerationError):
    """A provider response did not contain the expected assistant payload."""


class ResponseValidationError(GenerationError):
    """A response was extracted but failed schema or semantic validation."""

    def __init__(self, message: str, *, issues: tuple[object, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues


class SecretLeaseError(GenerationError):
    """A secret lease is invalid, expired, revoked, or exhausted."""


class GenerationRunFailed(GenerationError):
    """A generation run ended without an accepted value."""

    def __init__(self, message: str, *, run: object) -> None:
        super().__init__(message)
        self.run = run
