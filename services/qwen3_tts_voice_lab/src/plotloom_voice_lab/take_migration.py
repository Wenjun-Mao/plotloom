"""Preserve V3 voices while adding durable takes and dispatch registration."""

import sqlite3


def migrate_takes(db: sqlite3.Connection) -> None:
    db.executescript("""BEGIN IMMEDIATE;
        CREATE TABLE voice_takes (
            id TEXT PRIMARY KEY, voice_id TEXT NOT NULL REFERENCES voices(id),
            text TEXT NOT NULL, reference_text TEXT NOT NULL,
            reference_path TEXT NOT NULL, reference_sha256 TEXT NOT NULL,
            seed INTEGER NOT NULL, engine_id TEXT NOT NULL,
            snapshot_json TEXT NOT NULL, delivery_json TEXT NOT NULL,
            execution_details TEXT, media_json TEXT,
            status TEXT NOT NULL, error_code TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX idx_takes_voice ON voice_takes(voice_id,created_at);
        CREATE TABLE dispatch_outbox (
            kind TEXT NOT NULL CHECK(kind IN ('generation','clone','take')),
            job_id TEXT NOT NULL, binding_hash TEXT, registered_at TEXT,
            created_at TEXT NOT NULL, PRIMARY KEY(kind,job_id)
        );
        CREATE TABLE execution_grants (
            grant_id TEXT PRIMARY KEY, kind TEXT NOT NULL, job_id TEXT NOT NULL,
            binding_hash TEXT NOT NULL, release_confirmed INTEGER NOT NULL DEFAULT 0,
            error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(kind,job_id)
        );
        CREATE UNIQUE INDEX one_unreleased_voice_grant
            ON execution_grants((1)) WHERE release_confirmed=0;
        CREATE TRIGGER generation_dispatch AFTER INSERT ON generations
        WHEN NEW.status='queued' BEGIN
            INSERT INTO dispatch_outbox(kind,job_id,created_at)
                VALUES ('generation',NEW.id,NEW.created_at);
        END;
        CREATE TRIGGER clone_dispatch AFTER INSERT ON clone_trials
        WHEN NEW.status='queued' BEGIN
            INSERT INTO dispatch_outbox(kind,job_id,created_at)
                VALUES ('clone',NEW.id,NEW.created_at);
        END;
        CREATE TRIGGER take_dispatch AFTER INSERT ON voice_takes
        WHEN NEW.status='queued' BEGIN
            INSERT INTO dispatch_outbox(kind,job_id,created_at)
                VALUES ('take',NEW.id,NEW.created_at);
        END;
        PRAGMA user_version=4;
        COMMIT;
    """)
