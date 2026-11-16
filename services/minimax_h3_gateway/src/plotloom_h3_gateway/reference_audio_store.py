"""One-to-many reference audio rows inside the gateway's existing transaction."""
from .contracts import GATEWAY_JOB_RECORD_RETENTION_DAYS

SCHEMA = """CREATE TABLE IF NOT EXISTS job_reference_audio_bindings (
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 3),
  speaker TEXT NOT NULL CHECK (length(trim(speaker)) > 0),
  source_sha256 TEXT NOT NULL, prepared_sha256 TEXT NOT NULL,
  source_size_bytes INTEGER NOT NULL, duration_ms INTEGER NOT NULL,
  source_name TEXT NOT NULL, prepared_input_name TEXT NOT NULL,
  released_at TEXT,
  PRIMARY KEY (job_id, ordinal), UNIQUE (job_id, speaker)
)"""

UNRELEASED = """NOT EXISTS (SELECT 1 FROM job_reference_audio_bindings audio
    WHERE audio.job_id=jobs.id AND audio.released_at IS NULL)"""

# UNKNOWN is not a terminal ownership proof, even after the audit deadline.
DUE = """((jobs.status='succeeded' AND jobs.output_expires_at IS NOT NULL
           AND jobs.output_expires_at <= CURRENT_TIMESTAMP)
    OR (jobs.status IN ('failed','cancelled') AND jobs.created_at <= datetime('now', ?)))
    AND NOT EXISTS (SELECT 1 FROM generation_lane lane
        WHERE lane.owner='gateway' AND lane.job_id=jobs.id AND lane.state!='done')"""


def insert(connection, job_id: str, bindings: list[dict]) -> None:
    connection.executemany(
        """INSERT INTO job_reference_audio_bindings
        (job_id,ordinal,speaker,source_sha256,prepared_sha256,source_size_bytes,
         duration_ms,source_name,prepared_input_name)
        VALUES (:job_id,:ordinal,:speaker,:source_sha256,:prepared_sha256,:source_size_bytes,
                :duration_ms,:source_name,:prepared_input_name)""",
        [{**binding, "job_id": job_id} for binding in bindings],
    )


def bindings(store, job_id: str) -> list[dict]:
    with store._connect() as connection:
        return rows(connection, job_id)


def rows(connection, job_id: str) -> list[dict]:
    return [dict(row) for row in connection.execute(
        "SELECT * FROM job_reference_audio_bindings WHERE job_id=? ORDER BY ordinal", (job_id,)
    ).fetchall()]


def due_jobs(store) -> list[str]:
    with store._connect() as connection:
        return [row["id"] for row in connection.execute(
            f"""SELECT jobs.id FROM jobs WHERE {DUE} AND NOT {UNRELEASED}
                ORDER BY jobs.rowid""", (f"-{GATEWAY_JOB_RECORD_RETENTION_DAYS} days",)
        ).fetchall()]


def is_due(connection, job_id: str) -> bool:
    return connection.execute(
        f"SELECT jobs.id FROM jobs WHERE jobs.id=? AND {DUE}",
        (job_id, f"-{GATEWAY_JOB_RECORD_RETENTION_DAYS} days"),
    ).fetchone() is not None
