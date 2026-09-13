"""Gateway-owned image preparation, MP4 handoff, and retention operations."""
from __future__ import annotations

import os
import shutil
import uuid
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from .contracts import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_IMAGE_PIXELS,
    MAX_UPLOAD_BYTES,
    AspectPolicy,
    GatewayError,
    GatewaySettings,
)
from .naming import ASSET_ID, H3_JOB_ID, is_owned_storage_name, is_safe_path_part, timestamped_storage_name
from .profile_catalog import GatewayProfile
from .store import GatewayStore


class GatewayFiles:
    """Own only files named by the gateway's SQLite control plane."""

    def __init__(self, settings: GatewaySettings, store: GatewayStore) -> None:
        self.settings = settings
        self.store = store
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.comfy_input_dir.mkdir(parents=True, exist_ok=True)
        self.settings.comfy_output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = self.settings.data_dir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.managed_outputs_dir = self.settings.data_dir / "outputs"
        self.managed_outputs_dir.mkdir(parents=True, exist_ok=True)

    def add_asset(self, content: bytes, *, mime_type: str) -> dict[str, Any]:
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise GatewayError("unsupported_image_mime", 415)
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise GatewayError("image_size_invalid", 413)
        try:
            with Image.open(BytesIO(content)) as source:
                source.verify()
            with Image.open(BytesIO(content)) as source:
                width, height = source.size
        except (UnidentifiedImageError, OSError) as error:
            raise GatewayError("image_decode_invalid", 422) from error
        if width * height > MAX_IMAGE_PIXELS:
            raise GatewayError("image_pixels_exceed_limit", 422)
        asset_id = f"asset_{uuid.uuid4().hex}"
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime_type]
        path = self.assets_dir / timestamped_storage_name(asset_id, suffix)
        path.write_bytes(content)
        return self.store.put_asset(
            asset_id=asset_id,
            mime_type=mime_type,
            width=width,
            height=height,
            digest=sha256(content).hexdigest(),
            path=path,
        )

    def prepare_job_input(self, *, job: dict[str, Any], asset: dict[str, Any], profile: GatewayProfile) -> None:
        _prepare_input(
            source=Path(str(asset["path"])),
            destination=self.settings.comfy_input_dir / str(job["prepared_input_name"]),
            target_width=profile.width,
            target_height=profile.height,
            policy=str(job["aspect_policy"]),
        )

    def read_output(self, job: dict[str, Any]) -> bytes:
        path = self.managed_output_path(job)
        if path is None or not path.is_file() or path.is_symlink():
            self.store.mark_output_expired(str(job["id"]), error_code="gateway_output_missing")
            raise GatewayError("gateway_output_missing", 410)
        try:
            return path.read_bytes()
        except OSError as error:
            raise GatewayError("gateway_output_unavailable", 502) from error

    def cleanup_expired_outputs(self) -> int:
        """Delete only exact, database-owned gateway outputs past 72 hours."""

        removed = 0
        for job in self.store.list_expired_managed_outputs():
            path = self.managed_output_path(job)
            if path is None or path.is_symlink():
                self.store.mark_output_expired(str(job["id"]), error_code="gateway_output_storage_invalid")
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                # Keep the completed record and retry later. Cleanup never
                # expands beyond this exact, database-owned managed file.
                continue
            self.store.mark_output_expired(str(job["id"]), error_code="gateway_output_expired")
            removed += 1
        self.cleanup_expired_gateway_inputs_and_assets()
        return removed

    def cleanup_expired_job_records(self) -> int:
        """Purge only due control-plane records after their audit interval."""

        removed = 0
        for job in self.store.list_purgeable_expired_job_records():
            if self.store.purge_expired_job_record(str(job["id"])):
                removed += 1
        self.cleanup_pending_asset_purges()
        return removed

    def cleanup_expired_gateway_inputs_and_assets(self) -> int:
        """Release transfer-only keyframes once their last video has expired."""

        prepared_removed = 0
        for job in self.store.list_output_expired_jobs():
            input_path = self.prepared_input_path(job)
            try:
                if input_path is not None and input_path.exists():
                    input_path.unlink()
                    prepared_removed += 1
            except OSError:
                # The row is a safe retry marker. A failure to remove a tracked
                # Comfy input must not become a later broad filesystem cleanup.
                continue
            self.store.claim_asset_after_last_output_expiry(str(job["asset_id"]))
        return prepared_removed + self.cleanup_pending_asset_purges()

    def cleanup_pending_asset_purges(self) -> int:
        """Delete only gateway-owned uploads after their last job is gone."""

        removed = 0
        for asset in self.store.list_pending_asset_purges():
            path = self.gateway_asset_path(asset)
            if path is None:
                continue
            try:
                had_file = path.exists()
                path.unlink(missing_ok=True)
            except OSError:
                continue
            if had_file:
                removed += 1
            self.store.delete_pending_unreferenced_asset(str(asset["id"]))
        return removed

    def transfer_completed_output(self, job: dict[str, Any]) -> dict[str, Any]:
        """Copy, verify, then remove ComfyUI's exact expected output file."""

        source = self.comfy_output_path(job)
        destination = self.managed_output_path(job)
        if source is None or destination is None:
            return self.store.update_job(
                str(job["id"]), status="failed", error_code="gateway_output_storage_invalid"
            )
        try:
            if destination.exists():
                if not destination.is_file() or destination.is_symlink():
                    raise OSError("managed output path is not a regular file")
                digest, size_bytes = _file_digest(destination)
                if source.exists():
                    if not source.is_file() or source.is_symlink():
                        raise OSError("ComfyUI output path is not a regular file")
                    if _file_digest(source) != (digest, size_bytes):
                        return self.store.update_job(
                            str(job["id"]), status="failed", error_code="gateway_output_integrity_mismatch"
                        )
            else:
                if not source.is_file() or source.is_symlink():
                    return self.store.update_job(
                        str(job["id"]), status="failed", error_code="comfy_output_missing"
                    )
                digest, size_bytes = _copy_file_atomically(source, destination)
            if source.exists():
                if not source.is_file() or source.is_symlink():
                    raise OSError("ComfyUI output path is not a regular file")
                source.unlink()
        except OSError:
            return self.store.update_job(
                str(job["id"]), status="transfer_pending", error_code="gateway_output_transfer_pending"
            )
        return self.store.mark_managed_output(
            str(job["id"]), output_name=destination.name, digest=digest, size_bytes=size_bytes
        )

    def comfy_output_path(self, job: dict[str, Any]) -> Path | None:
        filename = job.get("output_filename")
        subfolder = job.get("output_subfolder")
        output_type = job.get("output_type")
        if (
            not isinstance(filename, str)
            or not isinstance(subfolder, str)
            or output_type != "output"
            or not is_safe_path_part(filename)
            or not is_safe_path_part(subfolder)
        ):
            return None
        candidate = self.settings.comfy_output_dir / subfolder / filename
        try:
            root = self.settings.comfy_output_dir.resolve()
            resolved = candidate.resolve(strict=False)
        except OSError:
            return None
        if root not in resolved.parents or candidate.is_symlink():
            return None
        return candidate

    def managed_output_path(self, job: dict[str, Any]) -> Path | None:
        job_id = str(job.get("id", ""))
        name = job.get("managed_output_name")
        if (
            H3_JOB_ID.fullmatch(job_id) is None
            or not is_owned_storage_name(name, object_id=job_id, suffixes=(".mp4",))
        ):
            return None
        return self.managed_outputs_dir / str(name)

    def prepared_input_path(self, job: dict[str, Any]) -> Path | None:
        job_id = str(job.get("id", ""))
        name = job.get("prepared_input_name")
        if (
            H3_JOB_ID.fullmatch(job_id) is None
            or not is_owned_storage_name(name, object_id=job_id, suffixes=(".png",))
        ):
            return None
        return self._direct_child_path(self.settings.comfy_input_dir, str(name))

    def gateway_asset_path(self, asset: dict[str, Any]) -> Path | None:
        asset_id = asset.get("id")
        stored_path = asset.get("path")
        if not isinstance(asset_id, str) or not isinstance(stored_path, str):
            return None
        if ASSET_ID.fullmatch(asset_id) is None:
            return None
        candidate = Path(stored_path)
        if not is_owned_storage_name(candidate.name, object_id=asset_id, suffixes=(".jpg", ".png", ".webp")):
            return None
        try:
            root = self.assets_dir.resolve()
            resolved = candidate.resolve(strict=False)
        except OSError:
            return None
        if resolved.parent != root or candidate.is_symlink():
            return None
        return candidate

    @staticmethod
    def _direct_child_path(root: Path, name: str) -> Path | None:
        candidate = root / name
        try:
            resolved_root = root.resolve()
            resolved = candidate.resolve(strict=False)
        except OSError:
            return None
        if resolved.parent != resolved_root or candidate.is_symlink():
            return None
        return candidate


def _prepare_input(
    *, source: Path, destination: Path, target_width: int, target_height: int, policy: AspectPolicy
) -> None:
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
            else:
                raise GatewayError("aspect_policy_invalid", 422)
            image.save(destination, "PNG", optimize=True)
    except GatewayError:
        raise
    except (UnidentifiedImageError, OSError) as error:
        raise GatewayError("input_prepare_failed", 422) from error


def _copy_file_atomically(source: Path, destination: Path) -> tuple[str, int]:
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.partial")
    try:
        with source.open("rb") as input_file, temporary.open("xb") as output_file:
            shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return _file_digest(destination)


def _file_digest(path: Path) -> tuple[str, int]:
    digest = sha256()
    size_bytes = 0
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
            size_bytes += len(chunk)
    return digest.hexdigest(), size_bytes
