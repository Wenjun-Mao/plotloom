"""One-time, checked transition from global casting rounds to projects."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE projects (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, brief TEXT NOT NULL,
    audition_text TEXT NOT NULL, revision INTEGER NOT NULL,
    selected_generation_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE candidate_slots (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL, direction TEXT NOT NULL, revision INTEGER NOT NULL,
    current_generation_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(project_id, ordinal)
);
CREATE TABLE generations (
    id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES candidate_slots(id) ON DELETE CASCADE,
    status TEXT NOT NULL, error_code TEXT, audition_text TEXT NOT NULL,
    brief TEXT NOT NULL,
    direction TEXT NOT NULL, seed INTEGER NOT NULL, model_id TEXT NOT NULL,
    model_revision TEXT NOT NULL, source_path TEXT, source_sha256 TEXT,
    source_duration_seconds REAL, source_sample_rate INTEGER,
    h3_path TEXT, h3_sha256 TEXT, h3_eligible INTEGER NOT NULL DEFAULT 0,
    preparation_version TEXT, removed_at TEXT, created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE selections (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    candidate_id TEXT, generation_id TEXT, selected_at TEXT NOT NULL
);
CREATE TABLE clone_trials (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL, generation_id TEXT NOT NULL,
    text TEXT NOT NULL, reference_text TEXT NOT NULL, seed INTEGER NOT NULL,
    model_id TEXT NOT NULL, model_revision TEXT NOT NULL,
    source_sha256 TEXT NOT NULL, reference_path TEXT, status TEXT NOT NULL,
    error_code TEXT, audio_path TEXT, audio_sha256 TEXT,
    duration_seconds REAL, sample_rate INTEGER,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE voices (
    id TEXT PRIMARY KEY, source_project_id TEXT NOT NULL,
    source_candidate_id TEXT NOT NULL, source_generation_id TEXT NOT NULL UNIQUE,
    transcript TEXT NOT NULL, brief TEXT NOT NULL, direction TEXT NOT NULL,
    model_id TEXT NOT NULL,
    model_revision TEXT NOT NULL, seed INTEGER NOT NULL,
    source_path TEXT NOT NULL, source_sha256 TEXT NOT NULL,
    h3_path TEXT NOT NULL, h3_sha256 TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE cleanup_debts (
    id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
);
CREATE INDEX idx_candidates_project ON candidate_slots(project_id, ordinal);
CREATE INDEX idx_generations_candidate ON generations(candidate_id, created_at);
CREATE INDEX idx_clones_project ON clone_trials(project_id, created_at);
"""


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _checked_hash(path: str | None, expected: str | None, root: Path) -> None:
    if not path or not expected:
        raise ValueError("legacy.audio_missing")
    file = Path(path)
    if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()) or not file.is_file():
        raise ValueError("legacy.audio_outside_managed_root")
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("legacy.audio_corrupt")


def _migrate_legacy(db: sqlite3.Connection, root: Path) -> None:
    db.executescript("""BEGIN IMMEDIATE;
        ALTER TABLE rounds RENAME TO legacy_rounds;
        ALTER TABLE candidates RENAME TO legacy_candidates;
        ALTER TABLE selections RENAME TO legacy_selections;
        ALTER TABLE clone_trials RENAME TO legacy_clone_trials;
    """ + SCHEMA)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    project_id = _new_id("vp")
    rounds = db.execute("SELECT * FROM legacy_rounds ORDER BY created_at, id").fetchall()
    latest_text = rounds[-1]["audition_text"] if rounds else ""
    db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)", (
        project_id, "Voice Lab pilot · 2026-09-26", "", latest_text, 1, None, stamp, stamp,
    ))
    candidate_to_generation: dict[str, str] = {}
    ordinal = 0
    for round_row in rounds:
        for old in db.execute(
            "SELECT * FROM legacy_candidates WHERE round_id=? ORDER BY ordinal", (round_row["id"],)
        ).fetchall():
            ordinal += 1
            generation_id = _new_id("vg")
            candidate_to_generation[old["id"]] = generation_id
            status = "interrupted" if old["status"] in {"queued", "running"} else old["status"]
            if old["source_path"] or old["source_sha256"]:
                _checked_hash(old["source_path"], old["source_sha256"], root)
            if old["h3_path"] or old["h3_sha256"]:
                _checked_hash(old["h3_path"], old["h3_sha256"], root)
            if status == "completed" and not old["source_path"]:
                raise ValueError("legacy.audio_missing")
            current = generation_id if status == "completed" else None
            db.execute("INSERT INTO candidate_slots VALUES (?,?,?,?,?,?,?,?)", (
                old["id"], project_id, ordinal, old["direction"], 1, current,
                old["created_at"], old["updated_at"],
            ))
            db.execute("""INSERT INTO generations VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                generation_id, old["id"], status,
                "generation.interrupted" if status == "interrupted" else old["error_code"],
                round_row["audition_text"], "", old["direction"], old["seed"], old["model_id"],
                old["model_revision"], old["source_path"], old["source_sha256"],
                old["source_duration_seconds"], old["source_sample_rate"], old["h3_path"],
                old["h3_sha256"], old["h3_eligible"], old["preparation_version"], None,
                old["created_at"], old["updated_at"],
            ))
    for old in db.execute("SELECT * FROM legacy_selections ORDER BY rowid").fetchall():
        generation_id = candidate_to_generation.get(old["candidate_id"])
        if generation_id:
            db.execute("INSERT INTO selections VALUES (?,?,?,?,?)", (
                old["id"], project_id, old["candidate_id"], generation_id, old["selected_at"],
            ))
            valid = db.execute("SELECT status FROM generations WHERE id=?", (generation_id,)).fetchone()
            if valid["status"] == "completed":
                db.execute("UPDATE projects SET selected_generation_id=? WHERE id=?", (generation_id, project_id))
    for old in db.execute("SELECT * FROM legacy_clone_trials").fetchall():
        generation_id = candidate_to_generation.get(old["candidate_id"])
        if not generation_id:
            raise ValueError("legacy.clone_source_missing")
        source = db.execute("SELECT audition_text,source_path FROM generations WHERE id=?", (generation_id,)).fetchone()
        status = "interrupted" if old["status"] in {"queued", "running"} else old["status"]
        if old["audio_path"] or old["audio_sha256"]:
            _checked_hash(old["audio_path"], old["audio_sha256"], root)
        if status == "completed" and not old["audio_path"]:
            raise ValueError("legacy.audio_missing")
        db.execute("""INSERT INTO clone_trials VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            old["id"], project_id, old["candidate_id"], generation_id,
            old["text"], source["audition_text"], old["seed"], old["model_id"],
            old["model_revision"], old["source_sha256"], None, status,
            "generation.interrupted" if status == "interrupted" else old["error_code"],
            old["audio_path"], old["audio_sha256"], old["duration_seconds"],
            old["sample_rate"], old["created_at"], old["updated_at"],
        ))
    for table in ("legacy_clone_trials", "legacy_selections", "legacy_candidates", "legacy_rounds"):
        db.execute(f"DROP TABLE {table}")


def initialize(db_path: Path, root: Path) -> None:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=OFF")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 4:
            return
        if version == 3:
            from .take_migration import migrate_takes
            migrate_takes(db)
            return
        if version == 2:
            from .engine_migration import migrate_engines
            migrate_engines(db)
            from .take_migration import migrate_takes
            migrate_takes(db)
            return
        if version != 0:
            raise ValueError(f"unsupported_voice_lab_schema:{version}")
        legacy = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rounds'").fetchone()
        if legacy:
            _migrate_legacy(db, root)
        else:
            db.executescript("BEGIN IMMEDIATE;" + SCHEMA)
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("voice_lab_foreign_key_violation")
        db.execute("PRAGMA user_version=2")
        db.commit()
        from .engine_migration import migrate_engines
        migrate_engines(db)
        from .take_migration import migrate_takes
        migrate_takes(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
