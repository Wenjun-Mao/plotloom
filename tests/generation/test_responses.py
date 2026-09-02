from __future__ import annotations

import pytest

from plotloom.generation.contracts import ExtractionPolicy, ProviderResponse
from plotloom.generation.exceptions import ResponseExtractionError
from plotloom.generation.responses import extract_assistant_text, parse_json_text


def test_strict_json_parser_does_not_silently_strip_wrappers() -> None:
    wrapped = "```json\n{\"ok\": true}\n```"
    with pytest.raises(ResponseExtractionError):
        parse_json_text(wrapped)

    extracted = parse_json_text(
        wrapped,
        policy=ExtractionPolicy(markdown_fence=True),
    )
    assert extracted.value == {"ok": True}
    assert extracted.transformations == ("removed_json_markdown_fence",)


def test_each_enabled_response_transformation_is_traced() -> None:
    response = "<think>private reasoning</think>preface {\"ok\": true} suffix"
    extracted = parse_json_text(
        response,
        policy=ExtractionPolicy(reasoning_tags=True, embedded_json=True),
    )
    assert extracted.value == {"ok": True}
    assert extracted.transformations == (
        "removed_leading_think_blocks",
        "extracted_embedded_json_document",
    )


def test_assistant_text_supports_string_and_text_part_envelopes() -> None:
    response = ProviderResponse(
        provider="fake",
        model="fake-model",
        raw={
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "{\"a\":"},
                            {"type": "text", "text": "1}"},
                        ]
                    }
                }
            ]
        },
    )
    assert extract_assistant_text(response) == '{"a":1}'

    with pytest.raises(ResponseExtractionError, match="no first choice"):
        extract_assistant_text({"choices": []})
