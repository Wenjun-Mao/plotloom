"""Reviewed Qwen-Image canvas contract and frozen execution snapshots."""
from __future__ import annotations

import json
from dataclasses import dataclass


QWEN_IMAGE_CONTRACT_VERSION = 2


@dataclass(frozen=True)
class QwenImageCanvas:
    """One exact public Qwen output canvas."""

    resolution: str
    width: int
    height: int


QWEN_IMAGE_CANVASES = (
    QwenImageCanvas("1024x1024", 1024, 1024),
    QwenImageCanvas("832x480", 832, 480),
    QwenImageCanvas("960x544", 960, 544),
    QwenImageCanvas("1280x704", 1280, 704),
    QwenImageCanvas("576x1024", 576, 1024),
    QwenImageCanvas("608x1088", 608, 1088),
    QwenImageCanvas("704x1280", 704, 1280),
)
QWEN_IMAGE_CANVASES_BY_RESOLUTION = {
    canvas.resolution: canvas for canvas in QWEN_IMAGE_CANVASES
}


def admitted_qwen_image_canvas(resolution: str) -> QwenImageCanvas:
    """Return an explicitly reviewed canvas or reject arbitrary dimensions."""

    return QWEN_IMAGE_CANVASES_BY_RESOLUTION[resolution]


def qwen_image_canvas_from_snapshot(snapshot_json: str) -> QwenImageCanvas:
    """Read a Qwen job's immutable canvas without consulting live defaults.

    Version 1 snapshots are retained for jobs admitted under the original
    square-only contract. Version 2 snapshots are emitted for the reviewed
    multi-canvas contract. Both must independently agree with the catalog.
    """

    try:
        payload = json.loads(snapshot_json)
        version = payload["imageContractVersion"]
        resolution = payload["resolution"]
        width = payload["width"]
        height = payload["height"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("invalid Qwen image execution snapshot") from error
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version not in {1, QWEN_IMAGE_CONTRACT_VERSION}
        or not isinstance(resolution, str)
    ):
        raise ValueError("unsupported Qwen image execution snapshot")
    try:
        canvas = admitted_qwen_image_canvas(resolution)
    except KeyError as error:
        raise ValueError("unknown Qwen image snapshot canvas") from error
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or (width, height) != (canvas.width, canvas.height)
    ):
        raise ValueError("Qwen image snapshot dimensions do not match its canvas")
    if version == 1 and canvas.resolution != "1024x1024":
        raise ValueError("version 1 Qwen image snapshot must be square")
    return canvas
