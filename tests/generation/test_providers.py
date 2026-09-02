from __future__ import annotations

from unittest.mock import Mock

import pytest

from plotloom.generation.contracts import (
    GenerationRequest,
    PromptMessage,
    ProviderCapabilities,
)
from plotloom.generation.exceptions import ProviderCapabilityError, ProviderError
from plotloom.generation.providers import OpenAICompatibleAdapter

from conftest import secret_lease


def _request(*, schema: dict | None) -> GenerationRequest:
    return GenerationRequest(
        messages=(
            PromptMessage(role="system", content="Return JSON"),
            PromptMessage(role="user", content="Create it"),
        ),
        model="test-model",
        response_schema=schema,
        response_schema_name="story_bible_v2" if schema is not None else None,
    )


def _session() -> Mock:
    response = Mock(status_code=200, headers={"x-request-id": "request-1"})
    response.json.return_value = {
        "id": "completion-1",
        "model": "test-model",
        "choices": [
            {
                "message": {"content": '{"ok":true}'},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    }
    session = Mock()
    session.post.return_value = response
    return session


def test_openai_compatible_adapter_sends_native_schema_when_supported() -> None:
    session = _session()
    adapter = OpenAICompatibleAdapter(
        name="openai-compatible",
        base_url="https://api.example.test/v1",
        capabilities=ProviderCapabilities(json_schema=True),
        session=session,
    )
    _, lease = secret_lease()
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    response = adapter.generate(_request(schema=schema), lease)

    sent = session.post.call_args.kwargs
    assert sent["json"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "story_bible_v2",
            "strict": True,
            "schema": schema,
        },
    }
    assert "test-provider-secret" not in repr(sent["json"])
    assert sent["headers"]["Authorization"] == "Bearer test-provider-secret"
    assert response.usage.input_tokens == 10
    assert response.request_id == "completion-1"


def test_adapter_rejects_schema_if_caller_ignored_capabilities() -> None:
    session = _session()
    adapter = OpenAICompatibleAdapter(
        name="no-schema",
        base_url="https://api.example.test/v1",
        capabilities=ProviderCapabilities(json_schema=False),
        session=session,
    )
    _, lease = secret_lease()
    with pytest.raises(ProviderCapabilityError):
        adapter.generate(_request(schema={"type": "object"}), lease)
    session.post.assert_not_called()


def test_adapter_omits_response_format_when_request_has_no_schema() -> None:
    session = _session()
    adapter = OpenAICompatibleAdapter(
        name="no-schema",
        base_url="https://api.example.test/v1",
        capabilities=ProviderCapabilities(json_schema=False),
        session=session,
    )
    _, lease = secret_lease()
    adapter.generate(_request(schema=None), lease)
    assert "response_format" not in session.post.call_args.kwargs["json"]


def test_provider_errors_do_not_include_remote_body_or_secret() -> None:
    response = Mock(status_code=401)
    response.text = "test-provider-secret: detailed remote failure"
    session = Mock()
    session.post.return_value = response
    adapter = OpenAICompatibleAdapter(
        name="provider",
        base_url="https://api.example.test/v1",
        session=session,
    )
    _, lease = secret_lease()
    with pytest.raises(ProviderError) as captured:
        adapter.generate(_request(schema=None), lease)
    assert "test-provider-secret" not in str(captured.value)
    assert "detailed remote failure" not in str(captured.value)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://api.example.test/v1",
        "https://user:password@api.example.test/v1",
        "https://api.example.test/v1?key=secret",
    ],
)
def test_adapter_rejects_non_https_or_credential_bearing_roots(base_url: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter(name="provider", base_url=base_url)
