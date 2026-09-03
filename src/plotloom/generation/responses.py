"""Explicit response-envelope and JSON-document extraction."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Mapping

from .contracts import ExtractedResponse, ExtractionPolicy, ProviderResponse
from .exceptions import ResponseExtractionError

if TYPE_CHECKING:
    from .secrets import SecretLease


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?([\s\S]*?)\n?```\s*$", re.IGNORECASE)
_LEADING_THINK_RE = re.compile(r"^\s*<think>[\s\S]*?</think>\s*", re.IGNORECASE)
_FINAL_TEXT_PART_TYPES = frozenset({"text", "output_text"})
_REASONING_PART_TYPES = frozenset(
    {"analysis", "reasoning", "reasoning_text", "thinking"}
)
_SECRET_RESPONSE_FIELDS = frozenset(
    {
        "apikey",
        "key",
        "accesstoken",
        "refreshtoken",
        "token",
        "secret",
        "password",
        "authorization",
        "credential",
        "credentials",
    }
)


def redact_provider_response_evidence(
    value: Any,
    *,
    known_secrets: tuple[str, ...] = (),
) -> Any:
    """Copy provider JSON while removing credentials before persistence.

    Usage counters such as ``prompt_tokens`` are numeric public evidence and
    remain intact. The built-in adapter also supplies the exact outbound
    credential so an echo under an otherwise innocent field is redacted.
    """

    secrets = tuple(secret for secret in known_secrets if secret)
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            normalized = "".join(
                character for character in str(key).lower() if character.isalnum()
            )
            secret_field = (
                normalized in _SECRET_RESPONSE_FIELDS
                or normalized.startswith("authorization")
                or normalized.endswith(
                    (
                        "apikey",
                        "accesstoken",
                        "refreshtoken",
                        "secret",
                        "password",
                        "credential",
                        "credentials",
                    )
                )
            )
            if secret_field and not (
                child is None or isinstance(child, (bool, int, float))
            ):
                cleaned[str(key)] = "[redacted]"
            else:
                cleaned[str(key)] = redact_provider_response_evidence(
                    child,
                    known_secrets=secrets,
                )
        return cleaned
    if isinstance(value, (list, tuple)):
        return [
            redact_provider_response_evidence(child, known_secrets=secrets)
            for child in value
        ]
    if isinstance(value, str):
        cleaned = value
        for secret in secrets:
            cleaned = cleaned.replace(secret, "[redacted]")
        if cleaned.lstrip().lower().startswith(("bearer ", "basic ")):
            return "[redacted]"
        return cleaned
    return value


def redact_provider_boundary_evidence(
    value: Any,
    *,
    secret_lease: "SecretLease | None" = None,
) -> Any:
    """Sanitize provider evidence at the durable application boundary.

    Adapters should redact their own outbound credential too, but this second
    boundary protects injected or third-party adapters.  The lease performs
    the exact-secret replacement internally without another reveal/use.
    """

    if secret_lease is not None:
        return secret_lease.redact_provider_evidence(value)
    return redact_provider_response_evidence(value)


def assistant_message_final_text(
    message: Mapping[str, Any],
) -> tuple[str | None, bool]:
    """Read only explicitly final assistant text from one message.

    OpenAI-compatible services sometimes represent ``message.content`` as a
    typed part array. A part's mere possession of a ``text`` or ``content``
    field is not evidence that it is final output: reasoning parts can use the
    same field names. Only the documented final-text part types are eligible;
    reasoning and unknown types remain raw evidence and are never promoted to
    canonical or correction input.
    """

    reasoning_present = any(
        isinstance(message.get(key), str) and bool(message[key].strip())
        for key in ("reasoning", "reasoning_content")
    )
    content = message.get("content")
    if isinstance(content, str):
        return (content if content.strip() else None), reasoning_present
    if not isinstance(content, list):
        return None, reasoning_present

    fragments: list[str] = []
    for part in content:
        if not isinstance(part, Mapping):
            continue
        part_type = part.get("type")
        if part_type in _REASONING_PART_TYPES:
            if any(
                isinstance(part.get(key), str) and bool(part[key].strip())
                for key in ("text", "content")
            ):
                reasoning_present = True
            continue
        if part_type not in _FINAL_TEXT_PART_TYPES:
            continue
        text = part.get("text")
        if isinstance(text, str):
            fragments.append(text)
    combined = "".join(fragments)
    return (combined if combined.strip() else None), reasoning_present


def extract_assistant_text(response: ProviderResponse | dict[str, Any]) -> str:
    """Extract Chat Completions assistant content from documented shapes."""

    raw = response.raw if isinstance(response, ProviderResponse) else response
    if not isinstance(raw, dict):
        raise ResponseExtractionError("Provider envelope must be an object")
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ResponseExtractionError("Provider envelope has no first choice")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ResponseExtractionError("Provider choice has no assistant message")
    final_text, _reasoning_present = assistant_message_final_text(message)
    if final_text is not None:
        return final_text
    raise ResponseExtractionError("Assistant message contains no textual content")


def extract_json_response(
    response: ProviderResponse | dict[str, Any],
    *,
    policy: ExtractionPolicy | None = None,
) -> ExtractedResponse:
    return parse_json_text(extract_assistant_text(response), policy=policy)


def parse_json_text(
    text: str,
    *,
    policy: ExtractionPolicy | None = None,
) -> ExtractedResponse:
    """Parse one JSON document using only explicitly enabled transformations."""

    if not isinstance(text, str) or not text.strip():
        raise ResponseExtractionError("Assistant content is blank")
    policy = policy or ExtractionPolicy()
    normalized = text.strip()
    transformations: list[str] = []

    if policy.reasoning_tags:
        stripped_any = False
        while True:
            match = _LEADING_THINK_RE.match(normalized)
            if match is None:
                break
            normalized = normalized[match.end():].strip()
            stripped_any = True
        if stripped_any:
            transformations.append("removed_leading_think_blocks")

    if policy.markdown_fence:
        fence = _FENCE_RE.fullmatch(normalized)
        if fence is not None:
            normalized = fence.group(1).strip()
            transformations.append("removed_json_markdown_fence")

    if policy.embedded_json:
        normalized, changed = _extract_embedded_document(normalized)
        if changed:
            transformations.append("extracted_embedded_json_document")

    try:
        value = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ResponseExtractionError(
            f"Assistant content is not valid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    return ExtractedResponse(
        raw_text=text,
        normalized_text=normalized,
        value=value,
        transformations=tuple(transformations),
    )


def _extract_embedded_document(text: str) -> tuple[str, bool]:
    decoder = json.JSONDecoder()
    candidates = [index for index, char in enumerate(text) if char in "{["]
    for start in candidates:
        try:
            _value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        document = text[start:start + end]
        changed = bool(text[:start].strip() or text[start + end:].strip())
        return document, changed
    return text, False
