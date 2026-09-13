"""Application service that coordinates durable H3 jobs and ComfyUI."""
from __future__ import annotations

import json
import os
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Any

import requests

from .comfy import ComfyClient
from .contracts import CreateJobRequest, GatewayError, GatewaySettings
from .media import GatewayFiles
from .naming import timestamped_storage_name
from .profile_catalog import H3_GATEWAY_PROFILES, PROFILE_CONTRACT_VERSION, profile
from .store import GatewayStore
from .workflow import load_legacy_template, render_workflow, single_output_descriptor


class H3Gateway:
    """The single trusted application boundary for H3 generation work."""

    def __init__(self, settings: GatewaySettings, *, session: requests.Session | Any | None = None) -> None:
        if settings.worker_poll_seconds <= 0:
            raise ValueError("worker_poll_seconds must be positive")
        self.settings = settings
        self.store = GatewayStore(self.settings.data_dir / "gateway.sqlite3")
        self.store.recover_interrupted_dispatches()
        self.files = GatewayFiles(settings, self.store)
        self.session = session or requests.Session()
        self.comfy = ComfyClient(settings, self.session)
        self.legacy_template = load_legacy_template()

    def health(self) -> dict[str, Any]:
        self.comfy.preflight()
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
        return self.files.add_asset(content, mime_type=mime_type)

    def create_job(self, request: CreateJobRequest) -> dict[str, Any]:
        """Reserve and prepare a job without a live ComfyUI round trip."""

        try:
            selected_profile = profile(request.profile_id)
        except KeyError as error:
            raise GatewayError("profile_not_supported", 422) from error
        asset = self.store.get_asset(request.asset_id)
        job_id = f"h3_{uuid.uuid4().hex}"
        seed = request.seed if request.seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
        values = {
            "id": job_id,
            "asset_id": asset["id"],
            "profile_id": request.profile_id,
            "aspect_policy": request.aspect_policy,
            "prompt": request.prompt,
            "seed": seed,
            "prepared_input_name": timestamped_storage_name(job_id, ".png"),
            "idempotency_key": request.idempotency_key,
            "request_hash": self._request_hash(request),
        }
        job, created = self.store.reserve_job(values)
        if not created:
            return job
        try:
            self.files.prepare_job_input(job=job, asset=asset, profile=selected_profile)
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
            if self.comfy.queue_depth() > 0:
                return None
            self.comfy.preflight()
        except GatewayError:
            # A post-admission outage leaves work durable for a later worker
            # pass; it is not a failed generation attempt.
            return None
        job = self.store.claim_next_queued()
        if job is None:
            return None
        try:
            selected_profile = profile(str(job["profile_id"]))
            workflow = render_workflow(
                self.legacy_template["prompt"],
                profile=selected_profile,
                prompt=str(job["prompt"]),
                input_name=str(job["prepared_input_name"]),
                seed=int(job["seed"]),
            )
        except (KeyError, TypeError, ValueError):
            return self.store.update_job(
                str(job["id"]), status="failed", error_code="dispatch_local_precondition_failed"
            )
        try:
            prompt_id = self.comfy.submit(workflow=workflow, client_id=str(job["id"]))
        except GatewayError as error:
            return self.store.update_job(str(job["id"]), status="outcome_unknown", error_code=error.code)
        return self.store.update_job(str(job["id"]), status="submitted", comfy_prompt_id=prompt_id)

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
        prompt_id = job["comfy_prompt_id"]
        record = history.get(prompt_id) if isinstance(history, dict) else None
        if not isinstance(record, dict):
            return self.store.update_job(job_id, status="running")
        status = record.get("status") if isinstance(record.get("status"), dict) else {}
        if status.get("status_str") not in {"success", "completed"}:
            if status.get("completed"):
                return self.store.update_job(job_id, status="failed", error_code="comfy_execution_failed")
            return self.store.update_job(job_id, status="running")
        descriptor = single_output_descriptor(record.get("outputs"))
        if descriptor is None:
            return self.store.update_job(job_id, status="failed", error_code="comfy_output_missing")
        pending = self.store.update_job(
            job_id,
            status="transfer_pending",
            error_code="gateway_output_transfer_pending",
            output_filename=descriptor["filename"],
            output_subfolder=descriptor["subfolder"],
            output_type=descriptor["type"],
            managed_output_name=timestamped_storage_name(job_id, ".mp4"),
        )
        return self.files.transfer_completed_output(pending)

    def read_output(self, job_id: str) -> bytes:
        job = self.refresh_job(job_id)
        if job["status"] == "output_expired":
            raise GatewayError("gateway_output_expired", 410)
        if job["status"] != "succeeded":
            raise GatewayError("output_not_ready", 409)
        return self.files.read_output(job)

    def cleanup_expired_outputs(self) -> int:
        return self.files.cleanup_expired_outputs()

    def cleanup_expired_job_records(self) -> int:
        return self.files.cleanup_expired_job_records()

    def cleanup_expired_gateway_inputs_and_assets(self) -> int:
        return self.files.cleanup_expired_gateway_inputs_and_assets()

    def cleanup_pending_asset_purges(self) -> int:
        return self.files.cleanup_pending_asset_purges()

    # These narrow delegators preserve the testable filesystem safety boundary
    # without making HTTP routing or job orchestration own path validation.
    def _managed_output_path(self, job: dict[str, Any]) -> Path | None:
        return self.files.managed_output_path(job)

    def _prepared_input_path(self, job: dict[str, Any]) -> Path | None:
        return self.files.prepared_input_path(job)

    @staticmethod
    def _request_hash(request: CreateJobRequest) -> str:
        payload = {
            "assetId": request.asset_id,
            "prompt": request.prompt,
            "aspectPolicy": request.aspect_policy,
            "profileId": request.profile_id,
            "seed": request.seed,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()
