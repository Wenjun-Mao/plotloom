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
)
from .exceptions import ProviderCapabilityError, ProviderError
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
        if self.auth_mode == "bearer":
            if secret is None:
                raise ProviderError(f"Provider {self.name!r} requires a bearer credential")
            with secret.reveal() as api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                response = self._post(payload, headers)
        else:
            # A no-auth local provider must not receive an accidental browser or
            # server credential even when the caller has one available.
            response = self._post(payload, headers)

        status_code = int(getattr(response, "status_code", 0) or 0)
        if not 200 <= status_code < 300:
            raise ProviderError(f"Provider {self.name!r} returned HTTP {status_code}")
        try:
            raw = response.json()
        except (ValueError, requests.JSONDecodeError) as exc:
            raise ProviderError(f"Provider {self.name!r} returned a non-JSON envelope") from exc
        if not isinstance(raw, dict):
            raise ProviderError(f"Provider {self.name!r} returned a non-object envelope")

        choices = raw.get("choices") if isinstance(raw.get("choices"), list) else []
        first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
        usage_data = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        headers_obj = getattr(response, "headers", {}) or {}
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
        )

    def _post(self, payload: dict[str, Any], headers: dict[str, str]) -> Any:
        try:
            return self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=(self.connect_timeout_seconds, self.timeout_seconds),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise ProviderError(
                f"Provider {self.name!r} request failed: {type(exc).__name__}"
            ) from exc


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None
