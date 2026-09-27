"""New-line tests pin their original reference before entering the queue."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from .identity import BASE_MODEL, BASE_REVISION
from .media import copy_verified
from .store import new_id, now

if TYPE_CHECKING:
    from .store import Store


class CloneRepository:
    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def public(row) -> dict:
        return {"trialId": row["id"], "projectId": row["project_id"],
                "candidateId": row["candidate_id"], "generationId": row["generation_id"],
                "text": row["text"], "seed": row["seed"], "status": row["status"],
                "errorCode": row["error_code"], "modelId": row["model_id"],
                "modelRevision": row["model_revision"], "sourceSha256": row["source_sha256"],
                "audioSha256": row["audio_sha256"], "durationSeconds": row["duration_seconds"],
                "sampleRate": row["sample_rate"], "createdAt": row["created_at"],
                "updatedAt": row["updated_at"]}

    def create(self, project_id: str, generation_id: str, text: str, seed: int | None) -> dict:
        trial_id, stamp = new_id("vt"), now()
        reference = self.store.data_dir / "clones" / trial_id / "reference.wav"
        try:
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                project = self.store.projects._require_project(db, project_id)
                row = db.execute("""SELECT g.*,c.project_id,c.current_generation_id FROM generations g
                    JOIN candidate_slots c ON c.id=g.candidate_id WHERE g.id=?""", (generation_id,)).fetchone()
                if row is None or row["project_id"] != project_id or project["selected_generation_id"] != generation_id or row["current_generation_id"] != generation_id or row["status"] != "completed":
                    raise ValueError("generation.not_selected")
                source = self.store.owned_file(row["source_path"])
                copy_verified(source, reference, row["source_sha256"])
                db.execute("""INSERT INTO clone_trials
                    (id,project_id,candidate_id,generation_id,text,reference_text,seed,
                     model_id,model_revision,source_sha256,reference_path,status,
                     created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    trial_id, project_id, row["candidate_id"], generation_id, text,
                    row["audition_text"], seed if seed is not None else secrets.randbits(32),
                    BASE_MODEL, BASE_REVISION, row["source_sha256"], str(reference),
                    "queued", stamp, stamp,
                ))
        except Exception:
            reference.unlink(missing_ok=True)
            raise
        return self.get(trial_id)

    def get(self, trial_id: str, *, private: bool = False) -> dict:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM clone_trials WHERE id=?", (trial_id,)).fetchone()
            if row is None:
                raise ValueError("clone.not_found")
            result = self.public(row)
            if private:
                result.update(referencePath=row["reference_path"], referenceText=row["reference_text"],
                              audioPath=row["audio_path"])
            return result

    def list(self, project_id: str) -> list[dict]:
        with self.store.connection() as db:
            rows = db.execute("SELECT * FROM clone_trials WHERE project_id=? ORDER BY rowid DESC LIMIT 100", (project_id,)).fetchall()
            return [self.public(row) for row in rows]

    def mark(self, trial_id: str, status: str, code: str | None = None, media: dict | None = None) -> None:
        media = media or {}
        with self.store.connection() as db:
            db.execute("""UPDATE clone_trials SET status=?,error_code=?,audio_path=?,audio_sha256=?,
                duration_seconds=?,sample_rate=?,updated_at=? WHERE id=?""", (
                status, code, media.get("audioPath"), media.get("audioSha256"),
                media.get("durationSeconds"), media.get("sampleRate"), now(), trial_id,
            ))
