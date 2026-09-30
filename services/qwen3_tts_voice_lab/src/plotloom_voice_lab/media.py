"""Immutable candidate audio and deterministic H3 reference preparation."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


PREPARATION_VERSION = "mono_pcm16_32k_resample_poly_peak_guard_v2"
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
    waveform = np.asarray(audio, dtype=np.float32)
    if waveform.ndim != 1 or sample_rate not in {22050, 24000} or not waveform.size or not np.all(np.isfinite(waveform)):
        raise ValueError("invalid_model_audio")
    duration = len(waveform) / sample_rate
    if duration > 30:
        raise ValueError("invalid_model_audio")
    return waveform, duration


def copy_verified(source: Path, target: Path, expected_sha256: str) -> Path:
    """Publish an independent checked copy without exposing a partial file."""
    if not source.is_file() or file_sha256(source) != expected_sha256:
        raise ValueError("audio.corrupt")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("audio.already_exists")
    fd, temp_name = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
    temp_path = Path(temp_name)
    try:
        with source.open("rb") as incoming, os.fdopen(fd, "wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        os.chmod(temp_path, 0o600)
        if file_sha256(temp_path) != expected_sha256:
            raise ValueError("audio.copy_corrupt")
        os.replace(temp_path, target)
        return target
    finally:
        temp_path.unlink(missing_ok=True)


def _native_audio(path: Path, expected_sample_rate: int) -> tuple[np.ndarray, int, float, dict]:
    if path.is_symlink():
        raise ValueError("audio.invalid")
    info = sf.info(path)
    if (info.format != "WAV" or info.channels != 1 or info.samplerate != expected_sample_rate
            or not 0 < info.duration <= 30):
        raise ValueError("audio.invalid")
    waveform, sample_rate = sf.read(path, dtype="float32")
    waveform, duration = _validated_waveform(waveform, sample_rate)
    peak = float(np.max(np.abs(waveform)))
    warnings = ["audio.peak_exceeds_full_scale"] if peak > 1 else []
    # Full-scale integer samples can indicate upstream clipping; a derivative
    # cannot restore that information. This is a review warning, not a verdict.
    if info.subtype == "PCM_16" and np.any((waveform >= 32767 / 32768) | (waveform <= -1)):
        warnings.append("audio.possible_source_clipping")
    return waveform, sample_rate, duration, {
        "subtype": info.subtype, "peak": peak,
        "warnings": warnings,
    }


def persist_candidate_file(data_dir: Path, candidate_id: str, generation_id: str,
                           native: Path, expected_sample_rate: int) -> dict:
    waveform, sample_rate, duration, details = _native_audio(native, expected_sample_rate)
    target = data_dir / "assets" / candidate_id / generation_id
    source = target / "source.wav"
    if source.exists():
        raise FileExistsError("candidate_audio_already_exists")
    copy_verified(native, source, file_sha256(native))
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
        "audioDetails": details,
    }
    if not 1 <= duration <= 10:
        result["h3IssueCode"] = "h3.duration_out_of_range"
        return result

    h3_path = target / "h3.wav"
    try:
        factor = gcd(sample_rate, 32000)
        prepared = resample_poly(waveform, 32000 // factor, sample_rate // factor)
        # The native FLOAT WAV is authoritative. Only the named PCM derivative
        # is attenuated when needed, including resampling overshoot.
        peak = float(np.max(np.abs(prepared)))
        gain = min(1.0, .98 / peak) if peak else 1.0
        prepared = prepared * gain
        details["h3Preparation"] = {"version": PREPARATION_VERSION, "gain": gain, "sampleRate": 32000}
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


def persist_clone_file(data_dir: Path, clone_id: str, native: Path, expected_sample_rate: int) -> dict:
    _waveform, sample_rate, duration, details = _native_audio(native, expected_sample_rate)
    path = data_dir / "clones" / clone_id / "audio.wav"
    if path.exists():
        raise FileExistsError("clone_audio_already_exists")
    copy_verified(native, path, file_sha256(native))
    return {
        "audioPath": str(path),
        "audioSha256": file_sha256(path),
        "durationSeconds": round(duration, 3),
        "sampleRate": sample_rate,
        "audioDetails": details,
    }


def persist_candidate(data_dir: Path, candidate_id: str, generation_id: str, audio: np.ndarray, sample_rate: int) -> dict:
    """Fixture/import convenience; inference always supplies its native file."""
    waveform, _duration = _validated_waveform(audio, sample_rate)
    with tempfile.TemporaryDirectory() as staging:
        native = Path(staging) / "audio.wav"
        _write_atomic(native, waveform, sample_rate, "FLOAT")
        return persist_candidate_file(data_dir, candidate_id, generation_id, native, sample_rate)
