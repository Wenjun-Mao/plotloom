"""Narrow, authenticated MiniMax-H3 gateway backed by one ComfyUI queue."""
from __future__ import annotations

import copy
import hmac
import json
import os
import sqlite3
import threading
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from .profile_catalog import (
    H3_GATEWAY_PROFILES,
    LEGACY_PROFILE_ID,
    PROFILE_CONTRACT_VERSION,
    TURBO_4STEP_LORA,
    GatewayProfile,
    profile,
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
AspectPolicy = Literal["cover_center_crop", "contain_pad", "reject_mismatch"]


class GatewayError(RuntimeError):
    """A stable gateway failure that is safe to expose to a trusted caller."""

    def __init__(self, code: str, status_code: int = 502):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True)
class GatewaySettings:
    """Deployment configuration. Secrets are never persisted in SQLite."""

    api_key: str
    data_dir: Path
    comfy_input_dir: Path
    comfy_url: str = "http://127.0.0.1:8188"
    request_timeout_seconds: float = 30.0
    worker_poll_seconds: float = 0.5
    dispatch_worker_enabled: bool = True

    @classmethod
    def from_environment(cls) -> "GatewaySettings":
        key = os.environ.get("H3_API_KEY", "").strip()
        if not key:
            raise RuntimeError("H3_API_KEY is required")
        return cls(
            api_key=key,
            data_dir=Path(os.environ.get("H3_GATEWAY_DATA_DIR", "/var/lib/plotloom-h3-gateway")),
            comfy_input_dir=Path(os.environ.get("H3_COMFY_INPUT_DIR", "/comfy/input")),
            comfy_url=os.environ.get("H3_COMFY_URL", "http://127.0.0.1:8188").rstrip("/"),
            worker_poll_seconds=float(os.environ.get("H3_WORKER_POLL_SECONDS", "0.5")),
            dispatch_worker_enabled=os.environ.get("H3_DISPATCH_WORKER_ENABLED", "true").strip().lower()
            not in {"0", "false", "no", "off"},
        )


class CreateJobRequest(BaseModel):
    """The intentionally small, versioned application contract."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(alias="assetId", min_length=3, max_length=80)
    prompt: str = Field(min_length=1, max_length=8_000)
    aspect_policy: AspectPolicy = Field(alias="aspectPolicy")
    # Omission keeps the old direct-gateway API behaviour. Plotloom's v2 UI
    # always sends an explicit current catalog choice, whose default is the
    # new portrait-fast profile.
    profile_id: str = Field(default=LEGACY_PROFILE_ID, alias="profileId", min_length=3, max_length=63, pattern=r"^[a-z][a-z0-9_]{0,62}$")
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)
    # Plotloom uses its durable local video-job ID here. Direct trusted callers
    # may omit it, preserving the prior API, but then cannot retry safely.
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", min_length=8, max_length=255)


class GatewayStore:
    """Small durable control plane; no raw ComfyUI payloads or secrets."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                  id TEXT PRIMARY KEY, mime_type TEXT NOT NULL, width INTEGER NOT NULL,
                  height INTEGER NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
                  profile_id TEXT NOT NULL, aspect_policy TEXT NOT NULL, prompt TEXT NOT NULL,
                  seed INTEGER NOT NULL, prepared_input_name TEXT NOT NULL, status TEXT NOT NULL,
                  idempotency_key TEXT, request_hash TEXT,
                  comfy_prompt_id TEXT, output_filename TEXT, output_subfolder TEXT,
                  output_type TEXT, error_code TEXT,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        """Apply additive gateway-local schema changes without rewriting jobs."""

        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "idempotency_key" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN idempotency_key TEXT")
        if "request_hash" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN request_hash TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS jobs_idempotency_key_unique "
            "ON jobs(idempotency_key) WHERE idempotency_key IS NOT NULL"
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def put_asset(self, *, asset_id: str, mime_type: str, width: int, height: int, digest: str, path: Path) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assets (id, mime_type, width, height, sha256, path) VALUES (?, ?, ?, ?, ?, ?)",
                (asset_id, mime_type, width, height, digest, str(path)),
            )
        return self.get_asset(asset_id)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        if row is None:
            raise GatewayError("asset_not_found", 404)
        return dict(row)

    def queue_counts(self) -> tuple[int, int]:
        """Return queued and active work without exposing prompts or assets."""

        with self._connect() as connection:
            queued = int(connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'queued'"
            ).fetchone()[0])
            active = int(connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('submitting', 'submitted', 'running')"
            ).fetchone()[0])
        return queued, active

    def reserve_job(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Persist a no-provider-call reservation or return an idempotent job."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            key = values.get("idempotency_key")
            if isinstance(key, str):
                row = connection.execute(
                    "SELECT * FROM jobs WHERE idempotency_key = ?", (key,)
                ).fetchone()
                if row is not None:
                    existing = dict(row)
                    if existing.get("request_hash") != values.get("request_hash"):
                        connection.rollback()
                        raise GatewayError("idempotency_conflict", 409)
                    connection.commit()
                    return existing, False
            connection.execute(
                """INSERT INTO jobs
                (id, asset_id, profile_id, aspect_policy, prompt, seed, prepared_input_name,
                 status, idempotency_key, request_hash)
                VALUES (:id, :asset_id, :profile_id, :aspect_policy, :prompt, :seed,
                        :prepared_input_name, 'reserved', :idempotency_key, :request_hash)""",
                values,
            )
            connection.commit()
        return self.get_job(values["id"]), True

    def claim_next_queued(self) -> dict[str, Any] | None:
        """Claim one FIFO job before the only possible outbound ComfyUI POST."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY rowid ASC LIMIT 1"
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            job_id = str(row["id"])
            updated = connection.execute(
                "UPDATE jobs SET status = 'submitting', updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND status = 'queued'",
                (job_id,),
            )
            if updated.rowcount != 1:
                connection.rollback()
                return None
            connection.commit()
        return self.get_job(job_id)

    def recover_interrupted_dispatches(self) -> None:
        """Never replay a job that may have crossed an outbound-call boundary."""

        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = 'outcome_unknown', "
                "error_code = COALESCE(error_code, 'gateway_restart_before_known_submission'), "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE status IN ('reserved', 'submitting')"
            )

    def list_active_jobs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status IN ('submitted', 'running') ORDER BY rowid ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def cancel_queued_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE jobs SET status = 'cancelled', error_code = 'cancelled_while_queued', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'queued'",
                (job_id,),
            )
            if updated.rowcount != 1:
                row = connection.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
                if row is None:
                    raise GatewayError("job_not_found", 404)
                raise GatewayError("job_not_cancellable", 409)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise GatewayError("job_not_found", 404)
        return dict(row)

    def update_job(self, job_id: str, *, status: str, **values: Any) -> dict[str, Any]:
        assignments = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params: list[Any] = [status]
        for name, value in values.items():
            assignments.append(f"{name} = ?")
            params.append(value)
        params.append(job_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?", params)
        return self.get_job(job_id)


class H3Gateway:
    def __init__(self, settings: GatewaySettings, *, session: requests.Session | Any | None = None) -> None:
        if settings.worker_poll_seconds <= 0:
            raise ValueError("worker_poll_seconds must be positive")
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.comfy_input_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = self.settings.data_dir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.store = GatewayStore(self.settings.data_dir / "gateway.sqlite3")
        self.store.recover_interrupted_dispatches()
        self.session = session or requests.Session()
        self.legacy_template = _load_legacy_template()

    def health(self) -> dict[str, Any]:
        self._preflight()
        queued, active = self.store.queue_counts()
        return {
            "status": "ok",
            "profileContractVersion": PROFILE_CONTRACT_VERSION,
            "profiles": [item.public_descriptor() for item in H3_GATEWAY_PROFILES],
            "queuedJobs": queued,
            "activeDispatches": active,
            "dispatchConcurrency": 1,
        }

    def add_asset(self, content: bytes, *, mime_type: str) -> dict[str, Any]:
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise GatewayError("unsupported_image_mime", 415)
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise GatewayError("image_size_invalid", 413)
        try:
            with Image.open(_bytes_io(content)) as source:
                source.verify()
            with Image.open(_bytes_io(content)) as source:
                width, height = source.size
        except (UnidentifiedImageError, OSError) as error:
            raise GatewayError("image_decode_invalid", 422) from error
        if width * height > MAX_IMAGE_PIXELS:
            raise GatewayError("image_pixels_exceed_limit", 422)
        asset_id = f"asset_{uuid.uuid4().hex}"
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime_type]
        path = self.assets_dir / f"{asset_id}{suffix}"
        path.write_bytes(content)
        return self.store.put_asset(
            asset_id=asset_id, mime_type=mime_type, width=width, height=height,
            digest=sha256(content).hexdigest(), path=path,
        )

    def create_job(self, request: CreateJobRequest) -> dict[str, Any]:
        # Admission deliberately has no ComfyUI round trip. The gateway can
        # validate its own catalog, asset and image preparation while H3 is
        # busy or temporarily unavailable; the worker performs the live
        # preflight immediately before the only outbound dispatch.
        try:
            selected_profile = profile(request.profile_id)
        except KeyError as error:
            raise GatewayError("profile_not_supported", 422) from error
        asset = self.store.get_asset(request.asset_id)
        job_id = f"h3_{uuid.uuid4().hex}"
        seed = request.seed if request.seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
        input_name = f"{job_id}.png"
        request_hash = sha256(json.dumps({
            "assetId": request.asset_id,
            "prompt": request.prompt,
            "aspectPolicy": request.aspect_policy,
            "profileId": request.profile_id,
            "seed": request.seed,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        job, created = self.store.reserve_job({
            "id": job_id, "asset_id": asset["id"], "profile_id": request.profile_id,
            "aspect_policy": request.aspect_policy, "prompt": request.prompt, "seed": seed,
            "prepared_input_name": input_name,
            "idempotency_key": request.idempotency_key, "request_hash": request_hash,
        })
        if not created:
            return job
        try:
            _prepare_input(
                source=Path(asset["path"]), destination=self.settings.comfy_input_dir / input_name,
                target_width=selected_profile.width,
                target_height=selected_profile.height, policy=request.aspect_policy,
            )
        except GatewayError as error:
            return self.store.update_job(job_id, status="failed", error_code=error.code)
        return self.store.update_job(job_id, status="queued")

    def dispatch_once(self) -> dict[str, Any] | None:
        """Advance at most one FIFO job through the only H3 dispatch lane."""

        for active in self.store.list_active_jobs():
            self.refresh_job(str(active["id"]))
        if self.store.list_active_jobs():
            return None
        try:
            # Do not stack a gateway job behind unrelated trusted ComfyUI work.
            if self._comfy_queue_depth() > 0:
                return None
            self._preflight()
        except GatewayError:
            # A post-admission outage leaves queued work durable for a later
            # worker pass; it is not a failed generation attempt.
            return None
        job = self.store.claim_next_queued()
        if job is None:
            return None
        try:
            selected_profile = profile(str(job["profile_id"]))
            workflow = _render_workflow(
                self.legacy_template["prompt"], profile=selected_profile,
                prompt=str(job["prompt"]), input_name=str(job["prepared_input_name"]),
                seed=int(job["seed"]),
            )
        except (KeyError, TypeError, ValueError):
            # This is a local immutable-contract failure; no ComfyUI call was
            # attempted, so it is safe and accurate to mark it failed.
            return self.store.update_job(
                str(job["id"]), status="failed", error_code="dispatch_local_precondition_failed"
            )
        try:
            response = self.session.post(
                f"{self.settings.comfy_url}/prompt",
                json={"prompt": workflow, "client_id": job["id"]},
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            # The durable state changed before the call, so a transport failure
            # or process death must never cause automatic replay.
            return self.store.update_job(
                str(job["id"]), status="outcome_unknown", error_code="submit_outcome_unknown"
            )
        prompt_id = payload.get("prompt_id") if isinstance(payload, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            return self.store.update_job(
                str(job["id"]), status="outcome_unknown", error_code="submit_response_invalid"
            )
        return self.store.update_job(
            str(job["id"]), status="submitted", comfy_prompt_id=prompt_id
        )

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Only jobs that have not entered ComfyUI can be cancelled safely."""

        return self.store.cancel_queued_job(job_id)

    def refresh_job(self, job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if job["status"] not in {"submitted", "running"}:
            return job
        prompt_id = job["comfy_prompt_id"]
        try:
            response = self.session.get(f"{self.settings.comfy_url}/history/{prompt_id}", timeout=self.settings.request_timeout_seconds)
            response.raise_for_status()
            history = response.json()
        except (requests.RequestException, ValueError):
            return job
        record = history.get(prompt_id) if isinstance(history, dict) else None
        if not isinstance(record, dict):
            return self.store.update_job(job_id, status="running")
        status = record.get("status") if isinstance(record.get("status"), dict) else {}
        if status.get("status_str") not in {"success", "completed"}:
            if status.get("completed"):
                return self.store.update_job(job_id, status="failed", error_code="comfy_execution_failed")
            return self.store.update_job(job_id, status="running")
        descriptor = _single_output_descriptor(record.get("outputs"))
        if descriptor is None:
            return self.store.update_job(job_id, status="failed", error_code="comfy_output_missing")
        return self.store.update_job(
            job_id, status="succeeded", output_filename=descriptor["filename"],
            output_subfolder=descriptor["subfolder"], output_type=descriptor["type"],
        )

    def read_output(self, job_id: str) -> bytes:
        job = self.refresh_job(job_id)
        if job["status"] != "succeeded":
            raise GatewayError("output_not_ready", 409)
        try:
            response = self.session.get(
                f"{self.settings.comfy_url}/view",
                params={"filename": job["output_filename"], "subfolder": job["output_subfolder"], "type": job["output_type"]},
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise GatewayError("comfy_output_unavailable", 502) from error
        return bytes(response.content)

    def _comfy_queue_depth(self) -> int:
        payload = self._get_json("/queue", code="comfy_unavailable")
        if not isinstance(payload, dict):
            raise GatewayError("comfy_queue_invalid", 503)
        active = payload.get("queue_running", [])
        pending = payload.get("queue_pending", [])
        if not isinstance(active, list) or not isinstance(pending, list):
            raise GatewayError("comfy_queue_invalid", 503)
        return len(active) + len(pending)

    def _preflight(self) -> None:
        self._get_json("/system_stats", code="comfy_unavailable")
        object_info = self._get_json("/object_info", code="comfy_profile_unavailable")
        required = (
            ("UNETLoader", "unet_name", "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"),
            ("CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
            ("VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors"),
            ("VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors"),
            ("LoraLoaderModelOnly", "lora_name", TURBO_4STEP_LORA),
        )
        for node_type, input_name, expected in required:
            try:
                options = object_info[node_type]["input"]["required"][input_name][0]
            except (KeyError, IndexError, TypeError) as error:
                raise GatewayError("comfy_profile_unavailable", 503) from error
            if not isinstance(options, list) or expected not in options:
                raise GatewayError("comfy_profile_unavailable", 503)
        if "MiniMaxH3ImageToVideo" not in object_info or "PrimitiveInt" not in object_info:
            raise GatewayError("comfy_profile_unavailable", 503)

    def _get_json(self, path: str, *, code: str) -> object:
        try:
            response = self.session.get(f"{self.settings.comfy_url}{path}", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            raise GatewayError(code, 503) from error


class GatewayDispatchWorker:
    """One process-local worker that advances the durable FIFO queue.

    SQLite claims protect the queue record itself. The deployment contract is
    deliberately one gateway process per data directory, which is the only
    supported way to ensure one H3/ComfyUI dispatch lane.
    """

    def __init__(self, gateway: H3Gateway) -> None:
        self._gateway = gateway
        self._stopped = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="plotloom-h3-dispatch", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stopped.set()
        self._thread.join(timeout=max(1.0, self._gateway.settings.request_timeout_seconds + 1.0))

    def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                self._gateway.dispatch_once()
            except Exception:
                # Job status and health provide the safe operator-facing
                # evidence. Never log prompts, asset paths, or server values.
                pass
            self._stopped.wait(self._gateway.settings.worker_poll_seconds)


def create_app(settings: GatewaySettings | None = None, *, session: requests.Session | Any | None = None) -> FastAPI:
    gateway = H3Gateway(settings or GatewaySettings.from_environment(), session=session)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker = GatewayDispatchWorker(gateway)
        app.state.dispatch_worker = worker
        if gateway.settings.dispatch_worker_enabled:
            worker.start()
        try:
            yield
        finally:
            if gateway.settings.dispatch_worker_enabled:
                worker.stop()

    app = FastAPI(title="Plotloom MiniMax-H3 gateway", version="1.0", lifespan=lifespan)
    app.state.gateway = gateway

    def authorize(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {gateway.settings.api_key}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.exception_handler(GatewayError)
    async def handle_gateway_error(_: Any, error: GatewayError) -> Response:
        return Response(
            content=json.dumps({"error": error.code}), status_code=error.status_code,
            media_type="application/json",
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return gateway.health()

    @app.post("/v1/assets", dependencies=[Depends(authorize)])
    async def upload_asset(image: UploadFile = File(...)) -> dict[str, Any]:
        content = await image.read(MAX_UPLOAD_BYTES + 1)
        asset = gateway.add_asset(content, mime_type=(image.content_type or "").lower())
        return {
            "assetId": asset["id"], "mimeType": asset["mime_type"], "width": asset["width"],
            "height": asset["height"], "sha256": asset["sha256"],
        }

    @app.post("/v1/video-jobs", dependencies=[Depends(authorize)], status_code=202)
    def create_video_job(request: CreateJobRequest) -> dict[str, Any]:
        job = gateway.create_job(request)
        return _job_response(job)

    @app.get("/v1/video-jobs/{job_id}", dependencies=[Depends(authorize)])
    def get_video_job(job_id: str) -> dict[str, Any]:
        return _job_response(gateway.refresh_job(job_id))

    @app.post("/v1/video-jobs/{job_id}/cancel", dependencies=[Depends(authorize)])
    def cancel_video_job(job_id: str) -> dict[str, Any]:
        return _job_response(gateway.cancel_job(job_id))

    @app.get("/v1/video-jobs/{job_id}/output", dependencies=[Depends(authorize)])
    def get_output(job_id: str) -> Response:
        return Response(content=gateway.read_output(job_id), media_type="video/mp4")

    return app


def _load_legacy_template() -> dict[str, Any]:
    path = Path(__file__).with_name("profiles") / f"{LEGACY_PROFILE_ID}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _render_workflow(
    template: dict[str, Any], *, profile: GatewayProfile, prompt: str, input_name: str, seed: int,
) -> dict[str, Any]:
    workflow = copy.deepcopy(template)

    # New catalog entries use hard-coded PrimitiveInt nodes, never a caller
    # supplied size or ResolutionSelector heuristic. The old one-profile
    # graph remains untouched for historical jobs.
    if profile.explicit_dimensions:
        workflow["115"] = {"class_type": "PrimitiveInt", "inputs": {"value": profile.width}}
        workflow["116"] = {"class_type": "PrimitiveInt", "inputs": {"value": profile.height}}
        workflow["105:104"]["inputs"] |= {
            "width": ["115", 0], "height": ["116", 0],
        }

    def replace(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: replace(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace(child) for child in value]
        return {"__PROMPT__": prompt, "__INPUT_IMAGE__": input_name, "__SEED__": seed}.get(value, value)

    return replace(workflow)


def _prepare_input(*, source: Path, destination: Path, target_width: int, target_height: int, policy: AspectPolicy) -> None:
    try:
        with Image.open(source) as input_image:
            image = ImageOps.exif_transpose(input_image).convert("RGB")
            source_ratio = image.width / image.height
            target_ratio = target_width / target_height
            if policy == "reject_mismatch" and abs(source_ratio - target_ratio) > 0.001:
                raise GatewayError("input_aspect_mismatch", 422)
            if policy == "cover_center_crop":
                if source_ratio > target_ratio:
                    crop_width = round(image.height * target_ratio)
                    left = (image.width - crop_width) // 2
                    image = image.crop((left, 0, left + crop_width, image.height))
                else:
                    crop_height = round(image.width / target_ratio)
                    top = (image.height - crop_height) // 2
                    image = image.crop((0, top, image.width, top + crop_height))
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            elif policy == "contain_pad":
                image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (target_width, target_height), "black")
                canvas.paste(image, ((target_width - image.width) // 2, (target_height - image.height) // 2))
                image = canvas
            elif policy == "reject_mismatch":
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            else:  # Literal typing is not a runtime boundary.
                raise GatewayError("aspect_policy_invalid", 422)
            image.save(destination, "PNG", optimize=True)
    except GatewayError:
        raise
    except (UnidentifiedImageError, OSError) as error:
        raise GatewayError("input_prepare_failed", 422) from error


def _single_output_descriptor(outputs: object) -> dict[str, str] | None:
    if not isinstance(outputs, dict):
        return None
    matches: list[dict[str, str]] = []
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        for item in node_output.get("images", []):
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            subfolder = item.get("subfolder", "")
            output_type = item.get("type")
            if not all(isinstance(value, str) for value in (filename, subfolder, output_type)):
                continue
            if output_type != "output" or not filename.endswith(".mp4") or not _safe_path_part(filename) or not _safe_path_part(subfolder):
                continue
            matches.append({"filename": filename, "subfolder": subfolder, "type": output_type})
    return matches[0] if len(matches) == 1 else None


def _safe_path_part(value: str) -> bool:
    return not value.startswith(("/", "\\")) and ".." not in Path(value).parts and "\\" not in value


def _job_response(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"], "status": job["status"], "profileId": job["profile_id"],
        "aspectPolicy": job["aspect_policy"], "error": job["error_code"],
        "outputReady": job["status"] == "succeeded",
    }


def _bytes_io(value: bytes) -> Any:
    from io import BytesIO
    return BytesIO(value)
