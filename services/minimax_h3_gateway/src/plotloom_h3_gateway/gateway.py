"""Application service coordinating durable H3 jobs and ComfyUI."""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

import requests

from .comfy import ComfyClient
from .contracts import CreateImageJobRequest, CreateTextJobRequest, GatewayError, GatewaySettings
from .media import GatewayFiles
from .naming import timestamped_storage_name
from .profile_catalog import (
    FRAMES_PER_SECOND,
    H3_GATEWAY_PROFILES,
    PROFILE_CONTRACT_VERSION,
    frame_count_for_duration_seconds,
    profile,
)
from .source_images import SourceImageFetcher
from .store import GatewayStore
from .workflow import load_h3_template, render_workflow, single_output_descriptor


class H3Gateway:
    """The single trusted application boundary for H3 generation work."""

    def __init__(self, settings: GatewaySettings, *, session: requests.Session | Any | None = None, source_session: requests.Session | Any | None = None) -> None:
        if settings.worker_poll_seconds <= 0:
            raise ValueError("worker_poll_seconds must be positive")
        if settings.source_fetch_connect_timeout_seconds <= 0 or settings.source_fetch_read_timeout_seconds <= 0:
            raise ValueError("source fetch timeouts must be positive")
        if settings.source_fetch_max_redirects < 0:
            raise ValueError("source_fetch_max_redirects must not be negative")
        self.settings = settings
        self.store = GatewayStore(self.settings.data_dir / "gateway.sqlite3")
        self.store.recover_interrupted_dispatches()
        self.files = GatewayFiles(settings, self.store)
        self.session = session or requests.Session()
        self.comfy = ComfyClient(settings, self.session)
        self.source_images = SourceImageFetcher(settings, session=source_session)
        self.workflow_template = load_h3_template()

    def health(self) -> dict[str, Any]:
        self.comfy.preflight()
        queued, active = self.store.queue_counts()
        return {
            "status": "ok", "profileContractVersion": PROFILE_CONTRACT_VERSION,
            "profiles": [item.public_descriptor() for item in H3_GATEWAY_PROFILES],
            "inputModes": ["image", "text"], "queuedJobs": queued, "activeDispatches": active,
            "dispatchConcurrency": 1,
        }

    def validate_image_job_request(self, request: CreateImageJobRequest) -> None:
        """Reject profile/duration configuration before a URL fetch or write."""

        self._selected_profile(request.profile_id)
        frame_count_for_duration_seconds(request.duration_seconds)

    def create_image_job(self, request: CreateImageJobRequest, *, start_content: bytes, end_content: bytes | None = None) -> dict[str, Any]:
        self.validate_image_job_request(request)
        start_asset = self.files.add_asset(start_content)
        assets = [start_asset]
        try:
            if end_content is not None:
                assets.append(self.files.add_asset(end_content))
            return self._create_job(
                input_mode="image", prompt=request.prompt, profile_id=request.profile_id,
                aspect_policy=request.aspect_policy, seed=request.seed,
                duration_seconds=request.duration_seconds, assets=assets,
            )
        except GatewayError:
            for asset in assets:
                self.files.discard_unreferenced_asset(asset)
            raise

    def create_text_job(self, request: CreateTextJobRequest) -> dict[str, Any]:
        self._selected_profile(request.profile_id)
        return self._create_job(
            input_mode="text", prompt=request.prompt, profile_id=request.profile_id,
            aspect_policy=None, seed=request.seed, duration_seconds=request.duration_seconds, assets=[],
        )

    def _create_job(self, *, input_mode: str, prompt: str, profile_id: str, aspect_policy: str | None, seed: int | None, duration_seconds: int, assets: list[dict[str, Any]]) -> dict[str, Any]:
        selected_profile = self._selected_profile(profile_id)
        frame_count = frame_count_for_duration_seconds(duration_seconds)
        if input_mode == "image":
            if aspect_policy is None or not assets:
                raise GatewayError("image_file_required", 422)
            for asset in assets:
                self.files.validate_job_input(asset=asset, profile=selected_profile, policy=aspect_policy)
        elif input_mode != "text" or assets or aspect_policy is not None:
            raise GatewayError("request_invalid", 422)

        job_id = f"h3_{uuid.uuid4().hex}"
        resolved_seed = seed if seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
        frames = [
            {"role": role, "asset_id": str(asset["id"]), "prepared_input_name": timestamped_storage_name(job_id, ".png", label=role)}
            for role, asset in zip(("start", "end"), assets, strict=False)
        ]
        prepared: list[dict[str, Any]] = []
        try:
            for frame, asset in zip(frames, assets, strict=True):
                self.files.prepare_job_frame(frame=frame, asset=asset, profile=selected_profile, policy=aspect_policy)  # type: ignore[arg-type]
                prepared.append(frame)
            return self.store.reserve_job(
                {
                    "id": job_id, "input_mode": input_mode, "profile_id": profile_id,
                    "aspect_policy": aspect_policy, "prompt": prompt, "seed": resolved_seed,
                    "requested_duration_seconds": duration_seconds, "frame_count": frame_count,
                    "fps": FRAMES_PER_SECOND,
                }, frames,
            )
        except GatewayError:
            self._discard_prepared_frames(job_id, prepared)
            raise

    def _discard_prepared_frames(self, job_id: str, frames: list[dict[str, Any]]) -> None:
        for frame in frames:
            path = self.files.prepared_input_path(job_id=job_id, frame=frame)
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _selected_profile(profile_id: str):
        try:
            return profile(profile_id)
        except KeyError as error:
            raise GatewayError("profile_not_supported", 422) from error

    def dispatch_once(self) -> dict[str, Any] | None:
        for active in self.store.list_active_jobs():
            self.refresh_job(str(active["id"]))
        if self.store.list_active_jobs():
            return None
        try:
            if self.comfy.queue_depth() > 0:
                return None
            self.comfy.preflight()
        except GatewayError:
            return None
        job = self.store.claim_next_queued()
        if job is None:
            return None
        try:
            frames = {str(frame["role"]): str(frame["prepared_input_name"]) for frame in self.store.get_job_frames(str(job["id"]))}
            workflow = render_workflow(
                self.workflow_template["prompt"], profile=profile(str(job["profile_id"])),
                prompt=str(job["prompt"]), start_input_name=frames.get("start"), end_input_name=frames.get("end"),
                seed=int(job["seed"]), frame_count=int(job["frame_count"]),
            )
        except (KeyError, TypeError, ValueError):
            return self.store.update_job(str(job["id"]), status="failed", error_code="dispatch_local_precondition_failed")
        try:
            prompt_id = self.comfy.submit(workflow=workflow, client_id=str(job["id"]))
        except GatewayError as error:
            return self.store.update_job(str(job["id"]), status="outcome_unknown", error_code=error.code)
        return self.store.update_job(
            str(job["id"]), status="submitted", comfy_prompt_id=prompt_id,
            generation_submitted_at_ms=_now_ms(),
        )

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        return self.store.cancel_queued_job(job_id)

    def refresh_job(self, job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if job["status"] == "transfer_pending":
            return self.files.transfer_completed_output(job)
        if job["status"] not in {"submitted", "running"}:
            return job
        history = self.comfy.history(job.get("comfy_prompt_id"))
        if history is None:
            return job
        record = history.get(job["comfy_prompt_id"]) if isinstance(history, dict) else None
        if not isinstance(record, dict):
            return self.store.update_job(job_id, status="running")
        status = record.get("status") if isinstance(record.get("status"), dict) else {}
        if status.get("status_str") not in {"success", "completed"}:
            if status.get("completed"):
                return self._generation_completed(job_id, status="failed", error_code="comfy_execution_failed")
            return self.store.update_job(job_id, status="running")
        descriptor = single_output_descriptor(record.get("outputs"))
        if descriptor is None:
            return self._generation_completed(job_id, status="failed", error_code="comfy_output_missing")
        pending = self._generation_completed(
            job_id, status="transfer_pending", error_code="gateway_output_transfer_pending",
            output_filename=descriptor["filename"], output_subfolder=descriptor["subfolder"], output_type=descriptor["type"],
            managed_output_name=timestamped_storage_name(job_id, ".mp4"),
        )
        return self.files.transfer_completed_output(pending)

    def _generation_completed(self, job_id: str, *, status: str, error_code: str, **values: Any) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        values["error_code"] = error_code
        if job.get("generation_completed_at_ms") is None:
            values["generation_completed_at_ms"] = _now_ms()
        return self.store.update_job(job_id, status=status, **values)

    def read_output(self, job_id: str) -> bytes:
        job = self.refresh_job(job_id)
        if job["status"] != "succeeded":
            raise GatewayError("output_not_ready", 409)
        return self.files.read_output(job)

    def output_is_ready(self, job: dict[str, Any]) -> bool:
        return job["status"] == "succeeded" and self.store.output_is_retained(str(job["id"])) and (path := self.files.managed_output_path(job)) is not None and path.is_file() and not path.is_symlink()

    def cleanup_expired_outputs(self) -> int: return self.files.cleanup_expired_outputs()
    def cleanup_due_job_records(self) -> int: return self.files.cleanup_due_job_records()
    def cleanup_expired_gateway_keyframes(self) -> int: return self.files.cleanup_expired_gateway_keyframes()
    def cleanup_expired_gateway_inputs_and_assets(self) -> int: return self.files.cleanup_expired_gateway_inputs_and_assets()
    def cleanup_pending_asset_purges(self) -> int: return self.files.cleanup_pending_asset_purges()

    def _managed_output_path(self, job: dict[str, Any]) -> Path | None: return self.files.managed_output_path(job)


def _now_ms() -> int:
    return time.time_ns() // 1_000_000
