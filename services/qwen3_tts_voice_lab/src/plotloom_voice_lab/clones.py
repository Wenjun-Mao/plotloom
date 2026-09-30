"""New-line tests pin their original reference before entering the queue."""

from __future__ import annotations

import secrets
import json
from typing import TYPE_CHECKING

from .engines.catalog import snapshot
from .contracts import DeliveryControl
from .generations import require_current_design
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
                "updatedAt": row["updated_at"], "engineId": row["engine_id"],
                "executionSnapshot": json.loads(row["snapshot_json"]),
                "delivery": json.loads(row["delivery_json"]),
                "executionDetails": json.loads(row["execution_details"] or "{}"),
                "audioDetails": json.loads(row["audio_details"] or "{}")}

    def create(self, project_id: str, generation_id: str, text: str, seed: int | None,
               engine_id: str = "qwen_base", delivery: dict | None = None) -> dict:
        spec = snapshot(engine_id, "reuse")
        control = DeliveryControl.model_validate(delivery or {"mode": "none"}).model_dump(exclude_none=True)
        if engine_id == "qwen_base" and control["mode"] != "none":
            raise ValueError("engine.delivery_unsupported")
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
                candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (row["candidate_id"],)).fetchone()
                require_current_design(row, candidate, project)
                source = self.store.owned_file(row["source_path"])
                copy_verified(source, reference, row["source_sha256"])
                db.execute("""INSERT INTO clone_trials
                    (id,project_id,candidate_id,generation_id,text,reference_text,seed,
                     model_id,model_revision,source_sha256,reference_path,status,
                     created_at,updated_at,engine_id,snapshot_json,delivery_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    trial_id, project_id, row["candidate_id"], generation_id, text,
                    row["audition_text"], seed if seed is not None else secrets.randbits(32),
                    spec["modelId"], spec["modelRevision"], row["source_sha256"], str(reference),
                    "queued", stamp, stamp, engine_id, json.dumps(spec), json.dumps(control),
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
            if media:
                db.execute("UPDATE clone_trials SET audio_details=? WHERE id=?", (json.dumps(media.get("audioDetails", {})), trial_id))

    def record_execution(self, trial_id: str, evidence: dict) -> None:
        from .engines.protocol import ExecutionEvidence
        evidence = ExecutionEvidence.model_validate(evidence).model_dump(exclude_none=True)
        with self.store.connection() as db:
            row = db.execute("SELECT execution_details,status FROM clone_trials WHERE id=?", (trial_id,)).fetchone()
            if row is None or row["status"] != "running" or row["execution_details"] is not None:
                raise ValueError("clone.evidence_not_appendable")
            db.execute("UPDATE clone_trials SET execution_details=? WHERE id=?", (json.dumps(evidence), trial_id))
