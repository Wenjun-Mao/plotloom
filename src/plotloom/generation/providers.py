"""Plotloom-owned provider protocol and OpenAI-compatible adapter."""

from __future__ import annotations

import re
from typing import Any, Literal, Protocol, runtime_checkable
from urllib.parse import urlparse

import requests

from .contracts import (
    GenerationRequest,
    ProviderCapabilities,
    ProviderResponse,
    ProviderUsage,
    ReasoningMode,
    RequestExtension,
)
from .exceptions import (
    ProviderCapabilityError,
    ProviderError,
    ProviderOutcomeUnknownError,
    ProviderRequestNotSentError,
    ProviderResponseError,
)
from .responses import assistant_message_final_text, redact_provider_response_evidence
from .secrets import SecretLease


_SCHEMA_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


@runtime_checkable
class ProviderAdapter(Protocol):
    """One-attempt model provider boundary used by the orchestrator."""

    name: str
    capabilities: ProviderCapabilities

    def generate(
        self,
        request: GenerationRequest,
        secret: SecretLease | None,
    ) -> ProviderResponse:
        ...


class OpenAICompatibleAdapter:
    """Synchronous OpenAI Chat Completions adapter.

    The adapter performs exactly one HTTP attempt. Retry and repair decisions
    belong to the run orchestrator so every attempt is represented explicitly.
    """

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        capabilities: ProviderCapabilities | None = None,
        timeout_seconds: float = 300.0,
        connect_timeout_seconds: float = 10.0,
        auth_mode: Literal["none", "bearer"] = "bearer",
        session: requests.Session | Any | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "base_url must be an HTTP(S) API root with a host and without credentials, query, or fragment"
            )
        try:
            parsed.port
        except ValueError as error:
            raise ValueError("base_url must use a valid port") from error
        if timeout_seconds <= 0 or connect_timeout_seconds <= 0:
            raise ValueError("provider timeouts must be greater than zero")
        if auth_mode not in {"none", "bearer"}:
            raise ValueError("auth_mode must be 'none' or 'bearer'")
        self.name = name.strip() or "openai-compatible"
        self.base_url = base_url.rstrip("/")
        self.capabilities = capabilities or ProviderCapabilities()
        self.timeout_seconds = timeout_seconds
        self.connect_timeout_seconds = connect_timeout_seconds
        self.auth_mode = auth_mode
        self._session = session or requests.Session()

    def generate(self, request: GenerationRequest, secret: SecretLease | None) -> ProviderResponse:
        if not self.capabilities.chat_completions:
            raise ProviderCapabilityError(
                f"Provider {self.name!r} does not advertise Chat Completions support"
            )
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens

        self._apply_request_extension(payload, request)

        if request.response_schema is not None:
            if not self.capabilities.json_schema:
                raise ProviderCapabilityError(
                    f"Provider {self.name!r} cannot satisfy required JSON Schema output"
                )
            schema_name = request.response_schema_name or "generation_result"
            if not _SCHEMA_NAME_RE.fullmatch(schema_name):
                raise ValueError(f"Invalid response_schema_name: {schema_name!r}")
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": request.response_schema,
                },
            }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        outbound_secret: str | None = None
        if self.auth_mode == "bearer":
            if secret is None:
                raise ProviderError(f"Provider {self.name!r} requires a bearer credential")
            with secret.reveal() as api_key:
                outbound_secret = api_key
                headers["Authorization"] = f"Bearer {api_key}"
                response = self._post(payload, headers)
        else:
            # A no-auth local provider must not receive an accidental browser or
            # server credential even when the caller has one available.
            response = self._post(payload, headers)

        status_code = int(getattr(response, "status_code", 0) or 0)
        headers_obj = getattr(response, "headers", {}) or {}
        header_request_id = headers_obj.get("x-request-id")
        if not 200 <= status_code < 300:
            raise ProviderResponseError(
                f"provider.http_{status_code}",
                status_code=status_code,
                request_id=(
                    str(header_request_id) if header_request_id is not None else None
                ),
            )
        try:
            raw = response.json()
        except (ValueError, requests.JSONDecodeError) as exc:
            raise ProviderResponseError(
                "provider.envelope_non_json",
                status_code=status_code,
                request_id=(
                    str(header_request_id) if header_request_id is not None else None
                ),
            ) from exc
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                "provider.envelope_non_object",
                status_code=status_code,
                request_id=(
                    str(header_request_id) if header_request_id is not None else None
                ),
            )
        raw = redact_provider_response_evidence(
            raw,
            known_secrets=((outbound_secret,) if outbound_secret is not None else ()),
        )

        choices = raw.get("choices") if isinstance(raw.get("choices"), list) else []
        first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
        message = first_choice.get("message")
        final_content, reasoning_present = (
            assistant_message_final_text(message)
            if isinstance(message, dict)
            else (None, False)
        )
        usage_data = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        request_id = raw.get("id") or headers_obj.get("x-request-id")
        return ProviderResponse(
            provider=self.name,
            model=str(raw.get("model") or request.model),
            raw=raw,
            request_id=str(request_id) if request_id is not None else None,
            finish_reason=(
                str(first_choice.get("finish_reason"))
                if first_choice.get("finish_reason") is not None
                else None
            ),
            usage=ProviderUsage(
                input_tokens=_non_negative_int(usage_data.get("prompt_tokens")),
                output_tokens=_non_negative_int(usage_data.get("completion_tokens")),
            ),
            final_content=final_content,
            reasoning_present=reasoning_present,
            outcome_code=(None if final_content is not None else "response.missing_final_content"),
        )

    def check_readiness(self, expected_model: str, secret: SecretLease | None) -> Any:
        """Check the standard model-list endpoint without generating content.

        This request has no creative payload and is safe to classify as a
        failed preflight.  It deliberately performs one request only.
        """

        # Imported lazily to keep the generation transport independent of the
        # registry module that calls this optional capability.
        from ..text_adapters import ReadinessResult

        if not self.capabilities.chat_completions:
            return ReadinessResult("capability_mismatch", "readiness.chat_completions_required", True)
        headers = {"Accept": "application/json"}
        if self.auth_mode == "bearer":
            if secret is None:
                return ReadinessResult("authentication_failed", "readiness.credential_unavailable", True)
            with secret.reveal() as api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                return self._check_models(headers, expected_model)
        return self._check_models(headers, expected_model)

    def _check_models(self, headers: dict[str, str], expected_model: str) -> Any:
        from ..text_adapters import ReadinessResult

        try:
            response = self._session.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=(self.connect_timeout_seconds, self.connect_timeout_seconds),
                allow_redirects=False,
            )
        except (requests.Timeout, requests.ConnectionError):
            return ReadinessResult("unreachable", "readiness.transport_unreachable", True)
        except requests.RequestException:
            return ReadinessResult("unreachable", "readiness.transport_unreachable", True)
        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code in {401, 403}:
            return ReadinessResult("authentication_failed", "readiness.authentication_rejected", True)
        # `/models` is an optional OpenAI-compatible extension.  A service
        # that does not implement it has not proved its chat endpoint broken;
        # retain an explicitly unverified state and let ordinary dispatch own
        # the generation outcome.
        if status_code in {404, 405}:
            return ReadinessResult("unverified", "readiness.models_unsupported", False)
        if not 200 <= status_code < 300:
            return ReadinessResult("unreachable", f"readiness.http_{status_code}", True)
        try:
            payload = response.json()
        except (ValueError, requests.JSONDecodeError):
            return ReadinessResult("unverified", "readiness.models_unsupported", False)
        entries = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return ReadinessResult("unverified", "readiness.models_unsupported", False)
        models = {
            item.get("id") for item in entries
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if expected_model not in models:
            return ReadinessResult("model_mismatch", "readiness.expected_model_absent", True)
        return ReadinessResult("available", "readiness.models_verified", True)

    def _apply_request_extension(
        self,
        payload: dict[str, Any],
        request: GenerationRequest,
    ) -> None:
        """Emit only the one explicitly declared non-standard extension.

        This intentionally does not accept a caller-owned mapping.  Passing
        arbitrary JSON through here would make a saved profile an unreviewed
        provider-specific execution surface and would make snapshots unable to
        state what the request actually meant.
        """

        if request.request_extension == RequestExtension.NONE:
            if request.reasoning_mode != ReasoningMode.PROVIDER_DEFAULT:
                raise ProviderCapabilityError(
                    "reasoning_mode requires request_extension=chat_template_kwargs"
                )
            return
        if request.request_extension != RequestExtension.CHAT_TEMPLATE_KWARGS:
            raise ProviderCapabilityError("unsupported request extension")
        if not self.capabilities.chat_template_kwargs:
            raise ProviderCapabilityError(
                f"Provider {self.name!r} does not advertise chat_template_kwargs support"
            )
        if request.reasoning_mode == ReasoningMode.PROVIDER_DEFAULT:
            raise ProviderCapabilityError(
                "chat_template_kwargs requires an explicit enabled or disabled reasoning_mode"
            )
        payload["chat_template_kwargs"] = {
            "enable_thinking": request.reasoning_mode == ReasoningMode.ENABLED
        }

    def _post(self, payload: dict[str, Any], headers: dict[str, str]) -> Any:
        try:
            return self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=(self.connect_timeout_seconds, self.timeout_seconds),
                allow_redirects=False,
            )
        except requests.ConnectTimeout as exc:
            raise ProviderRequestNotSentError(
                "provider connection was not established"
            ) from exc
        except requests.RequestException as exc:
            # Once connection establishment is no longer provably the failing
            # phase, the provider may have received and completed the request.
            # The caller must retain this as outcome_unknown and never replay it.
            raise ProviderOutcomeUnknownError(
                f"provider transport outcome is unknown: {type(exc).__name__}"
            ) from exc


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None
