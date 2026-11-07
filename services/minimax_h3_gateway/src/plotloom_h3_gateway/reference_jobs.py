"""Ordered image-only Ref2VA admission and immutable dispatch preparation."""
from __future__ import annotations

import os
import uuid
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from .contracts import GatewayError
from .naming import timestamped_storage_name
from .profile_catalog import admitted_execution
from .reference_contracts import REFERENCE_MAX_BYTES, CreateReferenceJobRequest, reference_frame
from .reference_execution import (
    ReferenceExecution, ReferenceImage, reference_execution_from_snapshot, render_reference_workflow,
)
from .reference_files import ReferenceFiles

if TYPE_CHECKING:
    from .gateway import H3Gateway


class ReferenceJobs:
    def __init__(self, gateway: H3Gateway) -> None:
        self.gateway = gateway
        self.files = ReferenceFiles(gateway)

    def create(self, request: CreateReferenceJobRequest, contents: list[bytes]) -> dict[str, Any]:
        if len(contents) != len(request.references):
            raise GatewayError("reference_image_count_mismatch", 422)
        if sum(map(len, contents)) > REFERENCE_MAX_BYTES:
            raise GatewayError("reference_images_size_invalid", 413)
        self.gateway.comfy.preflight_references(len(contents))
        execution = admitted_execution(quality=8, resolution=request.resolution)
        job_id = f"h3_{uuid.uuid4().hex}"
        seed = request.seed if request.seed is not None else int.from_bytes(os.urandom(8), "big") >> 1
        assets, frames, images = [], [], []
        admitted = False
        try:
            for index, (timing, content) in enumerate(zip(request.references, contents, strict=True), 1):
                asset = self.files.add(content)
                assets.append(asset)
                frame = {"job_id": job_id, "role": f"reference_{index}", "asset_id": asset["id"],
                         "prepared_input_name": timestamped_storage_name(job_id, ".png", label=f"reference_{index}")}
                frames.append(frame)
                digest = self.files.prepare(frame, asset, execution, request.aspect_policy)
                images.append(ReferenceImage(index=index, atMs=timing.at_ms,
                    frameIndex=reference_frame(timing.at_ms), imageName=frame["prepared_input_name"],
                    sourceSha256=asset["sha256"], preparedSha256=digest))
            frozen = ReferenceExecution(request.resolution, request.duration_ms, seed,
                                        sha256(request.prompt.encode("utf-8")).hexdigest(), tuple(images))
            job = self.gateway.store.reserve_job({
                "id": job_id, "backend": "h3_video", "input_mode": "image", "h3_contract": "ref2va",
                "quality": 8, "resolution": request.resolution, "aspect_policy": request.aspect_policy,
                "background_mode": None, "execution_snapshot_json": frozen.snapshot_json(),
                "prompt": request.prompt, "seed": seed, "requested_duration_seconds": request.duration_ms / 1000,
                "frame_count": frozen.frame_count, "fps": 24,
            }, frames)
            admitted = True
            return job
        finally:
            if not admitted:
                self.gateway._discard_prepared_frames(job_id, frames)
                for asset in assets:
                    self.gateway.files.discard_unreferenced_asset(asset)

    def prepare_dispatch(self, job: dict[str, Any]) -> dict[str, Any]:
        execution = reference_execution_from_snapshot(job["execution_snapshot_json"])
        frames = self.gateway.store.get_job_frames(job["id"])
        if (job["backend"] != "h3_video" or job["h3_contract"] != "ref2va"
                or job["input_mode"] != "image" or job["quality"] != 8
                or job["resolution"] != execution.resolution or job["fps"] != 24
                or job["frame_count"] != execution.frame_count or job["seed"] != execution.seed
                or job["requested_duration_seconds"] != execution.duration_ms / 1000
                or len(frames) != len(execution.images)
                or self.gateway.store.get_job_voice(job["id"]) is not None):
            raise GatewayError("reference_snapshot_mismatch", 422)
        for frame, image in zip(frames, execution.images, strict=True):
            if (frame["role"] != f"reference_{image.index}"
                    or frame["prepared_input_name"] != image.imageName or frame["sha256"] != image.sourceSha256):
                raise GatewayError("reference_snapshot_mismatch", 422)
            self.files.verify(job["id"], frame, image)
        self.gateway.comfy.preflight_references(len(frames))
        return render_reference_workflow(self.gateway.workflow_template["prompt"], execution, job["prompt"])
