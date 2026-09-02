import json
from unittest.mock import Mock, patch

import pytest

from plotloom.domain import (
    ContinuityState,
    MediaKind,
    MediaPromptContext,
    ProjectBrief,
    Shot,
    StoryBible,
)
from plotloom.generation.secrets import InMemorySecretVault
from plotloom.media import (
    AtlasCloudVideoAdapter,
    DashScopeImageAdapter,
    MediaGateway,
    MediaPromptCompiler,
    MediaProviderError,
    OpenAIImageAdapter,
    SeedanceVideoAdapter,
)


def _lease():
    vault = InMemorySecretVault()
    vault.put("media", "never-persist-this")
    return vault, vault.lease("media", max_uses=1)


def test_atlas_video_contract_matches_normalized_task_lifecycle():
    adapter = AtlasCloudVideoAdapter()
    spec = adapter.submit_spec({
        "model": "custom/video",
        "prompt": "slow push in",
        "image_url": "https://cdn.example/start.jpg",
        "duration": 8,
        "resolution": "720p",
        "aspect_ratio": "16:9",
    })
    assert spec.path == "generateVideo"
    assert spec.json["image_url"].endswith("start.jpg")
    assert adapter.read_submission({"data": {"id": "task-1"}}).provider_task_id == "task-1"
    result = adapter.read_poll({"data": {"status": "completed", "outputs": ["https://cdn/x.mp4"]}})
    assert result.status == "succeeded"


def test_openai_image_returns_synchronous_outputs():
    adapter = OpenAIImageAdapter()
    spec = adapter.submit_spec({"prompt": "frame", "size": "1536x1024"})
    assert spec.path == "images/generations"
    result = adapter.read_submission({"data": [{"url": "https://cdn/x.png"}]})
    assert result.status == "succeeded"
    assert result.provider_task_id is None


def test_dashscope_and_seedance_keep_provider_specific_contracts():
    dash = DashScopeImageAdapter().submit_spec({"prompt": "frame", "size": "1024x1536"})
    assert dash.headers["X-DashScope-Async"] == "enable"
    assert dash.json["parameters"]["size"] == "720*1280"
    seedance = SeedanceVideoAdapter().submit_spec({
        "prompt": "motion",
        "image_url": "https://cdn/x.jpg",
        "duration": 4,
    })
    assert seedance.json["content"][1]["type"] == "image_url"


def test_gateway_never_places_key_in_payload():
    response = Mock(status_code=200)
    response.json.return_value = {"data": [{"url": "https://cdn/x.png"}]}
    session = Mock()
    session.request.return_value = response
    gateway = MediaGateway(session=session)
    vault, lease = _lease()
    with patch("plotloom.media.socket.getaddrinfo", return_value=[(None, None, None, None, ("8.8.8.8", 443))]):
        result = gateway.submit(
            adapter=OpenAIImageAdapter(),
            params={"prompt": "frame", "size": "1536x1024"},
            base_url="https://api.example/v1",
            secret=lease,
        )
    assert result.status == "succeeded"
    call = session.request.call_args
    assert "never-persist-this" not in repr(call.kwargs["json"])
    assert call.kwargs["headers"]["Authorization"] == "Bearer never-persist-this"
    vault.clear()


def test_media_prompt_compiler_uses_versioned_templates():
    compiler = MediaPromptCompiler()
    prompt, trace = compiler.image(
        story_bible={"logline": "test"},
        storyboard_shot={"id": "shot-1", "action": "turns"},
        continuity_context={"entry": "standing"},
        media_constraints={"aspectRatio": "16:9"},
    )
    assert "shot-1" in prompt
    assert trace.prompt_id == "media_image"
    assert len(trace.spec_hash) == 64


@pytest.mark.parametrize(
    ("kind", "expected_prompt_id", "continuity_key"),
    [
        (MediaKind.IMAGE, "media_image", "continuityContext"),
        (MediaKind.VIDEO, "media_video", "startFrameContext"),
    ],
)
def test_media_prompt_compiler_compiles_frozen_context_for_api(
    kind: MediaKind,
    expected_prompt_id: str,
    continuity_key: str,
):
    context = MediaPromptContext(
        brief=ProjectBrief(
            title="回声",
            synopsis="领航员醒来。",
            genre="科幻悬疑",
            visualStyle="低饱和冷色电影感",
            aspectRatio="16:9",
        ),
        storyBible=StoryBible(
            logline="领航员必须确认自己的身份。",
            premise="废弃空间站里，记忆可能是伪造的。",
            visualLanguage="冷色硬光，克制构图",
        ),
        shot=Shot(
            id="shot-1",
            sceneId="scene-1",
            order=1,
            title="苏醒",
            shotSize="close_up",
            durationSeconds=8,
            action="林默睁开眼，保持平躺。",
            entryState=ContinuityState(
                facts={"pose": "仰卧", "apiKey": "must-not-survive"},
                lighting="冷白应急灯",
            ),
            exitState=ContinuityState(
                facts={"eyes": "open"},
                lighting="冷白应急灯",
            ),
        ),
        storyboardRevision=3,
    )

    prompt, components = MediaPromptCompiler().compile(context, kind)

    assert "shot-1" in prompt
    assert "仰卧" in prompt
    assert "eyes" in prompt
    assert "低饱和冷色电影感" in prompt
    assert components["kind"] == kind.value
    assert components["storyboardRevision"] == 3
    assert components["mediaConstraints"]["aspectRatio"] == "16:9"
    assert components[continuity_key]["entryState"]["facts"]["apiKey"] == "[redacted]"
    assert components[continuity_key]["exitState"]["facts"]["eyes"] == "open"
    assert components["trace"]["promptId"] == expected_prompt_id
    assert components["trace"]["source"].endswith(f"{expected_prompt_id}.yaml")
    serialized = json.dumps(components, ensure_ascii=False)
    assert "must-not-survive" not in serialized
    assert "must-not-survive" not in prompt


def test_gateway_rejects_private_provider_endpoint():
    _, lease = _lease()
    with patch("plotloom.media.socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 443))]):
        with pytest.raises(MediaProviderError):
            MediaGateway(session=Mock()).submit(
                adapter=OpenAIImageAdapter(),
                params={"prompt": "frame", "size": "1536x1024"},
                base_url="https://localhost/v1",
                secret=lease,
            )
