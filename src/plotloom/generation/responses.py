"""Explicit response-envelope and JSON-document extraction."""

from __future__ import annotations

import json
import re
from typing import Any

from .contracts import ExtractedResponse, ExtractionPolicy, ProviderResponse
from .exceptions import ResponseExtractionError


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?([\s\S]*?)\n?```\s*$", re.IGNORECASE)
_LEADING_THINK_RE = re.compile(r"^\s*<think>[\s\S]*?</think>\s*", re.IGNORECASE)


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
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        fragments: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                fragments.append(text)
            elif isinstance(part.get("content"), str):
                fragments.append(part["content"])
        combined = "".join(fragments)
        if combined.strip():
            return combined
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
