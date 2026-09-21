"""Durable SQLite control plane for MiniMax-H3 gateway jobs."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .contracts import (
    GATEWAY_KEYFRAME_RETENTION_DAYS,
    GATEWAY_JOB_RECORD_RETENTION_DAYS,
    MANAGED_OUTPUT_RETENTION_HOURS,
    GatewayError,
)


def _has_retired_contract(connection: sqlite3.Connection) -> bool:
    """Identify a retired database before schema setup can touch it."""

    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "jobs" not in tables:
        return False
    columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)")}
    return "execution_snapshot_json" not in columns


class GatewayStore:
    """Small durable control plane; no raw Comfy payloads or secrets.

    Image inputs are ordinary assets with immutable start/end bindings, rather
    than a special asset type embedded in each job record.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._connect() as connection:
            # A release cutover must never alter an old control-plane file on
            # the way to refusing it. The operator archives that state, then
            # starts this contract with a new empty data directory.
            if _has_retired_contract(connection):
                raise RuntimeError(
                    "gateway state reset required: retired profileId state cannot use the quality contract"
                )
            connection.executescript(_CURRENT_SCHEMA)
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        """Additive control-plane migration; retired profile state still refuses."""

        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)")}
        asset_columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(assets)")}
        if "purge_pending" not in asset_columns or "execution_snapshot_json" not in columns:
            raise RuntimeError(
                "gateway state reset required: retired profileId state cannot use the quality contract"
            )
        additions = {
            "backend": "TEXT NOT NULL DEFAULT 'h3_video'",
            "background_mode": "TEXT",
            "output_mime_type": "TEXT",
            "output_width": "INTEGER",
            "output_height": "INTEGER",
        }
        for name, declaration in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE jobs ADD COLUMN {name} {declaration}")
        frame_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(job_frame_bindings)")
        }
        # SQLite cannot widen the historical role CHECK in place. A source
        # reference is modeled as the existing start role in old databases;
        # new databases have the wider check in _CURRENT_SCHEMA.
        if "role" not in frame_columns:
            raise RuntimeError("gateway state reset required: frame binding contract is invalid")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def put_asset(self, *, asset_id: str, mime_type: str, width: int, height: int, digest: str, path: Path) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assets (id, mime_type, width, height, sha256, path) VALUES (?, ?, ?, ?, ?, ?)",
                (asset_id, mime_type, width, height, digest, str(path)),
            )
        return self.get_asset(asset_id)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM assets WHERE id = ? AND purge_pending = 0", (asset_id,)).fetchone()
        if row is None:
            raise GatewayError("asset_not_found", 404)
        return dict(row)

    def queue_counts(self) -> tuple[int, int]:
        with self._connect() as connection:
            queued = int(connection.execute("SELECT COUNT(*) FROM jobs WHERE status = 'queued'").fetchone()[0])
            active = int(connection.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('submitting', 'submitted', 'running', 'transfer_pending')").fetchone()[0])
        return queued, active

    def reserve_job(self, values: dict[str, Any], frames: list[dict[str, str]]) -> dict[str, Any]:
        """Atomically admit one H3 or Qwen job and its image bindings."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for frame in frames:
                asset = connection.execute("SELECT id FROM assets WHERE id = ? AND purge_pending = 0", (frame["asset_id"],)).fetchone()
                if asset is None:
                    connection.rollback()
                    raise GatewayError("asset_not_found", 404)
            connection.execute(
                """INSERT INTO jobs (id, backend, input_mode, quality, resolution, execution_snapshot_json, aspect_policy, background_mode, prompt, seed,
                   requested_duration_seconds, frame_count, fps, status)
                   VALUES (:id, :backend, :input_mode, :quality, :resolution, :execution_snapshot_json, :aspect_policy, :background_mode, :prompt, :seed,
                   :requested_duration_seconds, :frame_count, :fps, 'queued')""", values,
            )
            connection.executemany(
                "INSERT INTO job_frame_bindings (job_id, role, asset_id, prepared_input_name) VALUES (:job_id, :role, :asset_id, :prepared_input_name)",
                [{**frame, "job_id": values["id"]} for frame in frames],
            )
            connection.commit()
        return self.get_job(values["id"])

    def get_job_frames(self, job_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT bindings.role, bindings.asset_id, bindings.prepared_input_name,
                   assets.id, assets.mime_type, assets.width, assets.height, assets.sha256, assets.path
                   FROM job_frame_bindings bindings JOIN assets ON assets.id = bindings.asset_id
                   WHERE bindings.job_id = ?
                   ORDER BY CASE bindings.role WHEN 'start' THEN 0 WHEN 'end' THEN 1 ELSE 2 END""", (job_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def claim_next_queued(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM jobs WHERE status = 'queued' ORDER BY rowid ASC LIMIT 1").fetchone()
            if row is None:
                connection.commit()
                return None
            job_id = str(row["id"])
            updated = connection.execute("UPDATE jobs SET status = 'submitting', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'queued'", (job_id,))
            if updated.rowcount != 1:
                connection.rollback()
                return None
            connection.commit()
        return self.get_job(job_id)

    def recover_interrupted_dispatches(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'outcome_unknown', error_code = COALESCE(error_code, 'gateway_restart_before_known_submission'), updated_at = CURRENT_TIMESTAMP WHERE status IN ('reserved', 'submitting')"
            )

    def list_active_jobs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs WHERE status IN ('submitted', 'running', 'transfer_pending') ORDER BY rowid ASC").fetchall()
        return [dict(row) for row in rows]

    def cancel_queued_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            updated = connection.execute("UPDATE jobs SET status = 'cancelled', error_code = 'cancelled_while_queued', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'queued'", (job_id,))
            if updated.rowcount != 1:
                row = connection.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
                if row is None:
                    raise GatewayError("job_not_found", 404)
                raise GatewayError("job_not_cancellable", 409)
        return self.get_job(job_id)

    def mark_managed_output(
        self, job_id: str, *, output_name: str, digest: str, size_bytes: int,
        mime_type: str | None = None, width: int | None = None, height: int | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'succeeded', managed_output_name = ?, output_sha256 = ?, output_size_bytes = ?, output_mime_type = ?, output_width = ?, output_height = ?, output_expires_at = datetime('now', ?), error_code = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (output_name, digest, size_bytes, mime_type, width, height, f"+{MANAGED_OUTPUT_RETENTION_HOURS} hours", job_id),
            )
        return self.get_job(job_id)

    def list_expired_managed_outputs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs WHERE status = 'succeeded' AND output_expires_at IS NOT NULL AND output_expires_at <= CURRENT_TIMESTAMP ORDER BY rowid ASC").fetchall()
        return [dict(row) for row in rows]

    def output_is_retained(self, job_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 FROM jobs WHERE id = ? AND status = 'succeeded' AND output_expires_at IS NOT NULL AND output_expires_at > CURRENT_TIMESTAMP", (job_id,)).fetchone()
        return row is not None

    def list_purgeable_completed_job_records(self) -> list[dict[str, Any]]:
        audit_hours = GATEWAY_JOB_RECORD_RETENTION_DAYS * 24 - MANAGED_OUTPUT_RETENTION_HOURS
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs WHERE status = 'succeeded' AND output_expires_at IS NOT NULL AND output_expires_at <= datetime('now', ?) ORDER BY rowid ASC", (f"-{audit_hours} hours",)).fetchall()
        return [dict(row) for row in rows]

    def purge_completed_job_record(self, job_id: str) -> bool:
        audit_hours = GATEWAY_JOB_RECORD_RETENTION_DAYS * 24 - MANAGED_OUTPUT_RETENTION_HOURS
        with self._connect() as connection:
            deleted = connection.execute("DELETE FROM jobs WHERE id = ? AND status = 'succeeded' AND output_expires_at IS NOT NULL AND output_expires_at <= datetime('now', ?)", (job_id, f"-{audit_hours} hours"))
        return deleted.rowcount == 1

    def claim_asset_after_last_output_expiry(self, asset_id: str) -> bool:
        with self._connect() as connection:
            claimed = connection.execute(
                """UPDATE assets SET purge_pending = 1 WHERE id = ? AND purge_pending = 0
                   AND NOT EXISTS (
                     SELECT 1 FROM job_frame_bindings bindings JOIN jobs ON jobs.id = bindings.job_id
                     WHERE bindings.asset_id = ? AND (jobs.status != 'succeeded' OR jobs.output_expires_at IS NULL OR jobs.output_expires_at > CURRENT_TIMESTAMP)
                   )""", (asset_id, asset_id),
            )
        return claimed.rowcount == 1

    def claim_due_gateway_assets(self) -> int:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            claimed = connection.execute("UPDATE assets SET purge_pending = 1 WHERE purge_pending = 0 AND created_at <= datetime('now', ?)", (f"-{GATEWAY_KEYFRAME_RETENTION_DAYS} days",))
            connection.commit()
        return claimed.rowcount

    def list_pending_asset_purges(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM assets WHERE purge_pending = 1 ORDER BY rowid ASC").fetchall()
        return [dict(row) for row in rows]

    def delete_pending_unreferenced_asset(self, asset_id: str) -> bool:
        with self._connect() as connection:
            deleted = connection.execute("DELETE FROM assets WHERE id = ? AND purge_pending = 1 AND NOT EXISTS (SELECT 1 FROM job_frame_bindings WHERE asset_id = ?)", (asset_id, asset_id))
        return deleted.rowcount == 1

    def delete_unreferenced_asset(self, asset_id: str) -> bool:
        with self._connect() as connection:
            deleted = connection.execute("DELETE FROM assets WHERE id = ? AND NOT EXISTS (SELECT 1 FROM job_frame_bindings WHERE asset_id = ?)", (asset_id, asset_id))
        return deleted.rowcount == 1

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise GatewayError("job_not_found", 404)
        return dict(row)

    def update_job(self, job_id: str, *, status: str, **values: Any) -> dict[str, Any]:
        assignments = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params: list[Any] = [status]
        for name, value in values.items():
            assignments.append(f"{name} = ?")
            params.append(value)
        params.append(job_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?", params)
        return self.get_job(job_id)


_CURRENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY, mime_type TEXT NOT NULL, width INTEGER NOT NULL,
  height INTEGER NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL,
  purge_pending INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, backend TEXT NOT NULL DEFAULT 'h3_video' CHECK(backend IN ('h3_video', 'qwen_image')),
  input_mode TEXT NOT NULL CHECK(input_mode IN ('image', 'text')),
  quality INTEGER NOT NULL, resolution TEXT NOT NULL, execution_snapshot_json TEXT NOT NULL,
  aspect_policy TEXT, background_mode TEXT, prompt TEXT NOT NULL, seed INTEGER NOT NULL,
  requested_duration_seconds INTEGER NOT NULL, frame_count INTEGER NOT NULL, fps INTEGER NOT NULL,
  status TEXT NOT NULL, comfy_prompt_id TEXT, generation_submitted_at_ms INTEGER,
  generation_completed_at_ms INTEGER, output_filename TEXT, output_subfolder TEXT,
  output_type TEXT, managed_output_name TEXT, output_sha256 TEXT, output_size_bytes INTEGER,
  output_mime_type TEXT, output_width INTEGER, output_height INTEGER,
  output_expires_at TEXT, error_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS job_frame_bindings (
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK(role IN ('start', 'end', 'source')),
  asset_id TEXT NOT NULL REFERENCES assets(id), prepared_input_name TEXT NOT NULL,
  PRIMARY KEY(job_id, role)
);
CREATE INDEX IF NOT EXISTS job_frame_bindings_asset_idx ON job_frame_bindings(asset_id);
"""
