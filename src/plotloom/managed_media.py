"""Non-generative managed still-media contracts.

Imports deliberately do not use ``Artifact`` or ``GenerationRun`` rows: those
records are evidence for model work.  This module owns the small, separate
contract for creator-supplied bytes and their observed properties.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Literal

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, field_validator

from .artifacts import ArtifactStore
from .domain import CamelModel

MAX_IMPORT_BYTES = 8 * 1024 * 1024
MAX_IMPORT_PIXELS = 24_000_000
SUPPORTED_MEDIA_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png"}


class ManagedMediaError(ValueError):
    """A stable import/observation failure that does not create usable state."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ImportDeclaration(CamelModel):
    origin: str = Field(min_length=1, max_length=2_000)
    rights: Literal["known", "unknown"] = "unknown"
    rights_note: str | None = Field(default=None, max_length=2_000)
    declared_additions: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("origin")
    @classmethod
    def normalize_origin(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("origin must not be blank")
        return value


class VisualIntentInput(CamelModel):
    role: Literal["protagonist_reference", "location_reference", "shot_keyframe"]
    identity_intent: str | None = Field(default=None, max_length=2_000)
    composition_intent: str | None = Field(default=None, max_length=2_000)
    style_intent: str | None = Field(default=None, max_length=2_000)


class ReviewedSelectionRequest(CamelModel):
    asset_id: str = Field(min_length=1, max_length=36)
    shot_id: str = Field(min_length=1, max_length=100)
    scene_id: str = Field(min_length=1, max_length=100)
    expected_selection_revision: int = Field(ge=0)
    storyboard_revision: int = Field(ge=1)
    approval_id: str = Field(min_length=1, max_length=36)
    compatibility_note: str = Field(min_length=1, max_length=2_000)


class PreviewRequest(CamelModel):
    scene_id: str = Field(min_length=1, max_length=100)
    # P0 is deliberately a three-shot planning instrument, not a general
    # timeline API. Keep this invariant at the public boundary as well as in
    # the workbench so an alternate caller cannot create a weaker preview.
    shot_ids: list[str] = Field(min_length=3, max_length=3)
    expected_selection_revision: int = Field(ge=1)
    storyboard_revision: int = Field(ge=1)
    approval_id: str = Field(min_length=1, max_length=36)

    @field_validator("shot_ids")
    @classmethod
    def contiguous_input_is_not_duplicated(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("shotIds must not contain duplicates")
        return value


@dataclass(frozen=True)
class ObservedImage:
    mime_type: str
    width: int
    height: int
    byte_size: int
    content_hash: str
    display_bytes: bytes
    display_hash: str


def inspect_import_image(content: bytes) -> ObservedImage:
    """Fully decode a bounded JPEG/PNG and make a safe display derivative."""

    if not content:
        raise ManagedMediaError("empty_media", "image upload is empty")
    if len(content) > MAX_IMPORT_BYTES:
        raise ManagedMediaError("media_too_large", f"image exceeds {MAX_IMPORT_BYTES} byte limit")
    try:
        with Image.open(BytesIO(content)) as inspected:
            image_format = inspected.format
            if image_format not in SUPPORTED_MEDIA_TYPES:
                raise ManagedMediaError("unsupported_media", "only JPEG and PNG images are supported")
            if getattr(inspected, "n_frames", 1) != 1:
                raise ManagedMediaError("animated_media", "animated images are not supported")
            inspected.verify()
        with Image.open(BytesIO(content)) as decoded:
            decoded.load()
            width, height = decoded.size
            if width < 1 or height < 1 or width * height > MAX_IMPORT_PIXELS:
                raise ManagedMediaError("media_pixel_limit", f"image exceeds {MAX_IMPORT_PIXELS} pixel limit")
            display = ImageOps.exif_transpose(decoded).convert("RGB")
            display.thumbnail((2048, 2048))
            output = BytesIO()
            display.save(output, format="PNG", optimize=True)
            display_bytes = output.getvalue()
    except ManagedMediaError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ManagedMediaError("invalid_media", "image bytes could not be decoded") from error
    return ObservedImage(
        mime_type=SUPPORTED_MEDIA_TYPES[image_format],
        width=width,
        height=height,
        byte_size=len(content),
        content_hash=sha256(content).hexdigest(),
        display_bytes=display_bytes,
        display_hash=sha256(display_bytes).hexdigest(),
    )


def publish_import(store: ArtifactStore, content: bytes, observed: ObservedImage) -> tuple[str, str]:
    """Publish originals and derivative separately, then re-observe both hashes."""

    original_uri = store.put(content, expected_hash=observed.content_hash)
    # A deduplicated existing blob must be verified before imported metadata can
    # become visible.  Never repair corrupt shared content in this path.
    if sha256(store.get(original_uri)).hexdigest() != observed.content_hash:
        raise ManagedMediaError("corrupt_existing_blob", "stored original does not match its content hash")
    display_uri = store.put(observed.display_bytes, expected_hash=observed.display_hash)
    if sha256(store.get(display_uri)).hexdigest() != observed.display_hash:
        raise ManagedMediaError("corrupt_existing_blob", "stored derivative does not match its content hash")
    return original_uri, display_uri
