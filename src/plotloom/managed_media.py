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
from warnings import catch_warnings, simplefilter

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, field_validator, model_validator

from .artifacts import ArtifactStore
from .domain import CamelModel

SUPPORTED_MEDIA_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png"}


@dataclass(frozen=True)
class ManagedMediaLimits:
    """Bounded import limits supplied by the runtime, never by a browser."""

    max_import_bytes: int = 8 * 1024 * 1024
    max_import_pixels: int = 24_000_000

    def __post_init__(self) -> None:
        if not 1 <= self.max_import_bytes <= 64 * 1024 * 1024:
            raise ValueError("max_import_bytes must be between 1 byte and 64 MiB")
        if not 1 <= self.max_import_pixels <= 100_000_000:
            raise ValueError("max_import_pixels must be between 1 and 100,000,000")


DEFAULT_MANAGED_MEDIA_LIMITS = ManagedMediaLimits()


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
    source_refs: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("source_refs")
    @classmethod
    def normalize_source_refs(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("source_refs must not contain blank entries")
        if any(len(item) > 2_000 for item in normalized):
            raise ValueError("source_refs entries must be at most 2,000 characters")
        if len(set(normalized)) != len(normalized):
            raise ValueError("source_refs must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def require_reviewable_context(self) -> "VisualIntentInput":
        """Do not persist a role label as if it were a creator review intent."""

        has_authored_direction = any(
            value and value.strip()
            for value in (self.identity_intent, self.composition_intent, self.style_intent)
        )
        if not has_authored_direction:
            raise ValueError(
                "visual intent requires identity, composition, or style direction"
            )
        if not self.source_refs:
            raise ValueError("visual intent requires at least one source reference")
        return self


class ReviewedSelectionRequest(CamelModel):
    asset_id: str = Field(min_length=1, max_length=36)
    shot_id: str = Field(min_length=1, max_length=100)
    scene_id: str = Field(min_length=1, max_length=100)
    expected_selection_revision: int = Field(ge=0)
    storyboard_revision: int = Field(ge=1)
    approval_id: str = Field(min_length=1, max_length=36)
    compatibility_note: str = Field(min_length=1, max_length=2_000)
    visual_intent_id: str = Field(min_length=1, max_length=36)
    visual_intent_revision: int = Field(ge=1)


class PreviewRequest(CamelModel):
    scene_id: str = Field(min_length=1, max_length=100)
    # A pilot commonly exercises three shots, but the product contract lets a
    # creator freeze any nonempty contiguous subset of the current scene.
    shot_ids: list[str] = Field(min_length=1, max_length=100)
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


def inspect_import_image(
    content: bytes,
    limits: ManagedMediaLimits = DEFAULT_MANAGED_MEDIA_LIMITS,
) -> ObservedImage:
    """Fully decode a bounded JPEG/PNG and make a safe display derivative."""

    if not content:
        raise ManagedMediaError("empty_media", "image upload is empty")
    if len(content) > limits.max_import_bytes:
        raise ManagedMediaError("media_too_large", f"image exceeds {limits.max_import_bytes} byte limit")
    try:
        # Pillow's metadata parser is intentionally used before ``load`` so a
        # declared pixel bomb cannot make us decode a large raster just to
        # discover it exceeds Plotloom's stricter product limit.
        with catch_warnings():
            simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as inspected:
                image_format = inspected.format
                if image_format not in SUPPORTED_MEDIA_TYPES:
                    raise ManagedMediaError("unsupported_media", "only JPEG and PNG images are supported")
                width, height = inspected.size
                if width < 1 or height < 1 or width * height > limits.max_import_pixels:
                    raise ManagedMediaError("media_pixel_limit", f"image exceeds {limits.max_import_pixels} pixel limit")
                if getattr(inspected, "n_frames", 1) != 1:
                    raise ManagedMediaError("animated_media", "animated images are not supported")
                inspected.verify()
        with Image.open(BytesIO(content)) as decoded:
            decoded.load()
            display = ImageOps.exif_transpose(decoded).convert("RGB")
            display.thumbnail((2048, 2048))
            output = BytesIO()
            display.save(output, format="PNG", optimize=True)
            display_bytes = output.getvalue()
    except ManagedMediaError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ManagedMediaError("media_pixel_limit", f"image exceeds {limits.max_import_pixels} pixel limit") from error
    # ``verify`` can surface malformed chunk checksums as SyntaxError rather
    # than OSError (notably for PNG IDAT data).  It is still untrusted input,
    # so normalize it into the same public 422 contract.
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
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
