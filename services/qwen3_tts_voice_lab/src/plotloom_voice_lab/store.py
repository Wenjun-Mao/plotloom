"""SQLite composition and managed-file cleanup for the Voice Lab."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .migration import initialize


LOGGER = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "voice_lab.sqlite3"
        initialize(self.db_path, self.data_dir)
        from .projects import ProjectRepository
        from .generations import GenerationRepository
        from .clones import CloneRepository
        from .voices import VoiceRepository
        from .takes import TakeRepository
        from .dispatch import DispatchRepository

        self.projects = ProjectRepository(self)
        self.generations = GenerationRepository(self)
        self.clones = CloneRepository(self)
        self.voices = VoiceRepository(self)
        self.takes = TakeRepository(self)
        self.dispatch = DispatchRepository(self)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def owned_file(self, value: str | None) -> Path:
        if not value:
            raise ValueError("asset.missing")
        path = Path(value)
        if path.is_symlink() or not path.resolve().is_relative_to(self.data_dir):
            raise ValueError("asset.outside_managed_root")
        return path

    @staticmethod
    def enqueue_cleanup(db: sqlite3.Connection, paths: list[str | None]) -> None:
        for path in paths:
            if path:
                db.execute("INSERT OR IGNORE INTO cleanup_debts VALUES (?,?,?)", (
                    new_id("cd"), path, now(),
                ))

    def run_cleanup(self) -> int:
        removed = 0
        with self.connection() as db:
            debts = db.execute("SELECT id,path FROM cleanup_debts ORDER BY created_at,id").fetchall()
            for debt in debts:
                try:
                    path = self.owned_file(debt["path"])
                    path.unlink(missing_ok=True)
                    for parent in (path.parent, path.parent.parent):
                        if parent != self.data_dir:
                            try:
                                parent.rmdir()
                            except OSError:
                                pass
                    db.execute("DELETE FROM cleanup_debts WHERE id=?", (debt["id"],))
                    removed += 1
                except (OSError, ValueError):
                    LOGGER.exception("managed Voice Lab cleanup remains pending: %s", debt["id"])
        return removed

    def reconcile_interrupted(self) -> None:
        """A prior dispatch may have reached the model; never replay it."""
        with self.connection() as db:
            stamp = now()
            for table, kind in (("generations", "generation"), ("clone_trials", "clone"), ("voice_takes", "take")):
                db.execute(f"""UPDATE {table} SET status='interrupted',error_code='generation.interrupted',updated_at=?
                    WHERE status='running' OR (status='queued' AND (
                        NOT EXISTS(SELECT 1 FROM dispatch_outbox WHERE kind=? AND job_id={table}.id)
                        OR EXISTS(SELECT 1 FROM execution_grants WHERE kind=? AND job_id={table}.id)))""", (stamp, kind, kind))
        self.run_cleanup()
