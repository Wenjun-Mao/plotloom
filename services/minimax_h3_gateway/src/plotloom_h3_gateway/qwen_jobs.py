"""Qwen creation and post-claim execution within the Gateway's shared FIFO lane."""
from __future__ import annotations
from collections.abc import Callable
import os
import time
import uuid
from typing import Any
from .contracts import QWEN_IMAGE_GUIDANCE_SCALE, QWEN_IMAGE_STEPS, CreateQwenEditImageJobRequest, CreateQwenTextImageJobRequest, GatewayError, GatewaySettings
from .image_catalog import QWEN_IMAGE_CONTRACT_VERSION, admitted_qwen_image_canvas, qwen_image_canvas_from_snapshot
from .media import GatewayFiles
from .naming import timestamped_storage_name
from .qwen_image import QwenImageClient
from .store import GatewayStore


class QwenImageCoordinator:
    """No worker or claim authority; execute only after the Gateway's durable CAS."""

    def __init__(self, settings: GatewaySettings, store: GatewayStore, files: GatewayFiles,
                 client: QwenImageClient, *, completed: Callable[..., dict[str, Any]]) -> None:
        self.settings = settings
        self.store = store
        self.files = files
        self.qwen = client
        self._generation_completed = completed

    def create_qwen_text_image_job(self, request: CreateQwenTextImageJobRequest) -> dict[str, Any]:
        return self._create_qwen_image_job(
            input_mode="text", prompt=request.prompt, resolution=request.resolution,
            background_mode=request.background_mode, seed=request.seed, asset=None,
        )

    def create_qwen_edit_image_job(
        self, request: CreateQwenEditImageJobRequest, *, source_content: bytes
    ) -> dict[str, Any]:
        asset = self.files.add_asset(source_content)
        try:
            return self._create_qwen_image_job(
                input_mode="image", prompt=request.prompt, resolution=request.resolution,
                background_mode=request.background_mode, seed=request.seed, asset=asset,
            )
        except GatewayError:
            self.files.discard_unreferenced_asset(asset)
            raise

    def _create_qwen_image_job(
        self, *, input_mode: str, prompt: str, resolution: str, background_mode: str,
        seed: int | None, asset: dict[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            canvas = admitted_qwen_image_canvas(resolution)
        except KeyError:
            raise GatewayError("image_resolution_not_supported", 422)
        if input_mode == "image" and asset is None:
            raise GatewayError("image_file_required", 422)
        if input_mode == "text" and asset is not None:
            raise GatewayError("request_invalid", 422)
        job_id = f"img_{uuid.uuid4().hex}"
        resolved_seed = seed if seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
        # Existing H3-only databases accept start/end bindings. New schemas
        # support source explicitly; start is an equivalent one-reference
        # binding for the only image-edit mode we admit.
        frames = ([{"role": "start", "asset_id": str(asset["id"]), "prepared_input_name": ""}] if asset else [])
        snapshot = {
            "imageContractVersion": QWEN_IMAGE_CONTRACT_VERSION,
            "backend": "qwen_image",
            "model": self.settings.qwen_image_model,
            "resolution": canvas.resolution,
            "width": canvas.width,
            "height": canvas.height,
            "steps": QWEN_IMAGE_STEPS,
            "guidanceScale": QWEN_IMAGE_GUIDANCE_SCALE,
            "outputs": 1,
            "outputFormat": "png",
            "transparentPromptPolicyVersion": 1,
            "rendererVersion": 1,
        }
        import json
        return self.store.reserve_job(
            {
                "id": job_id, "backend": "qwen_image", "input_mode": input_mode,
                # These H3 columns remain non-null for records from the same
                # durable table; zero has no Qwen public meaning.
                "quality": 0, "resolution": resolution,
                "execution_snapshot_json": json.dumps(snapshot, sort_keys=True, separators=(",", ":")),
                "aspect_policy": None, "background_mode": background_mode, "prompt": prompt,
                "seed": resolved_seed, "requested_duration_seconds": 0,
                "frame_count": 0, "fps": 0,
            }, frames,
        )

    def dispatch_claimed(self, job: dict[str, Any]) -> dict[str, Any]:
        """Run one blocking local SGLang call while holding the shared lane."""

        job_id = str(job["id"])
        try:
            self.qwen.preflight()
            canvas = qwen_image_canvas_from_snapshot(str(job["execution_snapshot_json"]))
            source_content: bytes | None = None
            if job["input_mode"] == "image":
                frames = self.store.get_job_frames(job_id)
                if len(frames) != 1:
                    raise GatewayError("qwen_image_input_invalid", 422)
                source_content = self.files.asset_content(frames[0])
        except ValueError:
            return self.store.update_job(
                job_id, status="failed", error_code="qwen_image_execution_snapshot_invalid"
            )
        except GatewayError as error:
            return self.store.update_job(job_id, status="failed", error_code=error.code)

        self.store.update_job(job_id, status="running", generation_submitted_at_ms=_now_ms())
        try:
            if source_content is None:
                content = self.qwen.generate(
                    prompt=str(job["prompt"]), width=canvas.width, height=canvas.height, seed=int(job["seed"]),
                    background_mode=str(job["background_mode"]),
                )
            else:
                content = self.qwen.edit(
                    prompt=str(job["prompt"]), width=canvas.width, height=canvas.height, seed=int(job["seed"]),
                    background_mode=str(job["background_mode"]), source_name="reference.png",
                    source_content=source_content,
                )
        except GatewayError as error:
            status = "outcome_unknown" if error.code == "qwen_image_submit_outcome_unknown" else "failed"
            return self._generation_completed(job_id, status=status, error_code=error.code)
        completed = self._generation_completed(
            job_id, status="transfer_pending", error_code="gateway_output_transfer_pending",
            managed_output_name=timestamped_storage_name(job_id, ".png"),
        )
        return self.files.store_qwen_image_output(completed, content)



def _now_ms() -> int:
    return time.time_ns() // 1_000_000
