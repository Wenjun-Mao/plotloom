"""Plotloom-owned image/video prompt compilation and provider adapters.

The module intentionally duplicates no runtime dependency on the legacy
application. It is part of the extraction boundary described in
the repository extraction contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable
from urllib.parse import urlparse

import requests

from plotloom.domain import MediaKind as DomainMediaKind
from plotloom.domain import MediaPromptContext
from plotloom.generation.prompts import PromptRenderer
from plotloom.generation.secrets import SecretLease


MediaKind = Literal["image", "video"]
NormalizedStatus = Literal["processing", "succeeded", "failed"]


class MediaProviderError(RuntimeError):
    def __init__(self, message: str, *, status: int = 502, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


@dataclass(frozen=True)
class MediaRequestSpec:
    method: Literal["GET", "POST"]
    path: str
    json: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MediaSubmission:
    provider: str
    provider_task_id: str | None
    status: NormalizedStatus
    outputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class MediaPollResult:
    status: NormalizedStatus
    outputs: tuple[str, ...] = ()
    error: str | None = None


@runtime_checkable
class MediaProviderAdapter(Protocol):
    name: str
    kind: MediaKind
    synchronous: bool
    default_base_url: str
    default_model: str

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        ...

    def read_submission(self, payload: dict[str, Any]) -> MediaSubmission:
        ...

    def poll_spec(self, provider_task_id: str) -> MediaRequestSpec:
        ...

    def read_poll(self, payload: dict[str, Any]) -> MediaPollResult:
        ...


def normalize_status(value: object) -> NormalizedStatus:
    text = str(value or "").strip().lower()
    if text in {"succeeded", "success", "completed", "complete", "done", "finished"}:
        return "succeeded"
    if text in {"failed", "error", "cancelled", "canceled", "expired"}:
        return "failed"
    return "processing"


def _first_https_url(value: object) -> str | None:
    if isinstance(value, str) and value.startswith("https://"):
        return value
    if isinstance(value, dict):
        for child in value.values():
            found = _first_https_url(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _first_https_url(child)
            if found:
                return found
    return None


def _aspect(size: str) -> Literal["landscape", "portrait", "square"]:
    if size in {"1024x1536", "720x1280"}:
        return "portrait"
    if size in {"1536x1024", "1280x720"}:
        return "landscape"
    return "square"


def validate_trusted_provider_base_url(value: str) -> str:
    """Validate a root that reached this adapter through the saved profile.

    The caller-facing API never accepts endpoint overrides, so private/LAN and
    Tailnet roots are safe to support here without creating a browser-driven
    request primitive.  Redirects remain disabled at the actual HTTP boundary.
    """

    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise MediaProviderError(
            "Provider base URL must be an HTTP(S) root without credentials, query, or fragment",
            status=400,
        )
    try:
        parsed.port
    except ValueError as error:
        raise MediaProviderError("Provider base URL must use a valid port", status=400) from error
    return normalized


class AtlasCloudImageAdapter:
    name = "atlascloud"
    kind: MediaKind = "image"
    synchronous = False
    default_base_url = "https://api.atlascloud.ai/api/v1/model"
    default_model = "openai/gpt-image-2/text-to-image"
    default_edit_model = "openai/gpt-image-2/edit"

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        payload: dict[str, Any] = {
            "model": params.get("model") or self.default_model,
            "enable_base64_output": False,
            "enable_sync_mode": False,
            "output_format": params.get("output_format", "jpeg"),
            "prompt": _required_prompt(params),
            "quality": params.get("quality", "high"),
            "size": params.get("size", "1536x1024"),
            "moderation": params.get("moderation", "low"),
        }
        references = tuple(params.get("reference_images") or ())
        if references:
            payload["model"] = params.get("edit_model") or self.default_edit_model
            payload["images"] = list(references[:4])
        return MediaRequestSpec(method="POST", path="generateImage", json=payload)

    def read_submission(self, payload: dict[str, Any]) -> MediaSubmission:
        task_id = _nested(payload, "data", "id")
        if not task_id:
            raise MediaProviderError("AtlasCloud did not return a media task ID")
        return MediaSubmission(self.name, str(task_id), "processing")

    def poll_spec(self, provider_task_id: str) -> MediaRequestSpec:
        return MediaRequestSpec(method="GET", path=f"prediction/{provider_task_id}")

    def read_poll(self, payload: dict[str, Any]) -> MediaPollResult:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        outputs = tuple(item for item in data.get("outputs", []) if isinstance(item, str))
        return MediaPollResult(
            normalize_status(data.get("status")),
            outputs,
            str(data["error"]) if data.get("error") else None,
        )


class AtlasCloudVideoAdapter(AtlasCloudImageAdapter):
    kind: MediaKind = "video"
    default_model = "xai/grok-imagine-video-v1.5/image-to-video"

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        image_url = str(params.get("image_url") or "").strip()
        if not image_url:
            raise MediaProviderError("Video generation requires an image URL", status=400)
        payload = {
            "model": params.get("model") or self.default_model,
            "prompt": _required_prompt(params),
            "image_url": image_url,
            "duration": _duration(params),
            "resolution": params.get("resolution", "720p"),
            "aspect_ratio": params.get("aspect_ratio", "16:9"),
        }
        return MediaRequestSpec(method="POST", path="generateVideo", json=payload)


class OpenAIImageAdapter:
    name = "openai"
    kind: MediaKind = "image"
    synchronous = True
    default_base_url = "https://api.openai.com/v1"
    default_model = "dall-e-3"
    _sizes = {"landscape": "1792x1024", "portrait": "1024x1792", "square": "1024x1024"}

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        return MediaRequestSpec(
            method="POST",
            path="images/generations",
            json={
                "model": params.get("model") or self.default_model,
                "prompt": _required_prompt(params),
                "n": 1,
                "size": self._sizes[_aspect(str(params.get("size", "1536x1024")))],
                "response_format": "url",
            },
        )

    def read_submission(self, payload: dict[str, Any]) -> MediaSubmission:
        items = payload.get("data") if isinstance(payload.get("data"), list) else []
        outputs = tuple(
            item["url"]
            for item in items
            if isinstance(item, dict) and isinstance(item.get("url"), str)
        )
        if not outputs:
            if any(isinstance(item, dict) and item.get("b64_json") for item in items):
                raise MediaProviderError("This provider returned base64-only images; URL output is required")
            raise MediaProviderError("Image provider returned no output URL")
        return MediaSubmission(self.name, None, "succeeded", outputs)

    def poll_spec(self, provider_task_id: str) -> MediaRequestSpec:
        raise MediaProviderError("Synchronous image results are not polled", status=400)

    def read_poll(self, payload: dict[str, Any]) -> MediaPollResult:
        raise MediaProviderError("Synchronous image results are not polled", status=400)


class DashScopeImageAdapter:
    name = "dashscope"
    kind: MediaKind = "image"
    synchronous = False
    default_base_url = "https://dashscope.aliyuncs.com"
    default_model = "wan2.2-t2i-flash"
    _sizes = {"landscape": "1280*720", "portrait": "720*1280", "square": "1024*1024"}

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        return MediaRequestSpec(
            method="POST",
            path="api/v1/services/aigc/text2image/image-synthesis",
            json={
                "model": params.get("model") or self.default_model,
                "input": {"prompt": _required_prompt(params)},
                "parameters": {
                    "size": self._sizes[_aspect(str(params.get("size", "1536x1024")))],
                    "n": 1,
                },
            },
            headers={"X-DashScope-Async": "enable"},
        )

    def read_submission(self, payload: dict[str, Any]) -> MediaSubmission:
        task_id = _nested(payload, "output", "task_id")
        if not task_id:
            raise MediaProviderError("DashScope did not return a task_id")
        return MediaSubmission(self.name, str(task_id), "processing")

    def poll_spec(self, provider_task_id: str) -> MediaRequestSpec:
        return MediaRequestSpec(method="GET", path=f"api/v1/tasks/{provider_task_id}")

    def read_poll(self, payload: dict[str, Any]) -> MediaPollResult:
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        urls = tuple(
            item["url"]
            for item in output.get("results", [])
            if isinstance(item, dict) and isinstance(item.get("url"), str)
        )
        if not urls:
            found = _first_https_url(output)
            urls = (found,) if found else ()
        error = output.get("message") or payload.get("message")
        return MediaPollResult(normalize_status(output.get("task_status")), urls, str(error) if error else None)


class DashScopeVideoAdapter(DashScopeImageAdapter):
    kind: MediaKind = "video"
    default_model = "wan2.2-i2v-flash"

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        image_url = str(params.get("image_url") or "").strip()
        if not image_url:
            raise MediaProviderError("Video generation requires an image URL", status=400)
        return MediaRequestSpec(
            method="POST",
            path="api/v1/services/aigc/video-generation/video-synthesis",
            json={
                "model": params.get("model") or self.default_model,
                "input": {"prompt": _required_prompt(params), "img_url": image_url},
                "parameters": {"resolution": str(params.get("resolution", "720p")).upper()},
            },
            headers={"X-DashScope-Async": "enable"},
        )

    def read_poll(self, payload: dict[str, Any]) -> MediaPollResult:
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        url = output.get("video_url") or _first_https_url(output)
        error = output.get("message") or payload.get("message")
        return MediaPollResult(
            normalize_status(output.get("task_status")),
            (str(url),) if url else (),
            str(error) if error else None,
        )


class SeedanceVideoAdapter:
    name = "seedance"
    kind: MediaKind = "video"
    synchronous = False
    default_base_url = "https://ark.cn-beijing.volces.com/api/v3"
    default_model = "doubao-seedance-1-0-pro-250528"

    def submit_spec(self, params: dict[str, Any]) -> MediaRequestSpec:
        content: list[dict[str, Any]] = [{"type": "text", "text": _required_prompt(params)}]
        image_url = str(params.get("image_url") or "").strip()
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        return MediaRequestSpec(
            method="POST",
            path="contents/generations/tasks",
            json={
                "model": params.get("model") or self.default_model,
                "content": content,
                "duration": max(4, _duration(params)),
                "ratio": params.get("aspect_ratio", "16:9"),
                "resolution": params.get("resolution", "720p"),
            },
        )

    def read_submission(self, payload: dict[str, Any]) -> MediaSubmission:
        task_id = payload.get("id")
        if not task_id:
            raise MediaProviderError("Seedance did not return a task id")
        return MediaSubmission(self.name, str(task_id), "processing")

    def poll_spec(self, provider_task_id: str) -> MediaRequestSpec:
        return MediaRequestSpec(method="GET", path=f"contents/generations/tasks/{provider_task_id}")

    def read_poll(self, payload: dict[str, Any]) -> MediaPollResult:
        content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
        url = content.get("video_url") or _first_https_url(payload)
        error = payload.get("error")
        return MediaPollResult(
            normalize_status(payload.get("status")),
            (str(url),) if url else (),
            str(error) if error else None,
        )


IMAGE_ADAPTERS: dict[str, MediaProviderAdapter] = {
    adapter.name: adapter
    for adapter in (AtlasCloudImageAdapter(), OpenAIImageAdapter(), DashScopeImageAdapter())
}
VIDEO_ADAPTERS: dict[str, MediaProviderAdapter] = {
    adapter.name: adapter
    for adapter in (AtlasCloudVideoAdapter(), SeedanceVideoAdapter(), DashScopeVideoAdapter())
}


def get_media_adapter(kind: MediaKind, name: str | None) -> MediaProviderAdapter:
    table = IMAGE_ADAPTERS if kind == "image" else VIDEO_ADAPTERS
    adapter = table.get((name or "atlascloud").strip().lower())
    if adapter is None:
        raise MediaProviderError(f"Unknown {kind} provider: {name}", status=400)
    return adapter


class MediaGateway:
    """Execute exactly one provider request; retries remain visible to jobs."""

    def __init__(self, *, session: requests.Session | Any | None = None, timeout_seconds: float = 180):
        self._session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    def submit(
        self,
        *,
        adapter: MediaProviderAdapter,
        params: dict[str, Any],
        base_url: str,
        secret: SecretLease | None,
        auth_mode: Literal["none", "bearer"] = "bearer",
    ) -> MediaSubmission:
        payload = self._request(adapter.submit_spec(params), base_url, secret, auth_mode)
        return adapter.read_submission(payload)

    def poll(
        self,
        *,
        adapter: MediaProviderAdapter,
        provider_task_id: str,
        base_url: str,
        secret: SecretLease | None,
        auth_mode: Literal["none", "bearer"] = "bearer",
    ) -> MediaPollResult:
        payload = self._request(adapter.poll_spec(provider_task_id), base_url, secret, auth_mode)
        return adapter.read_poll(payload)

    def _request(
        self,
        spec: MediaRequestSpec,
        base_url: str,
        secret: SecretLease | None,
        auth_mode: Literal["none", "bearer"],
    ) -> dict[str, Any]:
        root = validate_trusted_provider_base_url(base_url)
        url = f"{root}/{spec.path.lstrip('/')}"
        if auth_mode not in {"none", "bearer"}:
            raise MediaProviderError("Media provider auth mode must be none or bearer", status=400)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **spec.headers,
        }
        if auth_mode == "bearer":
            if secret is None:
                raise MediaProviderError("Media provider requires a bearer credential", status=400)
            with secret.reveal() as api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                response = self._send(spec, url, headers)
        else:
            response = self._send(spec, url, headers)
        status = int(getattr(response, "status_code", 0) or 0)
        if not 200 <= status < 300:
            raise MediaProviderError(
                f"Media provider returned HTTP {status}",
                status=502,
                retryable=status == 429 or status >= 500,
            )
        try:
            payload = response.json()
        except (ValueError, requests.JSONDecodeError) as exc:
            raise MediaProviderError("Media provider returned a non-JSON response") from exc
        if not isinstance(payload, dict):
            raise MediaProviderError("Media provider returned a non-object response")
        return payload

    def _send(
        self,
        spec: MediaRequestSpec,
        url: str,
        headers: dict[str, str],
    ) -> Any:
        try:
            return self._session.request(
                spec.method,
                url,
                json=spec.json if spec.method == "POST" else None,
                headers=headers,
                timeout=self.timeout_seconds,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise MediaProviderError(
                f"Media provider request failed: {type(exc).__name__}", retryable=True
            ) from exc


class MediaPromptCompiler:
    """Compile canonical story/shot data into a versioned derived prompt."""

    def __init__(self, renderer: PromptRenderer | None = None):
        self.renderer = renderer or PromptRenderer()

    def image(
        self,
        *,
        story_bible: object,
        storyboard_shot: object,
        continuity_context: object,
        media_constraints: object,
    ) -> tuple[str, object]:
        rendered = self.renderer.render(
            "media_image",
            {
                "story_bible": story_bible,
                "storyboard_shot": storyboard_shot,
                "continuity_context": continuity_context,
                "media_constraints": media_constraints,
            },
        )
        return _flatten_prompt(rendered), rendered.trace

    def video(
        self,
        *,
        story_bible: object,
        storyboard_shot: object,
        start_frame_context: object,
        media_constraints: object,
    ) -> tuple[str, object]:
        rendered = self.renderer.render(
            "media_video",
            {
                "story_bible": story_bible,
                "storyboard_shot": storyboard_shot,
                "start_frame_context": start_frame_context,
                "media_constraints": media_constraints,
            },
        )
        return _flatten_prompt(rendered), rendered.trace

    def compile(
        self,
        context: MediaPromptContext,
        kind: DomainMediaKind,
    ) -> tuple[str, dict[str, Any]]:
        """Compile a frozen canonical media context for the API application layer.

        The API persists ``prompt_components`` as an audit record, so this method
        deliberately returns only JSON-shaped canonical inputs and public prompt
        trace metadata. Provider credentials never enter this boundary. Nested
        extension dictionaries are defensively redacted before either rendering
        or persistence.
        """

        normalized_kind = _domain_media_kind(kind)
        story_bible = _public_json(context.story_bible)
        storyboard_shot = _public_json(context.shot)
        continuity = {
            "entryState": _public_json(context.shot.entry_state),
            "exitState": _public_json(context.shot.exit_state),
        }
        media_constraints = _public_json(
            {
                "projectTitle": context.brief.title,
                "genre": context.brief.genre,
                "visualStyle": context.brief.visual_style,
                "language": context.brief.language,
                "aspectRatio": context.brief.aspect_ratio,
                "durationSeconds": context.shot.duration_seconds,
                "storyboardRevision": context.storyboard_revision,
            }
        )

        if normalized_kind == DomainMediaKind.IMAGE:
            prompt, trace = self.image(
                story_bible=story_bible,
                storyboard_shot=storyboard_shot,
                continuity_context=continuity,
                media_constraints=media_constraints,
            )
            continuity_name = "continuityContext"
        else:
            prompt, trace = self.video(
                story_bible=story_bible,
                storyboard_shot=storyboard_shot,
                start_frame_context=continuity,
                media_constraints=media_constraints,
            )
            continuity_name = "startFrameContext"

        prompt_components = {
            "kind": normalized_kind.value,
            "storyboardRevision": context.storyboard_revision,
            "storyBible": story_bible,
            "storyboardShot": storyboard_shot,
            continuity_name: continuity,
            "mediaConstraints": media_constraints,
            "trace": {
                "promptId": trace.prompt_id,
                "promptVersion": trace.prompt_version,
                "stage": trace.stage,
                "specHash": trace.spec_hash,
                "inputHash": trace.input_hash,
                "renderedHash": trace.rendered_hash,
                "source": trace.source,
                "renderedAt": trace.rendered_at.isoformat(),
                "variableNames": list(trace.variable_names),
            },
        }
        # Exercise the same JSON contract used by persistence now, close to the
        # source of the derived data, rather than failing later in a job worker.
        json.dumps(prompt_components, ensure_ascii=False, sort_keys=True)
        return prompt, prompt_components


def _flatten_prompt(rendered: object) -> str:
    messages = getattr(rendered, "messages")
    return "\n\n".join(message.content for message in messages).strip()


def _domain_media_kind(value: DomainMediaKind | str) -> DomainMediaKind:
    try:
        return value if isinstance(value, DomainMediaKind) else DomainMediaKind(value)
    except ValueError as exc:
        raise MediaProviderError(f"Unknown media kind: {value}", status=400) from exc


_SECRET_FIELD_NAMES = frozenset(
    {
        "apikey",
        "accesstoken",
        "refreshtoken",
        "token",
        "secret",
        "password",
        "authorization",
        "credential",
        "credentials",
    }
)


def _public_json(value: object) -> Any:
    """Return deterministic JSON data with structurally secret fields redacted."""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if _is_secret_field(str(key)) else _public_json(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_public_json(child) for child in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Refuse to silently stringify opaque runtime objects into a durable trace.
    raise TypeError(f"Media prompt component is not JSON-compatible: {type(value).__name__}")


def _is_secret_field(name: str) -> bool:
    normalized = "".join(character for character in name.lower() if character.isalnum())
    return normalized in _SECRET_FIELD_NAMES or normalized.endswith("apikey")


def _required_prompt(params: dict[str, Any]) -> str:
    value = str(params.get("prompt") or "").strip()
    if not value:
        raise MediaProviderError("Media prompt must not be blank", status=400)
    return value


def _duration(params: dict[str, Any]) -> int:
    try:
        value = int(params.get("duration", 8))
    except (TypeError, ValueError) as exc:
        raise MediaProviderError("Duration must be an integer", status=400) from exc
    if not 1 <= value <= 15:
        raise MediaProviderError("Duration must be between 1 and 15 seconds", status=400)
    return value


def _nested(payload: dict[str, Any], *keys: str) -> object | None:
    value: object = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value
