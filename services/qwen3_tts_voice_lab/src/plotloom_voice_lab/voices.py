"""Immutable published voices, independent of source-project lifetime."""

from __future__ import annotations

from typing import TYPE_CHECKING
import json

from .media import copy_verified
from .generations import require_current_design
from .store import new_id, now

if TYPE_CHECKING:
    from .store import Store


class VoiceRepository:
    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def public(row) -> dict:
        return {"voiceId": row["id"], "sourceProjectId": row["source_project_id"],
                "sourceCandidateId": row["source_candidate_id"],
                "sourceGenerationId": row["source_generation_id"],
                "transcript": row["transcript"], "brief": row["brief"],
                "direction": row["direction"],
                "modelId": row["model_id"], "modelRevision": row["model_revision"],
                "seed": row["seed"], "sourceSha256": row["source_sha256"],
                "h3Sha256": row["h3_sha256"], "createdAt": row["created_at"],
                "engineId": row["engine_id"], "executionSnapshot": json.loads(row["snapshot_json"]),
                "audioDetails": json.loads(row["audio_details"] or "{}")}

    def publish(self, project_id: str, generation_id: str) -> dict:
        voice_id = new_id("voice")
        source_copy = self.store.data_dir / "voices" / voice_id / "source.wav"
        h3_copy = self.store.data_dir / "voices" / voice_id / "h3.wav"
        try:
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT * FROM voices WHERE source_project_id=? AND source_generation_id=?", (
                    project_id, generation_id,
                )).fetchone()
                if existing:
                    return self.public(existing)
                project = self.store.projects._require_project(db, project_id)
                row = db.execute("""SELECT g.*,c.project_id,c.current_generation_id FROM generations g
                    JOIN candidate_slots c ON c.id=g.candidate_id WHERE g.id=?""", (generation_id,)).fetchone()
                if row is None or row["project_id"] != project_id or project["selected_generation_id"] != generation_id or row["current_generation_id"] != generation_id or row["status"] != "completed" or not row["h3_eligible"]:
                    raise ValueError("generation.not_publishable")
                candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (row["candidate_id"],)).fetchone()
                require_current_design(row, candidate, project)
                copy_verified(self.store.owned_file(row["source_path"]), source_copy, row["source_sha256"])
                copy_verified(self.store.owned_file(row["h3_path"]), h3_copy, row["h3_sha256"])
                db.execute("INSERT INTO voices (id,source_project_id,source_candidate_id,source_generation_id,transcript,brief,direction,model_id,model_revision,seed,source_path,source_sha256,h3_path,h3_sha256,created_at,engine_id,snapshot_json,audio_details) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    voice_id, project_id, row["candidate_id"], generation_id,
                    row["audition_text"], row["brief"], row["direction"], row["model_id"],
                    row["model_revision"], row["seed"], str(source_copy),
                    row["source_sha256"], str(h3_copy), row["h3_sha256"], now(),
                    row["engine_id"], row["snapshot_json"], row["audio_details"],
                ))
        except Exception:
            source_copy.unlink(missing_ok=True)
            h3_copy.unlink(missing_ok=True)
            raise
        return self.get(voice_id)

    def get(self, voice_id: str, *, private: bool = False) -> dict:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM voices WHERE id=?", (voice_id,)).fetchone()
            if row is None:
                raise ValueError("voice.not_found")
            result = self.public(row)
            if private:
                result.update(sourcePath=row["source_path"], h3Path=row["h3_path"])
            return result

    def list(self) -> list[dict]:
        with self.store.connection() as db:
            rows = db.execute("SELECT * FROM voices ORDER BY rowid DESC LIMIT 100").fetchall()
            return [self.public(row) for row in rows]
