"""Durable registration and one-use execution grants from the shared lane."""

import hashlib
import json
import os
import threading
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import Field, model_validator
from typing import Literal

from .contracts import StrictModel
from .store import now


TABLES = {"generation": "generations", "clone": "clone_trials", "take": "voice_takes"}
FIELDS = {
    "generation": ("candidate_id", "audition_text", "brief", "direction", "seed", "snapshot_json"),
    "clone": ("generation_id", "text", "reference_text", "source_sha256", "seed", "snapshot_json", "delivery_json"),
    "take": ("voice_id", "text", "reference_text", "reference_sha256", "seed", "snapshot_json", "delivery_json"),
}


class ExecutionGrant(StrictModel):
    kind: Literal["generation", "clone", "take"]
    jobId: str = Field(pattern=r"^(vg|vt|take)_[0-9a-f]{32}$")
    bindingHash: str = Field(pattern=r"^[0-9a-f]{64}$")
    grantId: str = Field(pattern=r"^[0-9a-f]{32}$")

    @model_validator(mode="after")
    def matching_kind(self):
        if not self.jobId.startswith({"generation": "vg_", "clone": "vt_", "take": "take_"}[self.kind]):
            raise ValueError("dispatch.kind_mismatch")
        return self


def binding_hash(db, kind, job_id):
    row = db.execute(f"SELECT * FROM {TABLES[kind]} WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise ValueError("job.not_found")
    value = {key: row[key] for key in FIELDS[kind]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class DispatchRepository:
    def __init__(self, store):
        self.store = store

    def pending(self):
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            result = []
            for row in db.execute("SELECT * FROM dispatch_outbox WHERE registered_at IS NULL ORDER BY rowid").fetchall():
                kind, job_id = row["kind"], row["job_id"]
                job = db.execute(f"SELECT status FROM {TABLES[kind]} WHERE id=?", (job_id,)).fetchone()
                if not job or job["status"] != "queued":
                    db.execute("UPDATE dispatch_outbox SET registered_at=? WHERE kind=? AND job_id=?", (now(), kind, job_id))
                    continue
                digest = binding_hash(db, kind, job_id)
                if row["binding_hash"] and digest != row["binding_hash"]:
                    raise ValueError("dispatch.binding_changed")
                db.execute("UPDATE dispatch_outbox SET binding_hash=? WHERE kind=? AND job_id=?", (digest, kind, job_id))
                result.append({"kind": kind, "jobId": job_id, "bindingHash": digest})
            return result

    def registered(self, kind, job_id):
        with self.store.connection() as db:
            db.execute("UPDATE dispatch_outbox SET registered_at=? WHERE kind=? AND job_id=?", (now(), kind, job_id))

    def authorize(self, grant: ExecutionGrant):
        """Deduplicate CPU control grants, never enqueue an execution twice."""
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM execution_grants WHERE kind=? AND job_id=?", (grant.kind, grant.jobId)).fetchone()
            if old:
                if old["grant_id"] != grant.grantId or old["binding_hash"] != grant.bindingHash:
                    raise ValueError("dispatch.grant_conflict")
                return False
            registration = db.execute("SELECT binding_hash FROM dispatch_outbox WHERE kind=? AND job_id=?", (grant.kind, grant.jobId)).fetchone()
            if not registration or registration[0] != grant.bindingHash:
                raise ValueError("dispatch.binding_mismatch")
            job = db.execute(f"SELECT status FROM {TABLES[grant.kind]} WHERE id=?", (grant.jobId,)).fetchone()
            start = bool(job and job["status"] == "queued")
            if start and binding_hash(db, grant.kind, grant.jobId) != grant.bindingHash:
                raise ValueError("dispatch.binding_mismatch")
            stamp = now()
            try:
                db.execute("""INSERT INTO execution_grants
                    (grant_id,kind,job_id,binding_hash,release_confirmed,error_code,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?)""", (grant.grantId, grant.kind, grant.jobId, grant.bindingHash,
                        int(not start), None if start else "dispatch.not_started", stamp, stamp))
            except Exception as error:
                import sqlite3
                if isinstance(error, sqlite3.IntegrityError):
                    raise ValueError("dispatch.other_execution_unreleased") from error
                raise
            return start

    def execution(self, grant_id):
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM execution_grants WHERE grant_id=?", (grant_id,)).fetchone()
            if not row:
                raise ValueError("dispatch.not_found")
            job = db.execute(f"SELECT status,error_code FROM {TABLES[row['kind']]} WHERE id=?", (row["job_id"],)).fetchone()
            return {"grantId": grant_id, "jobId": row["job_id"], "kind": row["kind"],
                    "bindingHash": row["binding_hash"], "releaseConfirmed": bool(row["release_confirmed"]),
                    "status": job["status"] if job else "deleted",
                    "errorCode": row["error_code"] or (job["error_code"] if job else None)}

    def release(self, grant_id, *, confirmed):
        with self.store.connection() as db:
            db.execute("UPDATE execution_grants SET release_confirmed=?,error_code=?,updated_at=? WHERE grant_id=?",
                       (int(confirmed), None if confirmed else "dispatch.release_unproven", now(), grant_id))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LaneClient:
    def __init__(self, url=None, key=None):
        self.url = (url if url is not None else os.environ.get("VOICE_LAB_GATEWAY_URL", "")).rstrip("/")
        self.key = key if key is not None else os.environ.get("VOICE_LAB_DISPATCH_KEY", "")
        self.http = build_opener(NoRedirect())

    def request(self, path, body=None):
        if not self.url or not self.key:
            raise ValueError("dispatch.unconfigured")
        request = Request(self.url + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            with self.http.open(request, timeout=3) as response:
                result = json.load(response)
                if not isinstance(result, dict):
                    raise ValueError("dispatch.invalid_response")
                return result
        except (HTTPError, URLError, OSError) as error:
            raise ValueError("dispatch.control_unavailable") from error

    def register(self, body):
        result = self.request("/internal/voice-registrations", body)
        if result.get("jobId") != body["jobId"] or type(result.get("sequence")) is not int or result["sequence"] < 1:
            raise ValueError("dispatch.invalid_registration_ack")
        return result

    def progress(self, job_id):
        return self.request(f"/internal/voice-registrations/{job_id}")


class RegistrationWorker:
    def __init__(self, store, client):
        self.store, self.client = store, client
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, name="voice-lane-registration", daemon=True)

    def run(self):
        while not self.stopped.is_set():
            try:
                for entry in self.store.dispatch.pending():
                    self.client.register(entry)
                    self.store.dispatch.registered(entry["kind"], entry["jobId"])
            except (ValueError, OSError):
                # Retained outbox + visible waiting phase, not local fallback.
                pass
            self.stopped.wait(.2)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=4)
        if self.thread.is_alive():
            raise RuntimeError("registration.shutdown_failed")
