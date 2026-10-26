from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request


def _session_api_key(request: Request) -> str | None:
    value = (request.headers.get("X-Plotloom-Session-API-Key") or "").strip()
    if len(value) > 4096:
        raise HTTPException(status_code=400, detail="session API key is too long")
    return value or None


def _normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Idempotency-Key must not be blank")
    if len(normalized) > 255:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key must be at most 255 characters"
        )
    return normalized


def _submit_with_optional_session_key(
    scheduler: Any, resource_id: str, request: Request
) -> Any:
    session_key = _session_api_key(request)
    if session_key is None:
        return scheduler.submit(resource_id)
    return scheduler.submit(resource_id, session_api_key=session_key)
