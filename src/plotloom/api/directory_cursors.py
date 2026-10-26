from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime

from fastapi import HTTPException, status


def _encode_project_cursor(cursor: tuple[datetime, str] | None) -> str | None:
    if cursor is None:
        return None
    created_at, project_id = cursor
    payload = json.dumps(
        {"createdAt": created_at.isoformat(), "id": project_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_project_cursor(value: str | None) -> tuple[datetime, str] | None:
    if value is None:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if set(payload) != {"createdAt", "id"} or not isinstance(payload["id"], str):
            raise ValueError("wrong cursor shape")
        created_at = datetime.fromisoformat(payload["createdAt"])
        if created_at.tzinfo is not None:
            raise ValueError(
                "cursor timestamp must use the database's local UTC representation"
            )
        if not payload["id"]:
            raise ValueError("blank project ID")
        return created_at, payload["id"]
    except (
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid project cursor",
        ) from error
