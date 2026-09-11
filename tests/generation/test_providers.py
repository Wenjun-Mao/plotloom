from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from plotloom.generation.contracts import (
    GenerationRequest,
    PromptMessage,
    ProviderCapabilities,
    ReasoningMode,
    RequestExtension,
)
from plotloom.generation.exceptions import (
    ProviderCapabilityError,
    ProviderError,
    ProviderOutcomeUnknownError,
    ProviderRequestNotSentError,
    ProviderResponseError,
)
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


def test_openai_compatible_readiness_uses_models_without_a_completion() -> None:
    session = _session()
    session.get.return_value = Mock(
        status_code=200,
        headers={},
        json=Mock(return_value={"data": [{"id": "test-model"}]}),
    )
    adapter = OpenAICompatibleAdapter(
        name="openai-compatible", base_url="https://api.example.test/v1", session=session
    )
    _, lease = secret_lease()

    result = adapter.check_readiness("test-model", lease)

    assert result.state == "available"
    assert result.reason_code == "readiness.models_verified"
    session.post.assert_not_called()
    assert session.get.call_args.args[0].endswith("/models")


def test_openai_compatible_readiness_classifies_missing_model() -> None:
    session = _session()
    session.get.return_value = Mock(
        status_code=200, headers={}, json=Mock(return_value={"data": [{"id": "other"}]})
    )
    adapter = OpenAICompatibleAdapter(
        name="openai-compatible", base_url="https://api.example.test/v1", session=session
    )
    _, lease = secret_lease()

    result = adapter.check_readiness("test-model", lease)

    assert (result.state, result.reason_code) == (
        "model_mismatch", "readiness.expected_model_absent"
    )


def test_openai_compatible_readiness_keeps_an_unsupported_model_list_unverified() -> None:
    session = _session()
    session.get.return_value = Mock(status_code=404, headers={}, json=Mock())
    adapter = OpenAICompatibleAdapter(
        name="openai-compatible", base_url="https://api.example.test/v1", session=session
    )
    _, lease = secret_lease()

    result = adapter.check_readiness("test-model", lease)

    assert (result.state, result.reason_code, result.checked) == (
        "unverified", "readiness.models_unsupported", False
    )
    session.post.assert_not_called()


def test_adapter_redacts_an_echoed_outbound_secret_but_keeps_usage_counters() -> None:
    session = _session()
    session.post.return_value.json.return_value.update(
        {
            "echo": "request used test-provider-secret",
            "authorization": "Bearer test-provider-secret",
        }
    )
    adapter = OpenAICompatibleAdapter(
        name="provider",
        base_url="https://api.example.test/v1",
        session=session,
    )
    _, lease = secret_lease()

    response = adapter.generate(_request(schema=None), lease)

    assert "test-provider-secret" not in repr(response.raw)
    assert response.raw["echo"] == "request used [redacted]"
    assert response.raw["authorization"] == "[redacted]"
    assert response.raw["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 4,
    }


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
    with pytest.raises(ProviderResponseError) as captured:
        adapter.generate(_request(schema=None), lease)
    assert captured.value.code == "provider.http_401"
    assert captured.value.status_code == 401
    assert "test-provider-secret" not in str(captured.value)
    assert "detailed remote failure" not in str(captured.value)


@pytest.mark.parametrize(
    ("json_value", "json_error", "expected_code"),
    [
        (None, ValueError("not json"), "provider.envelope_non_json"),
        ([], None, "provider.envelope_non_object"),
    ],
)
def test_received_invalid_envelope_is_known_and_secret_free(
    json_value: object,
    json_error: Exception | None,
    expected_code: str,
) -> None:
    session = _session()
    response = session.post.return_value
    response.text = "test-provider-secret: remote body"
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = json_value
    adapter = OpenAICompatibleAdapter(
        name="provider",
        base_url="https://api.example.test/v1",
        session=session,
    )
    _, lease = secret_lease()

    with pytest.raises(ProviderResponseError) as captured:
        adapter.generate(_request(schema=None), lease)

    assert captured.value.code == expected_code
    assert captured.value.status_code == 200
    assert "test-provider-secret" not in str(captured.value)
    assert "remote body" not in str(captured.value)


def test_connect_timeout_is_known_not_sent_but_read_timeout_is_unknown() -> None:
    _, lease = secret_lease()
    connect_session = Mock()
    connect_session.post.side_effect = requests.ConnectTimeout("connect")
    connect_adapter = OpenAICompatibleAdapter(
        name="provider",
        base_url="https://api.example.test/v1",
        session=connect_session,
    )
    with pytest.raises(ProviderRequestNotSentError):
        connect_adapter.generate(_request(schema=None), lease)

    _, second_lease = secret_lease()
    read_session = Mock()
    read_session.post.side_effect = requests.ReadTimeout("read")
    read_adapter = OpenAICompatibleAdapter(
        name="provider",
        base_url="https://api.example.test/v1",
        session=read_session,
    )
    with pytest.raises(ProviderOutcomeUnknownError):
        read_adapter.generate(_request(schema=None), second_lease)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://user:password@api.example.test/v1",
        "https://api.example.test/v1?key=secret",
        "https://api.example.test/v1#fragment",
        "ftp://api.example.test/v1",
        "https://api.example.test:bad/v1",
    ],
)
def test_adapter_rejects_untrusted_url_shapes(base_url: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter(name="provider", base_url=base_url)


def test_adapter_supports_no_auth_local_http_without_authorization_or_redirects() -> None:
    session = _session()
    adapter = OpenAICompatibleAdapter(
        name="local-llama",
        base_url="http://127.0.0.1:8080/v1",
        auth_mode="none",
        session=session,
    )

    adapter.generate(_request(schema=None), None)

    sent = session.post.call_args.kwargs
    assert "Authorization" not in sent["headers"]
    assert sent["allow_redirects"] is False
    assert sent["timeout"] == (10.0, 300.0)


def test_adapter_emits_only_declared_chat_template_kwargs() -> None:
    session = _session()
    adapter = OpenAICompatibleAdapter(
        name="template-capable",
        base_url="http://127.0.0.1:8080/v1",
        auth_mode="none",
        capabilities=ProviderCapabilities(chat_template_kwargs=True),
        session=session,
    )
    request = _request(schema=None).model_copy(
        update={
            "request_extension": RequestExtension.CHAT_TEMPLATE_KWARGS,
            "reasoning_mode": ReasoningMode.ENABLED,
        }
    )
    adapter.generate(request, None)
    assert session.post.call_args.kwargs["json"]["chat_template_kwargs"] == {
        "enable_thinking": True
    }


def test_adapter_rejects_undeclared_template_extension_before_http() -> None:
    session = _session()
    adapter = OpenAICompatibleAdapter(
        name="strict-provider",
        base_url="http://127.0.0.1:8080/v1",
        auth_mode="none",
        session=session,
    )
    request = _request(schema=None).model_copy(
        update={
            "request_extension": RequestExtension.CHAT_TEMPLATE_KWARGS,
            "reasoning_mode": ReasoningMode.DISABLED,
        }
    )
    with pytest.raises(ProviderCapabilityError, match="chat_template_kwargs"):
        adapter.generate(request, None)
    session.post.assert_not_called()


def test_adapter_records_only_final_content_when_reasoning_is_present() -> None:
    session = _session()
    session.post.return_value.json.return_value["choices"][0]["message"] = {
        "content": None,
        "reasoning": "private chain of thought",
    }
    adapter = OpenAICompatibleAdapter(
        name="reasoning-provider",
        base_url="http://127.0.0.1:8080/v1",
        auth_mode="none",
        session=session,
    )
    response = adapter.generate(_request(schema=None), None)
    assert response.final_content is None
    assert response.reasoning_present is True
    assert response.outcome_code == "response.missing_final_content"
    assert "private chain of thought" not in response.model_dump(exclude={"raw"})


def test_adapter_separates_reasoning_parts_from_typed_final_text_parts() -> None:
    session = _session()
    session.post.return_value.json.return_value["choices"][0]["message"] = {
        "content": [
            {"type": "reasoning", "text": "private chain of thought"},
            {"type": "unknown", "text": "untrusted text"},
            {"type": "text", "text": '{"ok":true}'},
        ]
    }
    adapter = OpenAICompatibleAdapter(
        name="reasoning-provider",
        base_url="http://127.0.0.1:8080/v1",
        auth_mode="none",
        session=session,
    )

    response = adapter.generate(_request(schema=None), None)

    assert response.final_content == '{"ok":true}'
    assert response.reasoning_present is True
    assert response.outcome_code is None
    assert "private chain of thought" not in response.final_content
