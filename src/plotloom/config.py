from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .domain import DEFAULT_TEXT_BASE_URL, DEFAULT_TEXT_MODEL, DEFAULT_TEXT_PROVIDER
from .provider_profiles import DEFAULT_PROVIDER_PROFILE_ID, PROFILE_ID_PATTERN


def profile_text_api_key_environment_name(profile_id: str) -> str:
    """Return the one server credential variable reserved for a text profile."""

    import re

    if not re.fullmatch(PROFILE_ID_PATTERN, profile_id):
        raise ValueError("profile_id must match [a-z][a-z0-9_]{0,62}")
    return f"PLOTLOOM_PROFILE_{profile_id.upper()}_TEXT_API_KEY"


def resolve_text_provider_api_key(
    profile_id: str,
    environ: dict[str, str] | None = None,
) -> str | None:
    """Resolve a server-only text key without persisting its source or value.

    The named variable has priority for every profile.  ``default`` keeps the
    pre-M1.5 fallback order so upgrading a checkout does not silently lose its
    existing credential.
    """

    values = os.environ if environ is None else environ
    key = values.get(profile_text_api_key_environment_name(profile_id)) or None
    if key:
        return key
    if profile_id == DEFAULT_PROVIDER_PROFILE_ID:
        return values.get("TEXT_MODEL_API_KEY") or values.get("ATLASCLOUD_API_KEY") or None
    return None


def _source_checkout_root() -> Path | None:
    """Return the checkout root only when this package lives in its source layout."""

    package_root = Path(__file__).resolve().parent
    if package_root.parent.name != "src":
        return None
    candidate = package_root.parent.parent
    if (candidate / "pyproject.toml").is_file() or (candidate / ".git").exists():
        return candidate
    return None


def _user_data_root() -> Path:
    """Resolve a writable per-user home for an installed Plotloom application."""

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Plotloom"
    if os.name == "nt":
        windows_root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return Path(windows_root).expanduser() / "Plotloom" if windows_root else (
            home / "AppData" / "Local" / "Plotloom"
        )
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home).expanduser() if xdg_data_home else home / ".local" / "share"
    return base / "plotloom"


def resolve_repo_root(start: Path | None = None) -> Path:
    """Resolve an explicit checkout or the package's own trusted runtime home.

    An installed package must never infer its data root from the process working
    directory: callers can launch the console script from any unrelated project.
    """

    if start is None:
        return (_source_checkout_root() or _user_data_root()).resolve()

    candidate = start.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / "pyproject.toml").is_file() or (directory / ".git").exists():
            return directory
    return candidate


class PlotloomSettings(BaseModel):
    """Runtime-owned configuration; it deliberately has no legacy settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_root: Path
    data_dir: Path
    database_url: str
    artifact_root: Path
    static_dir: Path
    host: str = "127.0.0.1"
    port: int = Field(default=8775, ge=1, le=65535)
    port_fallback_count: int = Field(default=19, ge=0, le=100)
    run_workers: int = Field(default=1, ge=1, le=32)
    media_workers: int = Field(default=2, ge=1, le=32)
    media_poll_interval_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    media_max_poll_attempts: int = Field(default=300, ge=1, le=10_000)
    text_provider: str = DEFAULT_TEXT_PROVIDER
    text_base_url: str = DEFAULT_TEXT_BASE_URL
    text_model: str = DEFAULT_TEXT_MODEL
    text_auth_mode: Literal["none", "bearer"] = "bearer"
    text_supports_json_object: bool = False
    text_supports_json_schema: bool = False
    text_supports_chat_template_kwargs: bool = False
    text_context_window_tokens: int = Field(default=32_768, ge=1)
    text_max_output_tokens: int = Field(default=8_192, ge=1)
    text_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    text_max_concurrency: int = Field(default=1, ge=1, le=32)
    text_connect_timeout_seconds: float = Field(default=10.0, gt=0.0, le=300.0)
    text_attempt_timeout_seconds: float = Field(default=300.0, gt=0.0, le=3_600.0)
    text_request_extension: Literal["none", "chat_template_kwargs"] = "none"
    text_reasoning_mode: Literal["provider_default", "enabled", "disabled"] = (
        "provider_default"
    )
    text_extraction_allow_json_fence: bool = False
    text_extraction_allow_leading_think_block: bool = False
    text_story_bible_max_output_tokens: int = Field(default=8192, ge=1)
    text_story_graph_max_output_tokens: int = Field(default=8192, ge=1)
    text_scene_beats_max_output_tokens: int = Field(default=4096, ge=1)
    text_storyboard_max_output_tokens: int = Field(default=4096, ge=1)
    text_max_semantic_corrections: int = Field(default=2, ge=0, le=2)
    text_preset_id: Literal[
        "compatible_v1", "quality_reasoning_v1", "final_only_v1", "custom"
    ] = "compatible_v1"
    image_provider: str = "atlascloud"
    image_base_url: str = "https://api.atlascloud.ai/api/v1/model"
    image_model: str = "openai/gpt-image-2/text-to-image"
    image_auth_mode: Literal["none", "bearer"] = "bearer"
    video_provider: str = "atlascloud"
    video_base_url: str = "https://api.atlascloud.ai/api/v1/model"
    video_model: str = "xai/grok-imagine-video-v1.5/image-to-video"
    video_auth_mode: Literal["none", "bearer"] = "bearer"
    text_api_key: SecretStr | None = None
    image_api_key: SecretStr | None = None
    video_api_key: SecretStr | None = None

    def text_api_key_for_profile(self, profile_id: str) -> SecretStr | None:
        """Resolve an ephemeral key for a named profile at dispatch time."""

        value = resolve_text_provider_api_key(profile_id)
        return SecretStr(value) if value else None

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> PlotloomSettings:
        source_checkout = repo_root is not None or _source_checkout_root() is not None
        root = resolve_repo_root(repo_root)
        if source_checkout:
            # Only an explicit/source checkout root is trusted as a dotenv
            # source. Existing host variables win because loading is
            # deliberately non-overriding. Installed wheels never inspect cwd.
            load_dotenv(dotenv_path=root / ".env", override=False)

        default_data_dir = root / "data" if source_checkout else root
        data_dir = Path(
            os.environ.get("PLOTLOOM_DATA_DIR") or default_data_dir
        ).expanduser()
        if not data_dir.is_absolute():
            data_dir = (root / data_dir).resolve()
        else:
            data_dir = data_dir.resolve()
        database_url = os.environ.get("PLOTLOOM_DATABASE_URL") or (
            f"sqlite:///{data_dir / 'plotloom.sqlite3'}"
        )
        artifact_root = Path(
            os.environ.get("PLOTLOOM_ARTIFACT_ROOT") or data_dir / "artifacts"
        ).expanduser()
        if not artifact_root.is_absolute():
            artifact_root = (root / artifact_root).resolve()
        static_dir = Path(
            os.environ.get("PLOTLOOM_STATIC_DIR")
            or Path(__file__).resolve().parent / "static"
        ).expanduser()
        if not static_dir.is_absolute():
            static_dir = (root / static_dir).resolve()

        hosting_port = os.environ.get("PORT")
        configured_port = hosting_port or os.environ.get("PLOTLOOM_PORT", "8775")
        fallback_key = os.environ.get("ATLASCLOUD_API_KEY") or None
        return cls(
            repo_root=root,
            data_dir=data_dir,
            database_url=database_url,
            artifact_root=artifact_root.resolve(),
            static_dir=static_dir.resolve(),
            host=os.environ.get("PLOTLOOM_HOST", os.environ.get("HOST", "127.0.0.1")),
            port=configured_port,
            port_fallback_count=0 if hosting_port is not None else 19,
            run_workers=os.environ.get("PLOTLOOM_RUN_WORKERS", "1"),
            media_workers=os.environ.get("PLOTLOOM_MEDIA_WORKERS", "2"),
            media_poll_interval_seconds=os.environ.get(
                "PLOTLOOM_MEDIA_POLL_INTERVAL_SECONDS", "2"
            ),
            media_max_poll_attempts=os.environ.get(
                "PLOTLOOM_MEDIA_MAX_POLL_ATTEMPTS", "300"
            ),
            text_provider=os.environ.get("TEXT_PROVIDER") or DEFAULT_TEXT_PROVIDER,
            text_base_url=os.environ.get("TEXT_BASE_URL") or DEFAULT_TEXT_BASE_URL,
            text_model=os.environ.get("TEXT_MODEL") or DEFAULT_TEXT_MODEL,
            text_auth_mode=os.environ.get("TEXT_AUTH_MODE") or "bearer",
            text_supports_json_object=os.environ.get("TEXT_SUPPORTS_JSON_OBJECT", "false"),
            text_supports_json_schema=os.environ.get("TEXT_SUPPORTS_JSON_SCHEMA", "false"),
            text_supports_chat_template_kwargs=os.environ.get(
                "TEXT_SUPPORTS_CHAT_TEMPLATE_KWARGS", "false"
            ),
            text_context_window_tokens=os.environ.get("TEXT_CONTEXT_WINDOW_TOKENS", "32768"),
            text_max_output_tokens=os.environ.get("TEXT_MAX_OUTPUT_TOKENS", "8192"),
            text_temperature=os.environ.get("TEXT_TEMPERATURE", "0.2"),
            text_max_concurrency=os.environ.get("TEXT_MAX_CONCURRENCY", "1"),
            text_connect_timeout_seconds=os.environ.get("TEXT_CONNECT_TIMEOUT_SECONDS", "10"),
            text_attempt_timeout_seconds=os.environ.get("TEXT_ATTEMPT_TIMEOUT_SECONDS", "300"),
            text_request_extension=os.environ.get("TEXT_REQUEST_EXTENSION", "none"),
            text_reasoning_mode=os.environ.get("TEXT_REASONING_MODE", "provider_default"),
            text_extraction_allow_json_fence=os.environ.get(
                "TEXT_EXTRACTION_ALLOW_JSON_FENCE", "false"
            ),
            text_extraction_allow_leading_think_block=os.environ.get(
                "TEXT_EXTRACTION_ALLOW_LEADING_THINK_BLOCK", "false"
            ),
            text_story_bible_max_output_tokens=os.environ.get(
                "TEXT_STORY_BIBLE_MAX_OUTPUT_TOKENS", "8192"
            ),
            text_story_graph_max_output_tokens=os.environ.get(
                "TEXT_STORY_GRAPH_MAX_OUTPUT_TOKENS", "8192"
            ),
            text_scene_beats_max_output_tokens=os.environ.get(
                "TEXT_SCENE_BEATS_MAX_OUTPUT_TOKENS", "4096"
            ),
            text_storyboard_max_output_tokens=os.environ.get(
                "TEXT_STORYBOARD_MAX_OUTPUT_TOKENS", "4096"
            ),
            text_max_semantic_corrections=os.environ.get(
                "TEXT_MAX_SEMANTIC_CORRECTIONS", "2"
            ),
            text_preset_id=os.environ.get("TEXT_PRESET_ID", "compatible_v1"),
            image_provider=os.environ.get("IMAGE_PROVIDER") or "atlascloud",
            image_base_url=os.environ.get("IMAGE_BASE_URL")
            or "https://api.atlascloud.ai/api/v1/model",
            image_model=os.environ.get("IMAGE_MODEL")
            or "openai/gpt-image-2/text-to-image",
            image_auth_mode=os.environ.get("IMAGE_AUTH_MODE") or "bearer",
            video_provider=os.environ.get("VIDEO_PROVIDER") or "atlascloud",
            video_base_url=os.environ.get("VIDEO_BASE_URL")
            or "https://api.atlascloud.ai/api/v1/model",
            video_model=os.environ.get("VIDEO_MODEL")
            or "xai/grok-imagine-video-v1.5/image-to-video",
            video_auth_mode=os.environ.get("VIDEO_AUTH_MODE") or "bearer",
            text_api_key=resolve_text_provider_api_key(DEFAULT_PROVIDER_PROFILE_ID),
            image_api_key=os.environ.get("IMAGE_MODEL_API_KEY") or fallback_key,
            video_api_key=os.environ.get("VIDEO_MODEL_API_KEY") or fallback_key,
        )
