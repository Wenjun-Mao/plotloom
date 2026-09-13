"""Durable SQLite control plane for MiniMax-H3 gateway jobs."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .contracts import (
    EXPIRED_JOB_RECORD_RETENTION_DAYS,
    GATEWAY_KEYFRAME_RETENTION_DAYS,
    MANAGED_OUTPUT_RETENTION_HOURS,
    GatewayError,
)


class GatewayStore:
    """Small durable control plane; no raw ComfyUI payloads or secrets."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                  id TEXT PRIMARY KEY, mime_type TEXT NOT NULL, width INTEGER NOT NULL,
                  height INTEGER NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL,
                  purge_pending INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
                  profile_id TEXT NOT NULL, aspect_policy TEXT NOT NULL, prompt TEXT NOT NULL,
                  seed INTEGER NOT NULL, prepared_input_name TEXT NOT NULL, status TEXT NOT NULL,
                  idempotency_key TEXT, request_hash TEXT,
                  comfy_prompt_id TEXT, output_filename TEXT, output_subfolder TEXT,
                  output_type TEXT, managed_output_name TEXT, output_sha256 TEXT,
                  output_size_bytes INTEGER, output_expires_at TEXT,
                  output_expired_at TEXT, error_code TEXT,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        """Apply additive gateway-local schema changes without rewriting jobs."""

        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)")}
        asset_columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(assets)")}
        if "purge_pending" not in asset_columns:
            connection.execute("ALTER TABLE assets ADD COLUMN purge_pending INTEGER NOT NULL DEFAULT 0")
        if "idempotency_key" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN idempotency_key TEXT")
        if "request_hash" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN request_hash TEXT")
        if "managed_output_name" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN managed_output_name TEXT")
        if "output_sha256" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN output_sha256 TEXT")
        if "output_size_bytes" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN output_size_bytes INTEGER")
        if "output_expires_at" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN output_expires_at TEXT")
        if "output_expired_at" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN output_expired_at TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS jobs_idempotency_key_unique "
            "ON jobs(idempotency_key) WHERE idempotency_key IS NOT NULL"
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def put_asset(
        self, *, asset_id: str, mime_type: str, width: int, height: int, digest: str, path: Path
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assets (id, mime_type, width, height, sha256, path) VALUES (?, ?, ?, ?, ?, ?)",
                (asset_id, mime_type, width, height, digest, str(path)),
            )
        return self.get_asset(asset_id)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM assets WHERE id = ? AND purge_pending = 0", (asset_id,)
            ).fetchone()
        if row is None:
            raise GatewayError("asset_not_found", 404)
        return dict(row)

    def queue_counts(self) -> tuple[int, int]:
        """Return queued and active work without exposing prompts or assets."""

        with self._connect() as connection:
            queued = int(connection.execute("SELECT COUNT(*) FROM jobs WHERE status = 'queued'").fetchone()[0])
            active = int(connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN "
                "('submitting', 'submitted', 'running', 'transfer_pending')"
            ).fetchone()[0])
        return queued, active

    def reserve_job(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Persist a no-provider-call reservation or return an idempotent job."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            key = values.get("idempotency_key")
            if isinstance(key, str):
                row = connection.execute(
                    "SELECT * FROM jobs WHERE idempotency_key = ?", (key,)
                ).fetchone()
                if row is not None:
                    existing = dict(row)
                    if existing.get("request_hash") != values.get("request_hash"):
                        connection.rollback()
                        raise GatewayError("idempotency_conflict", 409)
                    connection.commit()
                    return existing, False
            asset = connection.execute(
                "SELECT id FROM assets WHERE id = ? AND purge_pending = 0", (values["asset_id"],)
            ).fetchone()
            if asset is None:
                connection.rollback()
                raise GatewayError("asset_not_found", 404)
            connection.execute(
                """INSERT INTO jobs
                (id, asset_id, profile_id, aspect_policy, prompt, seed, prepared_input_name,
                 status, idempotency_key, request_hash)
                VALUES (:id, :asset_id, :profile_id, :aspect_policy, :prompt, :seed,
                        :prepared_input_name, 'reserved', :idempotency_key, :request_hash)""",
                values,
            )
            connection.commit()
        return self.get_job(values["id"]), True

    def claim_next_queued(self) -> dict[str, Any] | None:
        """Claim one FIFO job before the only possible outbound ComfyUI POST."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY rowid ASC LIMIT 1"
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            job_id = str(row["id"])
            updated = connection.execute(
                "UPDATE jobs SET status = 'submitting', updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND status = 'queued'",
                (job_id,),
            )
            if updated.rowcount != 1:
                connection.rollback()
                return None
            connection.commit()
        return self.get_job(job_id)

    def recover_interrupted_dispatches(self) -> None:
        """Never replay a job that may have crossed an outbound-call boundary."""

        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'outcome_unknown', "
                "error_code = COALESCE(error_code, 'gateway_restart_before_known_submission'), "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE status IN ('reserved', 'submitting')"
            )

    def list_active_jobs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status IN "
                "('submitted', 'running', 'transfer_pending') ORDER BY rowid ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def cancel_queued_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE jobs SET status = 'cancelled', error_code = 'cancelled_while_queued', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'queued'",
                (job_id,),
            )
            if updated.rowcount != 1:
                row = connection.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
                if row is None:
                    raise GatewayError("job_not_found", 404)
                raise GatewayError("job_not_cancellable", 409)
        return self.get_job(job_id)

    def mark_managed_output(
        self, job_id: str, *, output_name: str, digest: str, size_bytes: int
    ) -> dict[str, Any]:
        """Publish only a gateway-owned output after source removal succeeds."""

        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'succeeded', managed_output_name = ?, "
                "output_sha256 = ?, output_size_bytes = ?, "
                "output_expires_at = datetime('now', ?), error_code = NULL, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (output_name, digest, size_bytes, f"+{MANAGED_OUTPUT_RETENTION_HOURS} hours", job_id),
            )
        return self.get_job(job_id)

    def list_expired_managed_outputs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status = 'succeeded' "
                "AND output_expires_at IS NOT NULL "
                "AND output_expires_at <= CURRENT_TIMESTAMP ORDER BY rowid ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_output_expired(self, job_id: str, *, error_code: str) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'output_expired', error_code = ?, "
                "output_expired_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (error_code, job_id),
            )
        return self.get_job(job_id)

    def list_output_expired_jobs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status = 'output_expired' ORDER BY rowid ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_purgeable_expired_job_records(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status = 'output_expired' "
                "AND output_expired_at IS NOT NULL "
                "AND output_expired_at <= datetime('now', ?) ORDER BY rowid ASC",
                (f"-{EXPIRED_JOB_RECORD_RETENTION_DAYS} days",),
            ).fetchall()
        return [dict(row) for row in rows]

    def purge_expired_job_record(self, job_id: str) -> bool:
        """Delete one due job row after its post-output audit interval."""

        with self._connect() as connection:
            deleted = connection.execute(
                "DELETE FROM jobs WHERE id = ? AND status = 'output_expired' "
                "AND output_expired_at IS NOT NULL "
                "AND output_expired_at <= datetime('now', ?)",
                (job_id, f"-{EXPIRED_JOB_RECORD_RETENTION_DAYS} days"),
            )
        return deleted.rowcount == 1

    def claim_asset_after_last_output_expiry(self, asset_id: str) -> bool:
        """Make a keyframe unavailable after all linked videos have expired."""

        with self._connect() as connection:
            claimed = connection.execute(
                "UPDATE assets SET purge_pending = 1 WHERE id = ? "
                "AND purge_pending = 0 AND NOT EXISTS "
                "(SELECT 1 FROM jobs WHERE asset_id = ? AND status != 'output_expired')",
                (asset_id, asset_id),
            )
        return claimed.rowcount == 1

    def claim_due_gateway_assets(self) -> int:
        """Atomically claim every gateway keyframe past its retention window."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            claimed = connection.execute(
                "UPDATE assets SET purge_pending = 1 WHERE purge_pending = 0 "
                "AND created_at <= datetime('now', ?)",
                (f"-{GATEWAY_KEYFRAME_RETENTION_DAYS} days",),
            )
            connection.commit()
        return claimed.rowcount

    def list_pending_asset_purges(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM assets WHERE purge_pending = 1 ORDER BY rowid ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_pending_unreferenced_asset(self, asset_id: str) -> bool:
        """Remove metadata only after its last job reference is gone."""

        with self._connect() as connection:
            deleted = connection.execute(
                "DELETE FROM assets WHERE id = ? AND purge_pending = 1 "
                "AND NOT EXISTS (SELECT 1 FROM jobs WHERE asset_id = ?)",
                (asset_id, asset_id),
            )
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
