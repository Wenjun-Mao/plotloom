"""Frozen, one-candidate VoiceDesign jobs and current-pointer replacement."""

from __future__ import annotations

import secrets
import json
from typing import TYPE_CHECKING

from .engines.catalog import snapshot
from .media import file_sha256
from .store import new_id, now

if TYPE_CHECKING:
    from .store import Store


class GenerationRepository:
    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def public(row) -> dict:
        return {
            "generationId": row["id"], "candidateId": row["candidate_id"],
            "status": row["status"], "errorCode": row["error_code"],
            "auditionText": row["audition_text"], "brief": row["brief"],
            "direction": row["direction"],
            "seed": row["seed"], "modelId": row["model_id"],
            "modelRevision": row["model_revision"],
            "sourceSha256": row["source_sha256"],
            "sourceDurationSeconds": row["source_duration_seconds"],
            "sourceSampleRate": row["source_sample_rate"],
            "h3Sha256": row["h3_sha256"], "h3Eligible": bool(row["h3_eligible"]),
            "preparationVersion": row["preparation_version"],
            "removedAt": row["removed_at"], "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "engineId": row["engine_id"], "executionSnapshot": json.loads(row["snapshot_json"]),
            "audioDetails": json.loads(row["audio_details"] or "{}"),
        }

    def get(self, generation_id: str, *, private: bool = False) -> dict:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM generations WHERE id=?", (generation_id,)).fetchone()
            if row is None:
                raise ValueError("generation.not_found")
            result = self.public(row)
            if private:
                result.update(sourcePath=row["source_path"], h3Path=row["h3_path"])
            return result

    def history(self, candidate_id: str) -> list[dict]:
        with self.store.connection() as db:
            if not db.execute("SELECT 1 FROM candidate_slots WHERE id=?", (candidate_id,)).fetchone():
                raise ValueError("candidate.not_found")
            rows = db.execute("SELECT * FROM generations WHERE candidate_id=? ORDER BY rowid DESC", (candidate_id,)).fetchall()
            return [self.public(row) for row in rows]

    def create(self, candidate_id: str, project_revision: int, candidate_revision: int, seed: int | None) -> dict:
        generation_id, stamp = new_id("vg"), now()
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (candidate_id,)).fetchone()
            if candidate is None:
                raise ValueError("candidate.not_found")
            project = self.store.projects._require_project(db, candidate["project_id"], project_revision)
            if candidate["revision"] != candidate_revision:
                raise ValueError("candidate.revision_conflict")
            if not project["audition_text"].strip() or not candidate["direction"].strip():
                raise ValueError("generation.input_missing")
            if db.execute("SELECT 1 FROM generations WHERE candidate_id=? AND status IN ('queued','running')", (candidate_id,)).fetchone():
                raise ValueError("candidate.busy")
            self.admit(db, generation_id, stamp, candidate, project, seed)
        return self.get(generation_id)

    def admit(self, db, generation_id, stamp, candidate, project, seed) -> None:
        spec = snapshot(candidate["engine_id"], "creation")
        db.execute("""INSERT INTO generations
            (id,candidate_id,status,audition_text,brief,direction,seed,model_id,
             model_revision,created_at,updated_at,engine_id,snapshot_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            generation_id, candidate["id"], "queued", project["audition_text"],
            project["brief"], candidate["direction"], seed if seed is not None else secrets.randbits(32),
            spec["modelId"], spec["modelRevision"], stamp, stamp, candidate["engine_id"], json.dumps(spec),
        ))

    def mark_running(self, generation_id: str) -> None:
        with self.store.connection() as db:
            db.execute("UPDATE generations SET status='running',updated_at=? WHERE id=? AND status='queued'", (now(), generation_id))

    def complete(self, generation_id: str, media: dict) -> None:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            generation = db.execute("SELECT * FROM generations WHERE id=?", (generation_id,)).fetchone()
            if generation is None or generation["status"] != "running":
                raise ValueError("generation.not_running")
            candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (generation["candidate_id"],)).fetchone()
            project = db.execute("SELECT * FROM projects WHERE id=?", (candidate["project_id"],)).fetchone()
            stamp = now()
            changed = (generation["direction"] != candidate["direction"]
                       or generation["engine_id"] != candidate["engine_id"]
                       or generation["audition_text"] != project["audition_text"]
                       or generation["brief"] != project["brief"])
            db.execute("""UPDATE generations SET status=?,error_code=?,
                source_path=?,source_sha256=?,source_duration_seconds=?,source_sample_rate=?,
                h3_path=?,h3_sha256=?,h3_eligible=?,preparation_version=?,audio_details=?,updated_at=? WHERE id=?""", (
                "completed_stale" if changed else "completed",
                "generation.input_changed" if changed else media["h3IssueCode"],
                media["sourcePath"], media["sourceSha256"], media["sourceDurationSeconds"],
                media["sourceSampleRate"], media["h3Path"], media["h3Sha256"],
                int(media["h3Eligible"]), media["preparationVersion"], json.dumps(media.get("audioDetails", {})), stamp, generation_id,
            ))
            if changed:
                self.store.enqueue_cleanup(db, [media["sourcePath"], media["h3Path"]])
                db.execute("UPDATE generations SET source_path=NULL,h3_path=NULL,removed_at=? WHERE id=?", (
                    stamp, generation_id,
                ))
            else:
                old_id = candidate["current_generation_id"]
                db.execute("UPDATE candidate_slots SET current_generation_id=?,updated_at=? WHERE id=?", (
                    generation_id, stamp, candidate["id"],
                ))
                if old_id and old_id != generation_id:
                    old = db.execute("SELECT source_path,h3_path FROM generations WHERE id=?", (old_id,)).fetchone()
                    if old:
                        self.store.enqueue_cleanup(db, [old["source_path"], old["h3_path"]])
                        db.execute("UPDATE generations SET source_path=NULL,h3_path=NULL,removed_at=? WHERE id=?", (stamp, old_id))
                    if project["selected_generation_id"] == old_id:
                        db.execute("UPDATE projects SET selected_generation_id=NULL WHERE id=?", (project["id"],))
                        db.execute("INSERT INTO selections VALUES (?,?,?,?,?)", (
                            new_id("vs"), project["id"], None, None, stamp,
                        ))
        self.store.run_cleanup()

    def fail(self, generation_id: str, code: str) -> None:
        with self.store.connection() as db:
            db.execute("UPDATE generations SET status=?,error_code=?,updated_at=? WHERE id=? AND status IN ('queued','running')", (
                "interrupted" if code == "generation.interrupted" else "failed", code, now(), generation_id,
            ))

    def select(self, project_id: str, generation_id: str) -> dict:
        stamp, selection_id = now(), new_id("vs")
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            project = self.store.projects._require_project(db, project_id)
            row = db.execute("""SELECT g.*,c.project_id,c.current_generation_id FROM generations g
                JOIN candidate_slots c ON c.id=g.candidate_id WHERE g.id=?""", (generation_id,)).fetchone()
            if row is None or row["project_id"] != project_id or row["status"] != "completed" or row["current_generation_id"] != generation_id or not row["source_path"]:
                raise ValueError("generation.not_selectable")
            candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (row["candidate_id"],)).fetchone()
            require_current_design(row, candidate, project)
            source = self.store.owned_file(row["source_path"])
            if not source.is_file() or file_sha256(source) != row["source_sha256"]:
                raise ValueError("audio.corrupt")
            db.execute("UPDATE projects SET selected_generation_id=? WHERE id=?", (generation_id, project_id))
            db.execute("INSERT INTO selections VALUES (?,?,?,?,?)", (
                selection_id, project_id, row["candidate_id"], generation_id, stamp,
            ))
        return {"selectionId": selection_id, "projectId": project_id,
                "candidateId": row["candidate_id"], "generationId": generation_id,
                "selectedAt": stamp}

    def selections(self, project_id: str) -> list[dict]:
        with self.store.connection() as db:
            rows = db.execute("SELECT * FROM selections WHERE project_id=? ORDER BY rowid DESC LIMIT 50", (project_id,)).fetchall()
            return [{"selectionId": row["id"], "candidateId": row["candidate_id"],
                     "generationId": row["generation_id"], "selectedAt": row["selected_at"]}
                    for row in rows]


def require_current_design(generation, candidate, project) -> None:
    if (generation["engine_id"] != candidate["engine_id"] or generation["direction"] != candidate["direction"]
            or generation["brief"] != project["brief"] or generation["audition_text"] != project["audition_text"]):
        raise ValueError("generation.design_stale")
