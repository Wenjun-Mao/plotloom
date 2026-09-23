"""Synthetic, labelled timing evidence; never a production-generation receipt."""

import shutil
import subprocess
import sys
from array import array
from itertools import pairwise
from pathlib import Path

import pytest

from plotloom.video_segments import VideoSegmentError, derive_playback_segment


@pytest.fixture(scope="module")
def synthetic_eight_second_take(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg tools are required for synthetic segment verification")
    output: Path = tmp_path_factory.mktemp("synthetic-segment") / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
         "-frames:v", "192", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", "-y", str(output)],
        check=True, timeout=90,
    )
    return output.read_bytes()


def test_synthetic_middle_six_second_window(synthetic_eight_second_take: bytes) -> None:
    segment = derive_playback_segment(
        synthetic_eight_second_take, in_frame=24, out_frame=168, authored_duration_units=6_000
    )
    assert segment.source_probe["frameCount"] == 192
    assert segment.output_probe["frameCount"] == 144
    assert segment.output_probe["videoStart"] == "0"
    assert segment.in_frame == 24 and segment.out_frame == 168
    assert len(segment.digest) == 64


def test_synthetic_whole_eight_second_window(synthetic_eight_second_take: bytes) -> None:
    segment = derive_playback_segment(
        synthetic_eight_second_take, in_frame=0, out_frame=192, authored_duration_units=8_000
    )
    assert segment.output_probe["frameCount"] == 192


def test_synthetic_picture_and_sound_markers_follow_arbitrary_window(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg tools are required for synthetic segment verification")
    source = tmp_path / "marked-source.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error",
        "-f", "lavfi", "-i", "color=c=red:size=128x128:rate=24:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=1",
        "-f", "lavfi", "-i", "color=c=blue:size=128x128:rate=24:duration=6",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=6",
        "-f", "lavfi", "-i", "color=c=green:size=128x128:rate=24:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=1",
        "-filter_complex", "[0:v][2:v][4:v]concat=n=3:v=1:a=0[v];[1:a][3:a][5:a]concat=n=3:v=0:a=1[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart", "-y", str(source),
    ], check=True, timeout=90)

    def frame_channels(content: bytes, frame: int) -> tuple[float, float, float]:
        clip = tmp_path / "inspect.mp4"
        clip.write_bytes(content)
        raw = subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"select=eq(n\\,{frame})",
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ], capture_output=True, check=True, timeout=30).stdout
        assert len(raw) == 128 * 128 * 3
        channels = [sum(raw[channel::3]) / (128 * 128) for channel in range(3)]
        return channels[0], channels[1], channels[2]

    def tone_hz(content: bytes, offset_seconds: float) -> float:
        clip = tmp_path / "inspect.mp4"
        clip.write_bytes(content)
        raw = subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "48000",
            "-f", "s16le", "-",
        ], capture_output=True, check=True, timeout=30).stdout
        samples = array("h"); samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()
        start = int(offset_seconds * 48_000)
        window = samples[start:start + 12_000]
        return sum(left <= 0 < right for left, right in pairwise(window)) * 4

    middle = derive_playback_segment(source.read_bytes(), in_frame=24, out_frame=168, authored_duration_units=6_000)
    blue = frame_channels(middle.content, 0)
    assert blue[2] > blue[0] + 80 and blue[2] > blue[1] + 80
    assert 430 <= tone_hz(middle.content, 0.25) <= 450
    assert 430 <= tone_hz(middle.content, 5.5) <= 450

    late = derive_playback_segment(source.read_bytes(), in_frame=48, out_frame=192, authored_duration_units=6_000)
    green = frame_channels(late.content, 143)
    assert green[1] > green[0] + 50 and green[1] > green[2] + 50
    assert 870 <= tone_hz(late.content, 5.5) <= 890


def test_synthetic_nonzero_common_pts_keeps_exact_audio_window(
    synthetic_eight_second_take: bytes, tmp_path: Path,
) -> None:
    original = tmp_path / "source.mp4"
    shifted = tmp_path / "shifted.mp4"
    original.write_bytes(synthetic_eight_second_take)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(original),
         "-vf", "setpts=PTS+1/TB", "-af", "asetpts=PTS+1/TB",
         "-c:v", "libx264", "-c:a", "aac", "-y", str(shifted)],
        check=True, timeout=90,
    )
    segment = derive_playback_segment(
        shifted.read_bytes(), in_frame=12, out_frame=156,
        authored_duration_units=6_000,
    )
    assert segment.output_probe["frameCount"] == 144
    assert segment.output_probe["videoStart"] == "0"
    assert abs(segment.output_probe["audioSamples"] - 288_000) <= 1


def test_synthetic_short_audio_and_variable_cadence_are_refused(tmp_path: Path) -> None:
    short_audio = tmp_path / "short-audio.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=640x360:rate=24:duration=8",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5",
         "-frames:v", "192", "-c:v", "libx264", "-c:a", "aac", "-y", str(short_audio)],
        check=True, timeout=90,
    )
    with pytest.raises(VideoSegmentError, match="audio does not cover"):
        derive_playback_segment(short_audio.read_bytes(), in_frame=24, out_frame=168, authored_duration_units=6_000)

    variable = tmp_path / "variable.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=640x360:rate=24:duration=8",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
         "-vf", "setpts=2*PTS", "-fps_mode", "vfr", "-frames:v", "192",
         "-c:v", "libx264", "-c:a", "aac", "-y", str(variable)],
        check=True, timeout=90,
    )
    with pytest.raises(VideoSegmentError, match="24-fps|consecutive"):
        derive_playback_segment(variable.read_bytes(), in_frame=24, out_frame=168, authored_duration_units=6_000)


def test_corrupt_source_is_refused() -> None:
    with pytest.raises(VideoSegmentError):
        derive_playback_segment(b"not a video", in_frame=0, out_frame=144, authored_duration_units=6_000)


@pytest.mark.parametrize("start,end,duration", [(0, 143, 6_000), (49, 193, 6_000), (0, 192, 6_001)])
def test_invalid_window_fails_closed(
    synthetic_eight_second_take: bytes, start: int, end: int, duration: int
) -> None:
    with pytest.raises(VideoSegmentError):
        derive_playback_segment(
            synthetic_eight_second_take, in_frame=start, out_frame=end,
            authored_duration_units=duration,
        )
