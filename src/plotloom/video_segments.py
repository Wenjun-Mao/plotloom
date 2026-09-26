"""Frame-addressed, non-destructive playback units from qualified H3 takes.

The provider output remains immutable. This module proves a decoded 24-fps
timeline, derives an exact contiguous presentation window, and checks the
derived audio/video before it can be offered for creator review.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


class VideoSegmentError(ValueError):
    """A take or window cannot satisfy the frame-exact playback contract."""


@dataclass(frozen=True)
class SegmentProbe:
    frame_count: int
    video_start: Fraction
    audio_start: Fraction
    audio_end: Fraction
    audio_sample_rate: int
    audio_samples: int
    width: int
    height: int
    format_duration: Fraction

    def evidence(self) -> dict[str, Any]:
        return {
            "frameCount": self.frame_count,
            "fps": "24/1",
            "videoStart": str(self.video_start),
            "audioStart": str(self.audio_start),
            "audioEnd": str(self.audio_end),
            "audioSampleRate": self.audio_sample_rate,
            "audioSamples": self.audio_samples,
            "width": self.width,
            "height": self.height,
            "formatDuration": str(self.format_duration),
        }


@dataclass(frozen=True)
class DerivedSegment:
    content: bytes
    source_probe: dict[str, Any]
    output_probe: dict[str, Any]
    in_frame: int
    out_frame: int

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


def _fraction(value: object, label: str) -> Fraction:
    try:
        result = Fraction(str(value))
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise VideoSegmentError(f"{label} has no exact timebase") from error
    if result.denominator == 0:
        raise VideoSegmentError(f"{label} has no exact timebase")
    return result


def _run(command: list[str], *, timeout: int = 90) -> bytes:
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VideoSegmentError("media probe or derivation did not finish") from error
    if result.returncode != 0:
        raise VideoSegmentError("media probe or derivation rejected the take")
    return result.stdout


def _frame_time(frame: dict[str, Any], time_base: Fraction) -> Fraction:
    stamp = frame.get("best_effort_timestamp", frame.get("pts"))
    try:
        return int(stamp) * time_base
    except (TypeError, ValueError) as error:
        raise VideoSegmentError("decoded frame lacks a presentation timestamp") from error


def _ceil(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def _audio_timestamps_follow_samples(
    times: list[Fraction], counts: list[int], sample_rate: int,
) -> bool:
    """Allow one sample of AAC timestamp rounding, never accumulating drift."""

    origin = times[0]
    samples = 0
    for time, count in zip(times, counts):
        expected = origin + Fraction(samples, sample_rate)
        if abs(time - expected) > Fraction(1, sample_rate):
            return False
        samples += count
    return True


def _probe(path: Path, *, strict_container: bool = False) -> SegmentProbe:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise VideoSegmentError("ffprobe is required for exact playback timing")
    try:
        payload = json.loads(_run([ffprobe, "-v", "error", "-show_streams", "-show_frames", "-show_format", "-of", "json", str(path)]))
        streams = payload["streams"]
        video = next(item for item in streams if item.get("codec_type") == "video")
        audio = next(item for item in streams if item.get("codec_type") == "audio")
        video_base = _fraction(video["time_base"], "video")
        audio_base = _fraction(audio["time_base"], "audio")
        sample_rate = int(audio["sample_rate"])
        width, height = int(video["width"]), int(video["height"])
        format_duration = _fraction(payload["format"]["duration"], "container duration")
        container = str(payload["format"]["format_name"])
        video_frames = [frame for frame in payload["frames"] if frame.get("media_type") == "video"]
        audio_frames = [frame for frame in payload["frames"] if frame.get("media_type") == "audio"]
    except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as error:
        raise VideoSegmentError("media does not expose exact video and audio evidence") from error
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise VideoSegmentError("playback segment requires H.264 video and AAC audio")
    if not ({"mp4", "mov"} & set(container.split(","))):
        raise VideoSegmentError("playback segment requires an MP4 container")
    if (video.get("r_frame_rate"), video.get("avg_frame_rate")) != ("24/1", "24/1"):
        raise VideoSegmentError("source must be constant 24-fps video")
    if sample_rate <= 0 or width <= 0 or height <= 0 or not video_frames or not audio_frames:
        raise VideoSegmentError("media has no complete picture and sound timeline")
    video_times = [_frame_time(frame, video_base) for frame in video_frames]
    if any(right - left != Fraction(1, 24) for left, right in pairwise(video_times)):
        raise VideoSegmentError("source video frames are not consecutive at 24 fps")
    audio_times = [_frame_time(frame, audio_base) for frame in audio_frames]
    try:
        audio_counts = [int(frame["nb_samples"]) for frame in audio_frames]
    except (KeyError, TypeError, ValueError) as error:
        raise VideoSegmentError("source audio lacks decoded sample counts") from error
    if any(count <= 0 for count in audio_counts):
        raise VideoSegmentError("source audio has an empty decoded frame")
    if not _audio_timestamps_follow_samples(audio_times, audio_counts, sample_rate):
        raise VideoSegmentError("source audio has a presentation gap or overlap")
    frame_count = len(video_frames)
    if video.get("nb_frames") not in (None, "N/A", str(frame_count)):
        raise VideoSegmentError("declared frame count differs from decoded frames")
    video_end = video_times[0] + Fraction(frame_count, 24)
    audio_end = audio_times[-1] + Fraction(audio_counts[-1], sample_rate)
    # A container may include one codec packet's edit-list tail. A larger
    # discrepancy is not evidence of a coherent presentation interval.
    media_start = min(video_times[0], audio_times[0])
    tolerance = Fraction(1024, sample_rate) if strict_container else max(Fraction(1, 24), Fraction(1024, sample_rate))
    if abs(format_duration - (max(video_end, audio_end) - media_start)) > tolerance:
        raise VideoSegmentError("container duration disagrees with decoded streams")
    return SegmentProbe(frame_count, video_times[0], audio_times[0], audio_end, sample_rate, sum(audio_counts), width, height, format_duration)


def derive_playback_segment(content: bytes, *, in_frame: int, out_frame: int, authored_duration_units: int) -> DerivedSegment:
    """Return verified MP4 bytes; caller persists them only as a proposal."""

    if not isinstance(in_frame, int) or not isinstance(out_frame, int) or in_frame < 0 or out_frame <= in_frame:
        raise VideoSegmentError("choose a nonempty contiguous frame window")
    if authored_duration_units <= 0 or authored_duration_units * 24 % 1_000:
        raise VideoSegmentError("authored duration is not representable at 24 fps")
    required_frames = authored_duration_units * 24 // 1_000
    if out_frame - in_frame != required_frames:
        raise VideoSegmentError("chosen window must equal the authored shot duration")
    if len(content) > 128 * 1024 * 1024:
        raise VideoSegmentError("source take is too large for bounded local derivation")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise VideoSegmentError("ffmpeg is required for exact playback timing")
    with TemporaryDirectory(prefix="plotloom-segment-") as directory:
        source = Path(directory) / "source.mp4"
        output = Path(directory) / "segment.mp4"
        source.write_bytes(content)
        probe = _probe(source)
        if out_frame > probe.frame_count:
            raise VideoSegmentError("source take is shorter than the chosen window")
        start = probe.video_start + Fraction(in_frame, 24)
        end = probe.video_start + Fraction(out_frame, 24)
        if start < probe.audio_start or end > probe.audio_end:
            raise VideoSegmentError("source audio does not cover the chosen window")
        first_sample = _ceil((start - probe.audio_start) * probe.audio_sample_rate)
        last_sample = _ceil((end - probe.audio_start) * probe.audio_sample_rate)
        if last_sample > probe.audio_samples or first_sample < 0:
            raise VideoSegmentError("source audio sample window is unavailable")
        filters = (
            f"[0:v:0]trim=start_frame={in_frame}:end_frame={out_frame},setpts=N/(24*TB)[v];"
            f"[0:a:0]atrim=start_sample={first_sample}:end_sample={last_sample},asetpts=N/SR/TB[a]"
        )
        _run([ffmpeg, "-v", "error", "-i", str(source), "-filter_complex", filters,
              "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
              "-r", "24", "-c:a", "aac", "-ar", str(probe.audio_sample_rate),
              "-movflags", "+faststart", "-y", str(output)])
        derived = _probe(output, strict_container=True)
        if derived.frame_count != required_frames or derived.video_start != 0:
            raise VideoSegmentError("derivative video does not match the exact frame window")
        expected_audio_samples = last_sample - first_sample
        if abs(derived.audio_samples - expected_audio_samples) > 1 or derived.audio_start != 0:
            raise VideoSegmentError("derivative audio does not match the exact sample window")
        if abs(derived.audio_end - Fraction(required_frames, 24)) > Fraction(1, probe.audio_sample_rate):
            raise VideoSegmentError("derivative audio extends beyond the selected window")
        return DerivedSegment(output.read_bytes(), probe.evidence(), derived.evidence(), in_frame, out_frame)
