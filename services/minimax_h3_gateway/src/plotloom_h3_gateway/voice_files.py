"""Private per-job Ref2VA audio files and bounded retention."""
from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path
from typing import Any

from .contracts import GatewayError, GatewaySettings
from .media import GatewayFiles
from .naming import is_gateway_job_id, is_owned_storage_name, timestamped_storage_name
from .store import GatewayStore
from .voice_reference import CanonicalVoice


class VoiceFiles:
    def __init__(self, settings: GatewaySettings, store: GatewayStore, files: GatewayFiles) -> None:
        self._settings = settings
        self._store = store
        self._files = files
        self._source_dir = settings.data_dir / "voice_inputs"
        self._source_dir.mkdir(parents=True, exist_ok=True)

    def prepare(self, *, job_id: str, voice: CanonicalVoice) -> dict[str, Any]:
        """Write source and canonical Comfy inputs under one unguessable job ID."""

        name = timestamped_storage_name(job_id, ".wav", label="voice")
        binding = {
            "source_sha256": voice.source_sha256,
            "prepared_sha256": voice.prepared_sha256,
            "source_size_bytes": len(voice.source_bytes),
            "duration_ms": voice.duration_ms,
            "source_name": name,
            "prepared_input_name": name,
        }
        source = self.source_path(job_id, binding)
        prepared = self.prepared_path(job_id, binding)
        if source is None or prepared is None:
            raise GatewayError("voice_storage_invalid", 500)
        written: list[Path] = []
        try:
            _write_new(source, voice.source_bytes)
            written.append(source)
            # ComfyUI may run as a different user from the gateway. Keep the
            # shared input private, but give its directory owner read access.
            input_owner = self._settings.comfy_input_dir.stat()
            _write_new(
                prepared, voice.prepared_bytes,
                owner=(input_owner.st_uid, input_owner.st_gid),
            )
            written.append(prepared)
        except OSError as error:
            for path in written:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise GatewayError("voice_storage_failed", 500) from error
        return binding

    def verify(self, job_id: str, binding: dict[str, Any]) -> None:
        """Refuse dispatch when a frozen voice file was removed or modified."""

        source = self.source_path(job_id, binding)
        prepared = self.prepared_path(job_id, binding)
        if source is None or prepared is None:
            raise GatewayError("voice_input_missing", 422)
        for path, expected in (
            (source, binding["source_sha256"]), (prepared, binding["prepared_sha256"])
        ):
            if not path.is_file() or path.is_symlink():
                raise GatewayError("voice_input_missing", 422)
            try:
                digest = sha256(path.read_bytes()).hexdigest()
            except OSError as error:
                raise GatewayError("voice_input_missing", 422) from error
            if digest != expected:
                raise GatewayError("voice_input_integrity_mismatch", 422)

    def discard(self, job_id: str, binding: dict[str, Any]) -> None:
        for path in (self.source_path(job_id, binding), self.prepared_path(job_id, binding)):
            if path is not None and not path.is_symlink():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    def cleanup_due(self) -> int:
        removed = 0
        for binding in self._store.list_due_voice_inputs():
            job_id = str(binding["job_id"])
            frames = self._store.get_job_frames(job_id)
            image_path = (
                self._files.prepared_input_path(job_id=job_id, frame=frames[0])
                if len(frames) == 1 and frames[0]["role"] == "start" else None
            )
            paths = (self.source_path(job_id, binding), self.prepared_path(job_id, binding), image_path)
            if any(path is None or path.is_symlink() for path in paths):
                continue
            released = True
            for path in paths:
                try:
                    existed = path.exists()
                    path.unlink(missing_ok=True)
                    removed += int(existed)
                except OSError:
                    released = False
            if released:
                self._store.mark_voice_released(job_id)
        return removed

    def source_path(self, job_id: str, binding: dict[str, Any]) -> Path | None:
        return self._owned_path(self._source_dir, job_id, binding.get("source_name"))

    def prepared_path(self, job_id: str, binding: dict[str, Any]) -> Path | None:
        return self._owned_path(self._settings.comfy_input_dir, job_id, binding.get("prepared_input_name"))

    @staticmethod
    def _owned_path(root: Path, job_id: str, name: object) -> Path | None:
        if not is_gateway_job_id(job_id) or not is_owned_storage_name(
            name, object_id=job_id, suffixes=(".wav",), allow_voice_label=True
        ):
            return None
        candidate = root / str(name)
        try:
            if candidate.resolve(strict=False).parent != root.resolve() or candidate.is_symlink():
                return None
        except OSError:
            return None
        return candidate


def _write_new(path: Path, content: bytes, *, owner: tuple[int, int] | None = None) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            if owner is not None:
                os.fchown(stream.fileno(), *owner)
    except OSError:
        path.unlink(missing_ok=True)
        raise
