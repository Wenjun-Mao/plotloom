"""Indexed private voice inputs with immutable dispatch and expiry checks."""
import stat
from hashlib import sha256
from pathlib import Path

from .contracts import GatewayError
from .naming import is_gateway_job_id, is_owned_storage_name, timestamped_storage_name
from .private_files import write_new
from .reference_audio_contracts import ReferenceAudio
from . import reference_audio_store as audio_store


class ReferenceAudioFiles:
    def __init__(self, gateway):
        self.gateway = gateway
        self.root = gateway.settings.data_dir / "reference_audio_inputs"
        self.root.mkdir(parents=True, exist_ok=True)

    def prepare(self, job_id, index, speaker, voice) -> dict:
        name = timestamped_storage_name(job_id, ".wav", label=f"audio_reference_{index}")
        binding = {"ordinal": index, "speaker": speaker,
            "source_sha256": voice.source_sha256, "prepared_sha256": voice.prepared_sha256,
            "source_size_bytes": len(voice.source_bytes), "duration_ms": voice.duration_ms,
            "source_name": name, "prepared_input_name": name}
        source, prepared = self.paths(job_id, binding)
        owner = self.gateway.settings.comfy_input_dir.stat()
        written = []
        try:
            write_new(source, voice.source_bytes)
            written.append(source)
            write_new(prepared, voice.prepared_bytes, owner=(owner.st_uid, owner.st_gid))
            written.append(prepared)
        except OSError as error:
            for path in written:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise GatewayError("reference_audio_storage_failed", 500) from error
        return binding

    def paths(self, job_id, binding) -> tuple[Path, Path]:
        index = binding.get("ordinal")
        names = (binding.get("source_name"), binding.get("prepared_input_name"))
        if (not is_gateway_job_id(job_id) or type(index) is not int or not 1 <= index <= 3
                or any(not is_owned_storage_name(name, object_id=job_id, suffixes=(".wav",),
                    allow_reference_audio_label=True) or not name.endswith(f"_audio_reference_{index}.wav")
                    for name in names)):
            raise GatewayError("reference_audio_storage_invalid", 422)
        result = (self.root / names[0], self.gateway.settings.comfy_input_dir / names[1])
        if any(path.is_symlink() or path.resolve().parent != parent.resolve()
               for path, parent in zip(result, (self.root, self.gateway.settings.comfy_input_dir))):
            raise GatewayError("reference_audio_storage_invalid", 422)
        return result

    def verify(self, job_id, binding, audio: ReferenceAudio) -> None:
        expected = {"ordinal": audio.index, "speaker": audio.speaker,
            "source_sha256": audio.sourceSha256, "prepared_sha256": audio.preparedSha256,
            "source_size_bytes": audio.sourceSizeBytes, "duration_ms": audio.durationMs,
            "source_name": audio.audioName, "prepared_input_name": audio.audioName}
        if any(binding.get(key) != value for key, value in expected.items()) or binding.get("released_at"):
            raise GatewayError("reference_audio_snapshot_mismatch", 422)
        source, prepared = self.paths(job_id, binding)
        owner = self.gateway.settings.comfy_input_dir.stat()
        source_owner = self.root.stat()
        try:
            for path, digest in ((source, audio.sourceSha256), (prepared, audio.preparedSha256)):
                metadata = path.stat()
                if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
                    raise GatewayError("reference_audio_permissions_invalid", 422)
                expected_owner = owner if path == prepared else source_owner
                if (metadata.st_uid, metadata.st_gid) != (expected_owner.st_uid, expected_owner.st_gid):
                    raise GatewayError("reference_audio_permissions_invalid", 422)
                if sha256(path.read_bytes()).hexdigest() != digest:
                    raise GatewayError("reference_audio_integrity_mismatch", 422)
        except OSError as error:
            raise GatewayError("reference_audio_input_missing", 422) from error

    def discard(self, job_id, binding) -> None:
        for path in self.paths(job_id, binding):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def cleanup_due(self) -> int:
        removed = 0
        for job_id in audio_store.due_jobs(self.gateway.store):
            with self.gateway.store._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if not audio_store.is_due(connection, job_id):
                    continue
                # An unreleased audio row also protects this job's still inputs
                # from record purge until every prepared image was released.
                images_released = True
                for frame in self.gateway.store.get_job_frames(job_id):
                    path = self.gateway.files.prepared_input_path(job_id=job_id, frame=frame)
                    if path is None or path.is_symlink():
                        images_released = False
                        continue
                    try:
                        existed = path.exists()
                        path.unlink(missing_ok=True)
                        removed += int(existed)
                    except OSError:
                        images_released = False
                if not images_released:
                    continue
                for row in audio_store.rows(connection, job_id):
                    if row["released_at"] is not None:
                        continue
                    try:
                        paths = self.paths(job_id, row)
                        for path in paths:
                            existed = path.exists()
                            path.unlink(missing_ok=True)
                            removed += int(existed)
                    except (GatewayError, OSError):
                        continue
                    connection.execute("""UPDATE job_reference_audio_bindings
                        SET released_at=CURRENT_TIMESTAMP WHERE job_id=? AND ordinal=?""",
                        (job_id, row["ordinal"]))
        return removed
