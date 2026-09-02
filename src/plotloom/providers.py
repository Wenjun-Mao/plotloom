from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from .domain import CamelModel


class TextGenerationRequest(CamelModel):
    system_prompt: str
    user_prompt: str
    response_schema: dict[str, Any]
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextGenerationResult(CamelModel):
    content: str
    parsed: dict[str, Any] | None = None
    provider_request_id: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)


class MediaGenerationRequest(CamelModel):
    prompt: str
    model: str | None = None
    source_uris: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class MediaGenerationResult(CamelModel):
    content: bytes | None = None
    remote_uri: str | None = None
    media_type: str
    provider_request_id: str | None = None


@runtime_checkable
class TextProvider(Protocol):
    def generate_text(self, request: TextGenerationRequest) -> TextGenerationResult: ...


@runtime_checkable
class ImageProvider(Protocol):
    def generate_image(self, request: MediaGenerationRequest) -> MediaGenerationResult: ...


@runtime_checkable
class VideoProvider(Protocol):
    def generate_video(self, request: MediaGenerationRequest) -> MediaGenerationResult: ...


class ProviderPorts(CamelModel):
    """Dependency container for provider adapters owned by the Plotloom runtime."""

    model_config = CamelModel.model_config | {"arbitrary_types_allowed": True}

    text: TextProvider | None = None
    image: ImageProvider | None = None
    video: VideoProvider | None = None
