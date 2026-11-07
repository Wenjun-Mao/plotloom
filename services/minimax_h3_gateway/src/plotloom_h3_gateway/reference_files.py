"""Private ordered still inputs using existing gateway geometry and retention."""
from __future__ import annotations

import os
import stat
import tempfile
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, UnidentifiedImageError

from .contracts import MAX_IMAGE_PIXELS, MAX_UPLOAD_BYTES, GatewayError
from .media import _prepare_input
from .reference_execution import ReferenceImage

if TYPE_CHECKING:
    from .gateway import H3Gateway


class ReferenceFiles:
    def __init__(self, gateway: H3Gateway) -> None:
        self.gateway = gateway

    def add(self, content: bytes) -> dict[str, Any]:
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise GatewayError("image_size_invalid", 413)
        try:
            with Image.open(BytesIO(content)) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise GatewayError("image_pixels_exceed_limit", 422)
                if getattr(image, "n_frames", 1) != 1:
                    raise GatewayError("reference_image_must_be_single_still", 422)
                if (image.mode in {"RGBA", "LA"} or "transparency" in image.info) and (
                    image.convert("RGBA").getextrema()[3] != (255, 255)
                ):
                    raise GatewayError("reference_image_transparency_not_supported", 422)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise GatewayError("image_decode_invalid", 422) from error
        return self.gateway.files.add_asset(content, private=True)

    def prepare(self, frame: dict[str, Any], asset: dict[str, Any], execution, policy: str) -> str:
        files = self.gateway.files
        destination = files.prepared_input_path(job_id=frame["job_id"], frame=frame)
        source = files.gateway_asset_path(asset)
        if destination is None or source is None:
            raise GatewayError("reference_storage_invalid", 500)
        fd, name = tempfile.mkstemp(prefix=".reference-", suffix=".png", dir=destination.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            _prepare_input(source=source, destination=temporary, target_width=execution.width,
                           target_height=execution.height, policy=policy)
            digest = sha256(temporary.read_bytes()).hexdigest()
            owner = destination.parent.stat()
            os.chown(temporary, owner.st_uid, owner.st_gid)
            os.link(temporary, destination)
            return digest
        except OSError as error:
            raise GatewayError("reference_storage_failed", 500) from error
        finally:
            temporary.unlink(missing_ok=True)

    def verify(self, job_id: str, frame: dict[str, Any], image: ReferenceImage) -> None:
        files = self.gateway.files
        source = files.gateway_asset_path(frame)
        prepared = files.prepared_input_path(job_id=job_id, frame=frame)
        owner = self.gateway.settings.comfy_input_dir.stat()
        for path, expected in ((source, image.sourceSha256), (prepared, image.preparedSha256)):
            if path is None or path.is_symlink() or not path.is_file():
                raise GatewayError("reference_input_missing", 422)
            try:
                metadata = path.stat()
                if stat.S_IMODE(metadata.st_mode) != 0o600:
                    raise GatewayError("reference_input_permissions_invalid", 422)
                if path == prepared and (metadata.st_uid, metadata.st_gid) != (owner.st_uid, owner.st_gid):
                    raise GatewayError("reference_input_permissions_invalid", 422)
                if sha256(path.read_bytes()).hexdigest() != expected:
                    raise GatewayError("reference_input_integrity_mismatch", 422)
            except OSError as error:
                raise GatewayError("reference_input_missing", 422) from error

    def cleanup_due(self) -> int:
        removed = 0
        for job in self.gateway.store.list_due_reference_inputs():
            for frame in self.gateway.store.get_job_frames(job["id"]):
                path = self.gateway.files.prepared_input_path(job_id=job["id"], frame=frame)
                if path is None or path.is_symlink():
                    continue
                try:
                    existed = path.exists()
                    path.unlink(missing_ok=True)
                    removed += int(existed)
                except OSError:
                    continue
        return removed
