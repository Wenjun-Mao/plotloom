"""SQLite evidence store for immutable casting rounds and lab selections."""

from __future__ import annotations

import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


DESIGN_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
DESIGN_REVISION = "weights-sha256:391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522"
BASE_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
BASE_REVISION = "fd4b254389122332181a7c3db7f27e918eec64e3"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.db_path = data_dir / "voice_lab.sqlite3"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS rounds (
                    id TEXT PRIMARY KEY,
                    audition_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    round_id TEXT NOT NULL REFERENCES rounds(id),
                    ordinal INTEGER NOT NULL,
                    direction TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    model_id TEXT NOT NULL,
                    model_revision TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    source_path TEXT,
                    source_sha256 TEXT,
                    source_duration_seconds REAL,
                    source_sample_rate INTEGER,
                    h3_path TEXT,
                    h3_sha256 TEXT,
                    h3_eligible INTEGER NOT NULL DEFAULT 0,
                    preparation_version TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(round_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS selections (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(id),
                    selected_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clone_trials (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(id),
                    text TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    model_id TEXT NOT NULL,
                    model_revision TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    audio_path TEXT,
                    audio_sha256 TEXT,
                    duration_seconds REAL,
                    sample_rate INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_candidates_round ON candidates(round_id, ordinal);
                CREATE INDEX IF NOT EXISTS idx_clones_candidate ON clone_trials(candidate_id, created_at);
            """)

    def reconcile_interrupted(self) -> None:
        """Never silently replay a generation whose dispatch state is unknown."""
        with self.connection() as db:
            stamp = now()
            db.execute("UPDATE candidates SET status='interrupted', error_code='generation.interrupted', updated_at=? WHERE status IN ('queued','running')", (stamp,))
            db.execute("UPDATE rounds SET status='interrupted', error_code='generation.interrupted', updated_at=? WHERE status IN ('queued','running')", (stamp,))
            db.execute("UPDATE clone_trials SET status='interrupted', error_code='generation.interrupted', updated_at=? WHERE status IN ('queued','running')", (stamp,))

    def create_round(self, audition_text: str, directions: list[str]) -> str:
        round_id = new_id("vr")
        stamp = now()
        with self.connection() as db:
            db.execute("INSERT INTO rounds VALUES (?,?,?,?,?,?)", (round_id, audition_text, "queued", None, stamp, stamp))
            for ordinal, direction in enumerate(directions, start=1):
                db.execute("""INSERT INTO candidates
                    (id,round_id,ordinal,direction,seed,model_id,model_revision,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                    new_id("vc"), round_id, ordinal, direction, secrets.randbits(32),
                    DESIGN_MODEL, DESIGN_REVISION, "queued", stamp, stamp,
                ))
        return round_id

    def _candidate_public(self, row: sqlite3.Row) -> dict:
        return {
            "candidateId": row["id"], "roundId": row["round_id"],
            "ordinal": row["ordinal"], "direction": row["direction"],
            "seed": row["seed"], "status": row["status"],
            "errorCode": row["error_code"], "modelId": row["model_id"],
            "modelRevision": row["model_revision"],
            "sourceSha256": row["source_sha256"],
            "sourceDurationSeconds": row["source_duration_seconds"],
            "sourceSampleRate": row["source_sample_rate"],
            "h3Sha256": row["h3_sha256"], "h3Eligible": bool(row["h3_eligible"]),
            "preparationVersion": row["preparation_version"],
        }

    def get_round(self, round_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM rounds WHERE id=?", (round_id,)).fetchone()
            if row is None:
                return None
            candidates = db.execute("SELECT * FROM candidates WHERE round_id=? ORDER BY ordinal", (round_id,)).fetchall()
            return {
                "roundId": row["id"], "auditionText": row["audition_text"],
                "status": row["status"], "errorCode": row["error_code"],
                "createdAt": row["created_at"], "updatedAt": row["updated_at"],
                "candidates": [self._candidate_public(item) for item in candidates],
            }

    def list_rounds(self, limit: int = 30) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("""SELECT r.*, COUNT(c.id) AS candidate_count
                FROM rounds r JOIN candidates c ON c.round_id=r.id
                GROUP BY r.id ORDER BY r.created_at DESC LIMIT ?""", (limit,)).fetchall()
            return [{"roundId": row["id"], "auditionText": row["audition_text"],
                     "status": row["status"], "candidateCount": row["candidate_count"],
                     "createdAt": row["created_at"]} for row in rows]

    def get_candidate(self, candidate_id: str, *, private: bool = False) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
            if row is None:
                return None
            result = self._candidate_public(row)
            if private:
                result.update(sourcePath=row["source_path"], h3Path=row["h3_path"])
            return result

    def mark_round(self, round_id: str, status: str, error_code: str | None = None) -> None:
        with self.connection() as db:
            db.execute("UPDATE rounds SET status=?,error_code=?,updated_at=? WHERE id=?", (status, error_code, now(), round_id))

    def mark_candidate_running(self, candidate_id: str) -> None:
        with self.connection() as db:
            db.execute("UPDATE candidates SET status='running',updated_at=? WHERE id=? AND status='queued'", (now(), candidate_id))

    def complete_candidate(self, candidate_id: str, media: dict) -> None:
        with self.connection() as db:
            db.execute("""UPDATE candidates SET status='completed',error_code=?,
                source_path=?,source_sha256=?,source_duration_seconds=?,source_sample_rate=?,
                h3_path=?,h3_sha256=?,h3_eligible=?,preparation_version=?,updated_at=?
                WHERE id=? AND status='running'""", (
                media["h3IssueCode"], media["sourcePath"], media["sourceSha256"], media["sourceDurationSeconds"],
                media["sourceSampleRate"], media["h3Path"], media["h3Sha256"],
                int(media["h3Eligible"]), media["preparationVersion"], now(), candidate_id,
            ))

    def fail_candidate(self, candidate_id: str, code: str) -> None:
        with self.connection() as db:
            db.execute("UPDATE candidates SET status='failed',error_code=?,updated_at=? WHERE id=? AND status IN ('queued','running')", (code, now(), candidate_id))

    def select(self, candidate_id: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        if candidate is None or candidate["status"] != "completed":
            raise ValueError("candidate_not_selectable")
        entry = {"selectionId": new_id("vs"), "candidateId": candidate_id, "selectedAt": now()}
        with self.connection() as db:
            db.execute("INSERT INTO selections VALUES (?,?,?)", (entry["selectionId"], candidate_id, entry["selectedAt"]))
        return entry

    def current_selection(self) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM selections ORDER BY rowid DESC LIMIT 1").fetchone()
            return None if row is None else {"selectionId": row["id"], "candidateId": row["candidate_id"], "selectedAt": row["selected_at"]}

    def selection_history(self, limit: int = 30) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT * FROM selections ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
            return [{"selectionId": row["id"], "candidateId": row["candidate_id"],
                     "selectedAt": row["selected_at"]} for row in rows]

    def create_clone(self, candidate_id: str, text: str, seed: int | None) -> str:
        candidate = self.get_candidate(candidate_id)
        if candidate is None or candidate["status"] != "completed":
            raise ValueError("candidate_not_selectable")
        if (self.current_selection() or {}).get("candidateId") != candidate_id:
            raise ValueError("candidate_not_selected")
        clone_id = new_id("vt")
        stamp = now()
        with self.connection() as db:
            db.execute("""INSERT INTO clone_trials
                (id,candidate_id,text,seed,model_id,model_revision,source_sha256,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                clone_id, candidate_id, text, seed if seed is not None else secrets.randbits(32),
                BASE_MODEL, BASE_REVISION, candidate["sourceSha256"], "queued", stamp, stamp,
            ))
        return clone_id

    def get_clone(self, clone_id: str, *, private: bool = False) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM clone_trials WHERE id=?", (clone_id,)).fetchone()
            if row is None:
                return None
            result = {"trialId": row["id"], "candidateId": row["candidate_id"],
                      "text": row["text"], "seed": row["seed"], "status": row["status"],
                      "errorCode": row["error_code"], "modelId": row["model_id"],
                      "modelRevision": row["model_revision"], "sourceSha256": row["source_sha256"],
                      "audioSha256": row["audio_sha256"], "durationSeconds": row["duration_seconds"],
                      "sampleRate": row["sample_rate"], "createdAt": row["created_at"]}
            if private:
                result["audioPath"] = row["audio_path"]
            return result

    def list_clones(self, candidate_id: str, limit: int = 30) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id FROM clone_trials WHERE candidate_id=? ORDER BY created_at DESC LIMIT ?", (candidate_id, limit)).fetchall()
        return [trial for row in rows if (trial := self.get_clone(row["id"])) is not None]

    def mark_clone(self, clone_id: str, status: str, code: str | None = None, media: dict | None = None) -> None:
        media = media or {}
        with self.connection() as db:
            db.execute("""UPDATE clone_trials SET status=?,error_code=?,audio_path=?,audio_sha256=?,
                duration_seconds=?,sample_rate=?,updated_at=? WHERE id=?""", (
                status, code, media.get("audioPath"), media.get("audioSha256"),
                media.get("durationSeconds"), media.get("sampleRate"), now(), clone_id,
            ))
