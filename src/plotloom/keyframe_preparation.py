"""Pure, reviewable still-image preparation for frozen video profiles.

Video backends never get to decide how a mismatched keyframe is composed.  A
creator may choose this deterministic crop as a separate managed asset, review
it, and only then select it for a later video request.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps


def has_matching_aspect(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> bool:
    """Compare aspect ratios exactly without float rounding policy."""

    return source_width * target_height == source_height * target_width


def center_crop_png(source: bytes, *, target_width: int, target_height: int) -> bytes:
    """Create one explicit centered cover-crop PNG from supported source bytes.

    The caller observes and persists the result as a new managed asset.  This
    function intentionally does not write files, select a keyframe, or hide
    source provenance behind a video submission.
    """

    with Image.open(BytesIO(source)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        cropped = ImageOps.fit(
            image,
            (target_width, target_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        output = BytesIO()
        cropped.save(output, format="PNG", optimize=True)
        return output.getvalue()
