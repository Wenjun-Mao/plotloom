"""Bounded projections over the live gateway database, without initialization."""
from __future__ import annotations

import base64
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..naming import is_gateway_job_id, is_owned_storage_name

FIELDS = (
    "id", "backend", "input_mode", "h3_contract", "quality", "resolution",
    "aspect_policy", "seed", "requested_duration_seconds", "frame_count", "fps",
    "status", "comfy_prompt_id", "generation_submitted_at_ms", "generation_completed_at_ms",
    "managed_output_name", "output_sha256", "output_size_bytes", "output_mime_type",
    "output_expires_at", "error_code", "created_at", "updated_at",
)
STATUSES = {
    "queued", "submitting", "submitted", "running", "transfer_pending",
    "succeeded", "failed", "cancelled", "outcome_unknown",
}


class ReadError(Exception):
    def __init__(self, code: str, status: int = 503):
        self.code, self.status = code, status


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def iso(value) -> str | None:
    parsed = timestamp(value)
    return parsed.isoformat() if parsed else None


class DashboardReader:
    def __init__(self, data_root: Path):
        self.root = data_root.absolute()
        self.database = self.root / "gateway.sqlite3"
        self.outputs = self.root / "outputs"

    @contextmanager
    def connection(self):
        db = None
        try:
            if self.database.is_symlink() or self.root.is_symlink():
                raise ReadError("dashboard_database_unavailable")
            db = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True, timeout=1)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            columns = {r[1] for r in db.execute("PRAGMA table_info(jobs)")}
            lane = {r[1] for r in db.execute("PRAGMA table_info(generation_lane)")}
            if not set(FIELDS + ("prompt", "execution_snapshot_json")) <= columns or not {
                "sequence", "owner", "job_kind", "job_id", "state", "error_code", "created_at",
            } <= lane:
                raise ReadError("dashboard_schema_unavailable")
            yield db
        except sqlite3.Error as error:
            code = "dashboard_database_busy" if "locked" in str(error).lower() else "dashboard_database_unavailable"
            raise ReadError(code) from error
        finally:
            if db is not None:
                db.close()

    def overview(self) -> dict:
        with self.connection() as db:
            counts = dict(db.execute("SELECT state,COUNT(*) FROM generation_lane GROUP BY state"))
            rows = db.execute(
                "SELECT sequence,owner,job_kind,job_id,state,error_code,created_at "
                "FROM generation_lane WHERE state IN ('queued','active') ORDER BY sequence LIMIT 100"
            ).fetchall()
            queue = [{
                "sequence": r["sequence"], "owner": r["owner"], "kind": r["job_kind"],
                "jobId": r["job_id"], "state": r["state"], "error": r["error_code"],
                "createdAt": iso(r["created_at"]), "queueAhead": i,
            } for i, r in enumerate(rows)]
        return {"observedAt": utc_now().isoformat(), "database": "ok", "queue": queue,
                "queued": counts.get("queued", 0), "active": counts.get("active", 0),
                "queueTruncated": len(queue) < counts.get("queued", 0) + counts.get("active", 0)}

    def jobs(self, *, search="", backend="", status="", cursor="", limit=50) -> dict:
        if backend not in {"", "h3_video", "qwen_image"} or status not in STATUSES | {""}:
            raise ReadError("dashboard_filter_invalid", 422)
        if not 1 <= limit <= 100 or len(search) > 80 or len(cursor) > 512:
            raise ReadError("dashboard_filter_invalid", 422)
        clauses, values = [], []
        for field, value in (("backend", backend), ("status", status)):
            if value:
                clauses.append(field + "=?")
                values.append(value)
        if search:
            clauses.append("instr(id,?)>0")
            values.append(search)
        if cursor:
            try:
                created, job_id = json.loads(base64.urlsafe_b64decode(cursor))
                if not isinstance(created, str) or len(created) > 40 or not is_gateway_job_id(job_id):
                    raise ValueError()
            except (ValueError, TypeError, json.JSONDecodeError):
                raise ReadError("dashboard_cursor_invalid", 422) from None
            clauses.append("(created_at,id)<(?,?)")
            values.extend((created, job_id))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connection() as db:
            rows = db.execute(
                "SELECT " + ",".join(FIELDS) + " FROM jobs" + where
                + " ORDER BY created_at DESC,id DESC LIMIT ?", (*values, limit + 1),
            ).fetchall()
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = base64.urlsafe_b64encode(json.dumps([last["created_at"], last["id"]]).encode()).decode()
        return {"jobs": [self.project(dict(r)) for r in rows[:limit]], "nextCursor": next_cursor,
                "observedAt": utc_now().isoformat()}

    def job(self, job_id: str) -> dict:
        if not is_gateway_job_id(job_id):
            raise ReadError("job_not_found", 404)
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise ReadError("job_not_found", 404)
        return dict(row)

    def detail(self, job_id: str) -> dict:
        row = self.job(job_id)
        result = self.project(row)
        try:
            snapshot = json.loads(row["execution_snapshot_json"])
            result["frozenSettings"] = {
                key: snapshot[key] for key in (
                    "generationContractVersion", "workflowRendererVersion", "quality",
                    "resolution", "width", "height", "fps",
                ) if key in snapshot and isinstance(snapshot[key], (str, int, float, bool, type(None)))
            } if isinstance(snapshot, dict) else None
        except (TypeError, ValueError):
            result["frozenSettings"] = None
        return result

    def output_name(self, row: dict) -> str | None:
        expected = {"h3_video": "video/mp4", "qwen_image": "image/png"}
        if row["backend"] not in expected or row.get("output_mime_type") != expected[row["backend"]]:
            return None
        suffix = ".mp4" if row["backend"] == "h3_video" else ".png"
        name = row.get("managed_output_name")
        return name if is_gateway_job_id(row["id"]) and is_owned_storage_name(
            name, object_id=row["id"], suffixes=(suffix,),
        ) else None

    def availability(self, row: dict) -> str:
        if row["status"] != "succeeded":
            return "not_ready"
        expiry = timestamp(row.get("output_expires_at"))
        if not expiry:
            return "unavailable"
        if expiry <= utc_now():
            return "expired"
        name = self.output_name(row)
        if not name or self.outputs.is_symlink():
            return "unavailable"
        path = self.outputs / name
        return "available" if path.is_file() and not path.is_symlink() else "missing"

    def project(self, row: dict) -> dict:
        now_ms = int(utc_now().timestamp() * 1000)
        start, end = row["generation_submitted_at_ms"], row["generation_completed_at_ms"]
        active = row["status"] in {"submitted", "running", "transfer_pending"}
        elapsed = max(0, (end if isinstance(end, int) else now_ms) - start) if (
            isinstance(start, int) and (isinstance(end, int) or active)
        ) else None
        created = timestamp(row["created_at"])
        wait_end = start if isinstance(start, int) else now_ms if row["status"] == "queued" else None
        waiting = max(0, wait_end - int(created.timestamp() * 1000)) if created and wait_end else None
        video = row["backend"] == "h3_video"
        return {
            "id": row["id"], "backend": row["backend"], "status": row["status"],
            "inputMode": "image_voice" if row["h3_contract"] == "ref2va" else row["input_mode"],
            "quality": row["quality"] if video else None, "resolution": row["resolution"],
            "aspectPolicy": row["aspect_policy"], "seed": row["seed"],
            "requestedDurationSeconds": row["requested_duration_seconds"] if video else None,
            "expectedDurationSeconds": row["frame_count"] / row["fps"] if video and row["fps"] else None,
            "frameCount": row["frame_count"] if video else None, "fps": row["fps"] if video else None,
            "createdAt": iso(row["created_at"]), "updatedAt": iso(row["updated_at"]),
            "generationSubmittedAt": datetime.fromtimestamp(start / 1000, timezone.utc).isoformat() if isinstance(start, int) else None,
            "generationCompletedAt": datetime.fromtimestamp(end / 1000, timezone.utc).isoformat() if isinstance(end, int) else None,
            "generationElapsedMs": elapsed, "waitingElapsedMs": waiting,
            "error": row["error_code"], "comfyPromptId": row["comfy_prompt_id"],
            "output": self.availability(row), "outputExpiresAt": iso(row["output_expires_at"]),
            "outputSizeBytes": row["output_size_bytes"], "outputSha256": row["output_sha256"],
        }
