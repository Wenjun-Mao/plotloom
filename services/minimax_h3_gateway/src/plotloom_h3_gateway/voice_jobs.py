"""Ref2VA admission and frozen-input dispatch within the shared gateway lane."""
from __future__ import annotations

import os
import uuid
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from .contracts import CreateImageVoiceJobRequest, GatewayError
from .naming import timestamped_storage_name
from .profile_catalog import (
    FRAMES_PER_SECOND,
    admitted_execution,
    frame_count_for_duration_seconds,
)
from .voice_reference import (
    VoiceExecution,
    admitted_voice_resolution,
    canonical_voice,
    render_voice_workflow,
    voice_execution_from_snapshot,
)

if TYPE_CHECKING:
    from .gateway import H3Gateway


class VoiceJobs:
    def __init__(self, gateway: H3Gateway) -> None:
        self.gateway = gateway

    def validate_request(self, request: CreateImageVoiceJobRequest) -> None:
        admitted_voice_resolution(request.resolution, request.duration_seconds)
        self.gateway.comfy.preflight_voice()

    def create(
        self, request: CreateImageVoiceJobRequest, *, image_content: bytes, voice_content: bytes
    ) -> tuple[dict[str, Any], str]:
        self.validate_request(request)
        voice = canonical_voice(voice_content)
        image_execution = admitted_execution(quality=8, resolution=request.resolution)
        files = self.gateway.files
        asset = files.add_asset(image_content)
        job_id = f"h3_{uuid.uuid4().hex}"
        frame = {
            "role": "start", "asset_id": str(asset["id"]),
            "prepared_input_name": timestamped_storage_name(job_id, ".png", label="start"),
        }
        binding: dict[str, Any] | None = None
        admitted = False
        try:
            files.validate_job_input(asset=asset, execution=image_execution, policy=request.aspect_policy)
            files.prepare_job_frame(
                frame=frame, asset=asset, execution=image_execution, policy=request.aspect_policy
            )
            binding = self.gateway.voice_files.prepare(job_id=job_id, voice=voice)
            image_path = files.prepared_input_path(job_id=job_id, frame=frame)
            if image_path is None:
                raise GatewayError("input_prepare_failed", 422)
            image_digest = sha256(image_path.read_bytes()).hexdigest()
            seed = request.seed if request.seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
            frame_count = frame_count_for_duration_seconds(request.duration_seconds)
            snapshot = VoiceExecution(
                resolution=image_execution.resolution,
                requested_duration_seconds=request.duration_seconds,
                frame_count=frame_count, seed=seed,
                prompt_sha256=sha256(request.prompt.encode("utf-8")).hexdigest(),
                image_name=frame["prepared_input_name"],
                audio_name=binding["prepared_input_name"],
                image_sha256=str(asset["sha256"]), prepared_image_sha256=image_digest,
                audio_sha256=voice.source_sha256,
                prepared_audio_sha256=voice.prepared_sha256,
            )
            job = self.gateway.store.reserve_job(
                {
                    "id": job_id, "backend": "h3_video", "input_mode": "image",
                    "h3_contract": "ref2va", "quality": 8, "resolution": request.resolution,
                    "execution_snapshot_json": snapshot.snapshot_json(),
                    "aspect_policy": request.aspect_policy, "background_mode": None,
                    "prompt": request.prompt, "seed": seed,
                    "requested_duration_seconds": request.duration_seconds,
                    "frame_count": frame_count, "fps": FRAMES_PER_SECOND,
                }, [frame], binding,
            )
            admitted = True
            return job, voice.source_sha256
        finally:
            if not admitted:
                if binding is not None:
                    self.gateway.voice_files.discard(job_id, binding)
                self.gateway._discard_prepared_frames(job_id, [frame])
                files.discard_unreferenced_asset(asset)

    def prepare_dispatch(self, job: dict[str, Any]) -> dict[str, Any]:
        job_id = str(job["id"])
        frames = self.gateway.store.get_job_frames(job_id)
        binding = self.gateway.store.get_job_voice(job_id)
        execution = voice_execution_from_snapshot(str(job["execution_snapshot_json"]))
        if len(frames) != 1 or frames[0]["role"] != "start" or binding is None:
            raise GatewayError("voice_binding_invalid", 422)
        frame = frames[0]
        if (
            job["h3_contract"] != "ref2va" or job["input_mode"] != "image"
            or job["quality"] != 8 or job["resolution"] != execution.resolution.value
            or job["frame_count"] != execution.frame_count or job["seed"] != execution.seed
            or job["requested_duration_seconds"] != execution.requested_duration_seconds
            or frame["prepared_input_name"] != execution.image_name
            or frame["sha256"] != execution.image_sha256
            or binding["prepared_input_name"] != execution.audio_name
            or binding["source_sha256"] != execution.audio_sha256
            or binding["prepared_sha256"] != execution.prepared_audio_sha256
        ):
            raise GatewayError("voice_snapshot_mismatch", 422)
        image_path = self.gateway.files.prepared_input_path(job_id=job_id, frame=frame)
        if image_path is None or not image_path.is_file() or image_path.is_symlink():
            raise GatewayError("voice_image_input_missing", 422)
        if sha256(image_path.read_bytes()).hexdigest() != execution.prepared_image_sha256:
            raise GatewayError("voice_image_integrity_mismatch", 422)
        self.gateway.voice_files.verify(job_id, binding)
        self.gateway.comfy.preflight_voice()
        return render_voice_workflow(
            self.gateway.workflow_template["prompt"], execution=execution,
            prompt=str(job["prompt"]),
        )
