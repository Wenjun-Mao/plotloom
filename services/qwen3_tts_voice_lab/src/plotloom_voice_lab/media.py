"""Immutable candidate audio and deterministic H3 reference preparation."""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


PREPARATION_VERSION = "mono_pcm16_32k_resample_poly_v1"
LOGGER = logging.getLogger(__name__)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic(path: Path, waveform: np.ndarray, sample_rate: int, subtype: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".pending-", suffix=".wav", dir=path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        sf.write(temp_path, waveform, sample_rate, subtype=subtype)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _validated_waveform(audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float]:
    waveform = np.asarray(audio, dtype=np.float32).reshape(-1)
    if sample_rate != 24000 or not waveform.size or not np.all(np.isfinite(waveform)):
        raise ValueError("invalid_model_audio")
    duration = len(waveform) / sample_rate
    if duration > 30 or np.max(np.abs(waveform)) > 1:
        raise ValueError("invalid_model_audio")
    return waveform, duration


def persist_candidate(data_dir: Path, candidate_id: str, audio: np.ndarray, sample_rate: int) -> dict:
    waveform, duration = _validated_waveform(audio, sample_rate)
    target = data_dir / "assets" / candidate_id
    source = target / "source.wav"
    if source.exists():
        raise FileExistsError("candidate_audio_already_exists")
    _write_atomic(source, waveform, sample_rate, "FLOAT")
    result = {
        "sourcePath": str(source),
        "sourceSha256": file_sha256(source),
        "sourceDurationSeconds": round(duration, 3),
        "sourceSampleRate": sample_rate,
        "h3Path": None,
        "h3Sha256": None,
        "h3Eligible": False,
        "h3IssueCode": None,
        "preparationVersion": PREPARATION_VERSION,
    }
    if not 1 <= duration <= 10:
        result["h3IssueCode"] = "h3.duration_out_of_range"
        return result

    h3_path = target / "h3.wav"
    try:
        factor = gcd(sample_rate, 32000)
        prepared = resample_poly(waveform, 32000 // factor, sample_rate // factor)
        _write_atomic(h3_path, prepared, 32000, "PCM_16")
        info = sf.info(h3_path)
        if info.channels != 1 or info.samplerate != 32000 or h3_path.stat().st_size > 2 * 1024 * 1024:
            result["h3IssueCode"] = "h3.invalid_prepared_audio"
            h3_path.unlink(missing_ok=True)
            return result
        result.update(h3Path=str(h3_path), h3Sha256=file_sha256(h3_path), h3Eligible=True)
    except Exception:
        LOGGER.exception("H3 reference preparation failed for candidate %s", candidate_id)
        h3_path.unlink(missing_ok=True)
        result["h3IssueCode"] = "h3.preparation_failed"
        return result
    return result


def persist_clone(data_dir: Path, clone_id: str, audio: np.ndarray, sample_rate: int) -> dict:
    waveform, duration = _validated_waveform(audio, sample_rate)
    path = data_dir / "clones" / clone_id / "audio.wav"
    if path.exists():
        raise FileExistsError("clone_audio_already_exists")
    _write_atomic(path, waveform, sample_rate, "FLOAT")
    return {
        "audioPath": str(path),
        "audioSha256": file_sha256(path),
        "durationSeconds": round(duration, 3),
        "sampleRate": sample_rate,
    }
