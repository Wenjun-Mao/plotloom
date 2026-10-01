"""Line-specific immutable audio, independent of casting project lifetime."""

from __future__ import annotations

import json
import secrets
from typing import TYPE_CHECKING

from .contracts import TakeCreate
from .engines.catalog import snapshot
from .engines.protocol import ExecutionEvidence
from .media import copy_verified
from .store import new_id, now

if TYPE_CHECKING:
    from .store import Store


class TakeRepository:
    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def public(row) -> dict:
        media = json.loads(row["media_json"] or "{}")
        return {
            "takeId": row["id"], "voiceId": row["voice_id"],
            "text": row["text"], "seed": row["seed"], "engineId": row["engine_id"],
            "referenceSha256": row["reference_sha256"],
            "executionSnapshot": json.loads(row["snapshot_json"]),
            "delivery": json.loads(row["delivery_json"]),
            "executionDetails": json.loads(row["execution_details"] or "{}"),
            "status": row["status"], "errorCode": row["error_code"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"],
            "sourceSha256": media.get("sourceSha256"), "h3Sha256": media.get("h3Sha256"),
            "durationSeconds": media.get("sourceDurationSeconds"),
            "sampleRate": media.get("sourceSampleRate"),
            "h3Eligible": media.get("h3Eligible", False),
            "h3IssueCode": media.get("h3IssueCode"),
            "preparationVersion": media.get("preparationVersion"),
            "audioDetails": media.get("audioDetails", {}),
        }

    def create(self, body: TakeCreate) -> dict:
        spec = snapshot(body.engineId, "reuse")
        take_id, stamp = new_id("take"), now()
        reference = self.store.data_dir / "takes" / take_id / "reference.wav"
        try:
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                voice = db.execute("SELECT * FROM voices WHERE id=?", (body.voiceId,)).fetchone()
                if voice is None:
                    raise ValueError("voice.not_found")
                copy_verified(self.store.owned_file(voice["source_path"]), reference, voice["source_sha256"])
                db.execute("""INSERT INTO voice_takes
                    (id,voice_id,text,reference_text,reference_path,reference_sha256,
                     seed,engine_id,snapshot_json,delivery_json,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,'queued',?,?)""", (
                    take_id, body.voiceId, body.text, voice["transcript"], str(reference),
                    voice["source_sha256"], body.seed if body.seed is not None else secrets.randbits(32),
                    body.engineId, json.dumps(spec), body.delivery.model_dump_json(exclude_none=True), stamp, stamp,
                ))
        except Exception:
            reference.unlink(missing_ok=True)
            raise
        return self.get(take_id)

    def get(self, take_id: str, *, private: bool = False) -> dict:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM voice_takes WHERE id=?", (take_id,)).fetchone()
            if row is None:
                raise ValueError("take.not_found")
            result = self.public(row)
            if private:
                result.update(referencePath=row["reference_path"], referenceText=row["reference_text"],
                              **{key: value for key, value in json.loads(row["media_json"] or "{}").items()
                                 if key in {"sourcePath", "h3Path"}})
            return result

    def list(self, voice_id: str) -> list[dict]:
        self.store.voices.get(voice_id)
        with self.store.connection() as db:
            rows = db.execute("SELECT * FROM voice_takes WHERE voice_id=? ORDER BY rowid DESC", (voice_id,))
            return [self.public(row) for row in rows]

    def mark(self, take_id: str, status: str, code: str | None = None, media: dict | None = None):
        with self.store.connection() as db:
            row = db.execute("SELECT status FROM voice_takes WHERE id=?", (take_id,)).fetchone()
            if row is None or row["status"] not in {"queued", "running"}:
                raise ValueError("take.not_appendable")
            db.execute("UPDATE voice_takes SET status=?,error_code=?,media_json=?,updated_at=? WHERE id=?", (
                status, code, json.dumps(media) if media else None, now(), take_id,
            ))

    def record_execution(self, take_id: str, evidence: dict):
        evidence = ExecutionEvidence.model_validate(evidence).model_dump(exclude_none=True)
        with self.store.connection() as db:
            updated = db.execute("""UPDATE voice_takes SET execution_details=?
                WHERE id=? AND status='running' AND execution_details IS NULL""", (json.dumps(evidence), take_id))
            if updated.rowcount != 1:
                raise ValueError("take.evidence_not_appendable")

    def delete(self, take_id: str, confirmation: str):
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM voice_takes WHERE id=?", (take_id,)).fetchone()
            if row is None:
                raise ValueError("take.not_found")
            if confirmation != take_id:
                raise ValueError("take.confirmation_mismatch")
            if row["status"] in {"queued", "running"} or db.execute(
                "SELECT 1 FROM execution_grants WHERE kind='take' AND job_id=? AND release_confirmed=0", (take_id,)
            ).fetchone():
                raise ValueError("take.busy")
            media = json.loads(row["media_json"] or "{}")
            self.store.enqueue_cleanup(db, [row["reference_path"], media.get("sourcePath"), media.get("h3Path")])
            db.execute("UPDATE voice_takes SET status='deleted',media_json=NULL,updated_at=? WHERE id=?", (now(), take_id))
        self.store.run_cleanup()
