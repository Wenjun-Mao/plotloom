"""Bounded download and probe helpers for remote P2 video candidates."""
from __future__ import annotations

import ipaddress
import json
import math
import shutil
import subprocess
from tempfile import NamedTemporaryFile
from dataclasses import dataclass
from urllib.parse import urlparse


class VideoIngestionError(RuntimeError):
    pass


class MediaProbeUnavailable(VideoIngestionError):
    pass


@dataclass(frozen=True)
class ObservedVideo:
    duration_seconds: float
    width: int
    height: int
    video_codec: str
    audio_codec: str | None
    container: str = "mp4"


def assert_public_https_url(url: str) -> None:
    """Reject obvious non-public endpoints before a provider download.

    The real transport must additionally pin/validate resolved addresses. This
    small boundary prevents accidental reuse of a local/Tailscale URL in the
    adapter and makes redirects a gateway-level opt-in (P2 never enables it).
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise VideoIngestionError("provider download URL must be an HTTPS URL without credentials")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise VideoIngestionError("provider download URL is not publicly routable")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_unspecified:
        raise VideoIngestionError("provider download URL resolves to a forbidden address")


def probe_video(content: bytes, *, ffprobe: str = "ffprobe", timeout_seconds: float = 10.0) -> ObservedVideo:
    """Require portable FFmpeg tools; metadata alone is not acceptance evidence."""
    executable = shutil.which(ffprobe)
    if executable is None:
        raise MediaProbeUnavailable("ffprobe is required to validate downloaded video before publication")
    completed = subprocess.run(
        [executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", "pipe:0"],
        input=content, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False,
    )
    if completed.returncode != 0:
        raise VideoIngestionError("ffprobe could not decode the downloaded video")
    try:
        payload = json.loads(completed.stdout)
        streams = payload["streams"]
        video = next(item for item in streams if item.get("codec_type") == "video")
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        duration = float(payload["format"]["duration"])
        width, height = int(video["width"]), int(video["height"])
        codec = str(video["codec_name"])
        container = str(payload["format"]["format_name"])
    except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as error:
        raise VideoIngestionError("ffprobe output did not establish playable video metadata") from error
    audio_codec = str(audio["codec_name"]) if audio else None
    if not math.isfinite(duration) or duration <= 0 or duration > 30 or width <= 0 or height <= 0 or max(width, height) > 3_840 or min(width, height) < 360 or not codec:
        raise VideoIngestionError("downloaded video has invalid duration or dimensions")
    if codec != "h264" or audio_codec != "aac":
        raise VideoIngestionError("downloaded video has unsupported browser playback codecs")
    if not ({"mp4", "mov"} & set(container.split(","))):
        raise VideoIngestionError("downloaded video has an unsupported browser playback container")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise MediaProbeUnavailable("ffmpeg is required to decode downloaded video before publication")
    # MP4 indexes commonly live at EOF; piping makes a valid non-faststart
    # file look truncated. Stage the bounded bytes and decode the exact file.
    with NamedTemporaryFile(prefix="plotloom-video-probe-", suffix=".media") as staged:
        staged.write(content)
        staged.flush()
        decoded = subprocess.run(
            [ffmpeg, "-v", "error", "-i", staged.name, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False,
        )
    if decoded.returncode != 0:
        raise VideoIngestionError("ffmpeg could not fully decode the downloaded video")
    return ObservedVideo(duration, width, height, codec, audio_codec, container)
