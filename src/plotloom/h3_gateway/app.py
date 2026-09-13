"""Narrow, authenticated MiniMax-H3 gateway backed by one ComfyUI queue."""
from __future__ import annotations

import copy
import hmac
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

PROFILE_ID = "minimax_h3_fp8_turbo4_480p"
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
    max_queue_depth: int = 2
    request_timeout_seconds: float = 30.0

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
            max_queue_depth=int(os.environ.get("H3_MAX_QUEUE_DEPTH", "2")),
        )


class CreateJobRequest(BaseModel):
    """The intentionally small, versioned application contract."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(alias="assetId", min_length=3, max_length=80)
    prompt: str = Field(min_length=1, max_length=8_000)
    aspect_policy: AspectPolicy = Field(alias="aspectPolicy")
    profile_id: Literal["minimax_h3_fp8_turbo4_480p"] = Field(
        default=PROFILE_ID,
        alias="profileId",
    )
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)


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
                  comfy_prompt_id TEXT, output_filename TEXT, output_subfolder TEXT,
                  output_type TEXT, error_code TEXT,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
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

    def active_job_count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('reserved', 'submitted', 'running')"
            ).fetchone()[0])

    def create_job(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO jobs
                (id, asset_id, profile_id, aspect_policy, prompt, seed, prepared_input_name, status)
                VALUES (:id, :asset_id, :profile_id, :aspect_policy, :prompt, :seed, :prepared_input_name, 'reserved')""",
                values,
            )
        return self.get_job(values["id"])

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
        if settings.max_queue_depth < 1:
            raise ValueError("max_queue_depth must be at least one")
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.comfy_input_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = self.settings.data_dir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.store = GatewayStore(self.settings.data_dir / "gateway.sqlite3")
        self.session = session or requests.Session()
        self.profile = _load_profile()

    def health(self) -> dict[str, Any]:
        self._preflight()
        return {"status": "ok", "profiles": [PROFILE_ID], "maxQueueDepth": self.settings.max_queue_depth}

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
        if max(self.store.active_job_count(), self._comfy_queue_depth()) >= self.settings.max_queue_depth:
            raise GatewayError("queue_capacity_reached", 429)
        self._preflight()
        asset = self.store.get_asset(request.asset_id)
        job_id = f"h3_{uuid.uuid4().hex}"
        seed = request.seed if request.seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
        input_name = f"{job_id}.png"
        job = self.store.create_job({
            "id": job_id, "asset_id": asset["id"], "profile_id": request.profile_id,
            "aspect_policy": request.aspect_policy, "prompt": request.prompt, "seed": seed,
            "prepared_input_name": input_name,
        })
        try:
            _prepare_input(
                source=Path(asset["path"]), destination=self.settings.comfy_input_dir / input_name,
                target_width=int(self.profile["output"]["width"]),
                target_height=int(self.profile["output"]["height"]), policy=request.aspect_policy,
            )
        except GatewayError as error:
            return self.store.update_job(job_id, status="failed", error_code=error.code)
        workflow = _render_workflow(self.profile["prompt"], prompt=request.prompt, input_name=input_name, seed=seed)
        try:
            response = self.session.post(
                f"{self.settings.comfy_url}/prompt",
                json={"prompt": workflow, "client_id": job_id},
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            # The request may have reached ComfyUI. It is never safe to auto-replay.
            return self.store.update_job(job_id, status="outcome_unknown", error_code="submit_outcome_unknown")
        prompt_id = payload.get("prompt_id") if isinstance(payload, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            return self.store.update_job(job_id, status="outcome_unknown", error_code="submit_response_invalid")
        return self.store.update_job(job_id, status="submitted", comfy_prompt_id=prompt_id)

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
            ("LoraLoaderModelOnly", "lora_name", "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"),
        )
        for node_type, input_name, expected in required:
            try:
                options = object_info[node_type]["input"]["required"][input_name][0]
            except (KeyError, IndexError, TypeError) as error:
                raise GatewayError("comfy_profile_unavailable", 503) from error
            if not isinstance(options, list) or expected not in options:
                raise GatewayError("comfy_profile_unavailable", 503)
        if "MiniMaxH3ImageToVideo" not in object_info:
            raise GatewayError("comfy_profile_unavailable", 503)

    def _get_json(self, path: str, *, code: str) -> object:
        try:
            response = self.session.get(f"{self.settings.comfy_url}{path}", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            raise GatewayError(code, 503) from error


def create_app(settings: GatewaySettings | None = None, *, session: requests.Session | Any | None = None) -> FastAPI:
    gateway = H3Gateway(settings or GatewaySettings.from_environment(), session=session)
    app = FastAPI(title="Plotloom MiniMax-H3 gateway", version="1.0")

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

    @app.get("/v1/video-jobs/{job_id}/output", dependencies=[Depends(authorize)])
    def get_output(job_id: str) -> Response:
        return Response(content=gateway.read_output(job_id), media_type="video/mp4")

    return app


def _load_profile() -> dict[str, Any]:
    path = Path(__file__).with_name("profiles") / f"{PROFILE_ID}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _render_workflow(template: dict[str, Any], *, prompt: str, input_name: str, seed: int) -> dict[str, Any]:
    workflow = copy.deepcopy(template)

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
