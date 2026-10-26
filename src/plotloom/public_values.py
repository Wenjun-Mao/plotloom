from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlparse

SECRET_SETTING_NAMES = frozenset(
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


def is_secret_setting_name(name: object) -> bool:
    normalized = "".join(
        character for character in str(name).lower() if character.isalnum()
    )
    return (
        normalized in SECRET_SETTING_NAMES
        or normalized.startswith("authorization")
        or normalized.endswith(
            ("apikey", "token", "secret", "password", "credential", "credentials")
        )
    )


def contains_secret_setting(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if is_secret_setting_name(key):
                return True
            if contains_secret_setting(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(contains_secret_setting(child) for child in value)
    return False


def contains_secret_value(value: Any) -> bool:
    """Detect recognizable credentials without guessing arbitrary prose tokens."""

    if isinstance(value, dict):
        return any(contains_secret_value(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_secret_value(child) for child in value)
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    lowered = candidate.lower()
    # Secrets frequently arrive embedded in untrusted prose such as an
    # executor's completion note. Detect only conventional credential forms at
    # word boundaries so ordinary language stays admissible.
    if re.search(
        r"\b(?:bearer\s+\S+|basic\s+[A-Za-z0-9+/]{8,}={0,2}|(?:sk[-_]|xai-|hf_|aiza)[A-Za-z0-9_-]+)",
        candidate,
        flags=re.IGNORECASE,
    ):
        return True
    if "-----begin private key-----" in lowered:
        return True

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        if parsed.username or parsed.password:
            return True
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        if any(is_secret_setting_name(key) for key, _ in query_items):
            return True

    return any(
        is_secret_setting_name(match.group(1))
        for match in re.finditer(
            r"(?<![A-Za-z0-9_-])([A-Za-z][A-Za-z0-9_-]*)\s*=(?!=)", candidate
        )
    )


def validate_public_api_root(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "provider base URLs must be HTTP(S) roots with a host and without credentials, query, or fragment"
        )
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("provider base URLs must use a valid port") from error
    return normalized


def validate_public_base_urls(value: Any) -> None:
    """Apply the trusted HTTP(S)-root contract to nested public *BaseUrl fields."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = "".join(
                character for character in str(key).lower() if character.isalnum()
            )
            if normalized_key.endswith("baseurl"):
                if not isinstance(child, str):
                    raise ValueError("provider base URLs must be strings")
                validate_public_api_root(child)
            validate_public_base_urls(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate_public_base_urls(child)
