"""One durable inference owner, independent of backend-specific payloads."""

import hashlib
import json
import sqlite3
import uuid

from .contracts import GatewayError


MEDIA_INPUT_FIELDS = (
    "id", "backend", "input_mode", "h3_contract", "quality", "resolution",
    "execution_snapshot_json", "aspect_policy", "background_mode", "prompt",
    "seed", "requested_duration_seconds", "frame_count", "fps",
)


def media_binding(job) -> str:
    value = {key: job[key] for key in MEDIA_INPUT_FIELDS}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def initialize_lane(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS generation_lane (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL, job_kind TEXT NOT NULL, job_id TEXT NOT NULL,
            binding_hash TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
            grant_id TEXT, error_code TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner,job_id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_generation_lane
            ON generation_lane((1)) WHERE state='active';
    """)
    # Only unfinished media work joins the lane. Historical unknown outcomes
    # and terminal snapshots are not retroactively reinterpreted.
    for row in db.execute("SELECT * FROM jobs WHERE status IN ('queued','submitting','submitted','running','transfer_pending') ORDER BY rowid").fetchall():
        register(db, "gateway", row["backend"], row["id"], media_binding(row),
                 state="queued" if row["status"] == "queued" else "active")


def register(db, owner, kind, job_id, binding_hash, *, state="queued"):
    existing = db.execute("SELECT * FROM generation_lane WHERE owner=? AND job_id=?", (owner, job_id)).fetchone()
    if existing:
        if existing["job_kind"] != kind or existing["binding_hash"] != binding_hash:
            raise GatewayError("lane.binding_conflict", 409)
        return dict(existing)
    db.execute("""INSERT INTO generation_lane(owner,job_kind,job_id,binding_hash,state,grant_id)
        VALUES (?,?,?,?,?,?)""", (owner, kind, job_id, binding_hash, state,
                                 uuid.uuid4().hex if state == "active" else None))
    return dict(db.execute("SELECT * FROM generation_lane WHERE owner=? AND job_id=?", (owner, job_id)).fetchone())


class GenerationLane:
    def __init__(self, store):
        self.store = store

    def register_voice(self, kind, job_id, binding_hash):
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return register(db, "voice_lab", kind, job_id, binding_hash)

    def active(self):
        with self.store._connect() as db:
            row = db.execute("SELECT * FROM generation_lane WHERE state='active'").fetchone()
            return dict(row) if row else None

    def claim(self):
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM generation_lane WHERE state='active'").fetchone():
                return None
            row = db.execute("SELECT * FROM generation_lane WHERE state='queued' ORDER BY sequence LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE generation_lane SET state='active',grant_id=?,updated_at=CURRENT_TIMESTAMP WHERE sequence=?",
                       (uuid.uuid4().hex, row["sequence"]))
            return dict(db.execute("SELECT * FROM generation_lane WHERE sequence=?", (row["sequence"],)).fetchone())

    def finish(self, entry):
        with self.store._connect() as db:
            db.execute("UPDATE generation_lane SET state='done',error_code=NULL,updated_at=CURRENT_TIMESTAMP WHERE sequence=? AND grant_id=? AND state='active'",
                       (entry["sequence"], entry["grant_id"]))

    def hold(self, entry, code):
        with self.store._connect() as db:
            db.execute("UPDATE generation_lane SET error_code=?,updated_at=CURRENT_TIMESTAMP WHERE sequence=? AND grant_id=? AND state='active'",
                       (code, entry["sequence"], entry["grant_id"]))

    def progress(self, owner, job_id):
        with self.store._connect() as db:
            row = db.execute("SELECT * FROM generation_lane WHERE owner=? AND job_id=?", (owner, job_id)).fetchone()
            if not row:
                return {"phase": "waiting_for_registration", "queueAhead": None}
            ahead = db.execute("SELECT COUNT(*) FROM generation_lane WHERE sequence<? AND state IN ('queued','active')", (row["sequence"],)).fetchone()[0]
            return {"phase": row["state"], "queueAhead": ahead,
                    "errorCode": row["error_code"], "sequence": row["sequence"]}

    def counts(self):
        with self.store._connect() as db:
            rows = {row[0]: row[1] for row in db.execute("SELECT state,COUNT(*) FROM generation_lane GROUP BY state")}
            return rows.get("queued", 0), rows.get("active", 0)

    def purge_finished_voice_records(self):
        # Registration audit is temporary; the owning Lab keeps durable takes
        # and one-use grants. Never discard queued or uncertain ownership.
        with self.store._connect() as db:
            return db.execute("DELETE FROM generation_lane WHERE owner='voice_lab' AND state='done' AND updated_at<=datetime('now','-30 days')").rowcount


class LaneDispatcher:
    def __init__(self, gateway, voice_client):
        self.gateway = gateway
        self.lane = gateway.lane
        self.voice = voice_client

    def advance(self):
        entry = self.lane.active()
        if entry:
            self._observe(entry)
            if self.lane.active():
                return None
        while True:
            entry = self.lane.claim()
            if not entry:
                return None
            if entry["owner"] != "gateway":
                break
            job = self.gateway.store.get_job(entry["job_id"])
            if job["status"] not in {"succeeded", "failed", "cancelled"}:
                break
            self.lane.finish(entry)
        if entry["owner"] == "voice_lab":
            try:
                result = self.voice.execute(entry)
            except GatewayError as error:
                self.lane.hold(entry, error.code)
                return None
            return self._voice_result(entry, result)
        job = self.gateway.store.get_job(entry["job_id"])
        if media_binding(job) != entry["binding_hash"]:
            self.lane.hold(entry, "lane.media_binding_mismatch")
            return None
        result = self.gateway.dispatch_media(job)
        if result and result["status"] in {"succeeded", "failed", "cancelled"}:
            self.lane.finish(entry)
        elif result and result["status"] == "outcome_unknown":
            self.lane.hold(entry, result["error_code"])
        elif result and result["status"] == "queued":
            # Keep ownership while an external Comfy task is active. This is
            # known not dispatched, so a subsequent check may start it safely.
            self.lane.hold(entry, "lane.waiting_for_external_backend")
        return result

    def _observe(self, entry):
        if entry["owner"] == "voice_lab":
            try:
                return self._voice_result(entry, self.voice.execution(entry))
            except GatewayError as error:
                self.lane.hold(entry, error.code)
                return None
        job = self.gateway.store.get_job(entry["job_id"])
        if job["status"] == "queued":
            if media_binding(job) != entry["binding_hash"]:
                self.lane.hold(entry, "lane.media_binding_mismatch")
                return None
            job = self.gateway.dispatch_media(job)
        elif job["status"] in {"submitted", "running", "transfer_pending"}:
            job = self.gateway.refresh_job(entry["job_id"])
        if job and job["status"] in {"succeeded", "failed", "cancelled"}:
            self.lane.finish(entry)
        elif job and job["status"] == "outcome_unknown":
            self.lane.hold(entry, job["error_code"])
        return job

    def _voice_result(self, entry, result):
        if (result.get("grantId") != entry["grant_id"]
                or result.get("bindingHash") != entry["binding_hash"]
                or result.get("jobId") != entry["job_id"]
                or result.get("kind") != entry["job_kind"]):
            self.lane.hold(entry, "lane.voice_binding_mismatch")
        elif result.get("status") not in {"queued", "running", "completed", "completed_stale", "failed", "interrupted", "deleted"}:
            self.lane.hold(entry, "lane.voice_status_invalid")
        elif result.get("releaseConfirmed") is True and result.get("status") not in {"queued", "running"}:
            self.lane.finish(entry)
        else:
            self.lane.hold(entry, result.get("errorCode") or ("dispatch.release_unproven" if result.get("status") not in {"queued", "running"} else None))
        return result
