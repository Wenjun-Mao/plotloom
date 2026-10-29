"""Explicit multilingual timing cannot escape supported language authority."""
from copy import deepcopy

import pytest

from plotloom.content_language_contract import bind_language_result
from plotloom.production_dialogue_timing import (
    freeze_f5_dialogue_timing,
    projected_dialogue_timing,
)
from tests.content_language_fixtures import (
    checking_request,
    original_request,
    result_for,
)


@pytest.mark.parametrize("language", [None, "", " ", "zh", "en", "xyz", "fr-FR", False, 1, {}])
def test_explicit_unsupported_override_is_rejected_before_timing_or_receiving(language):
    value = {"speaker": "VO", "line": "Open the door.", "language": language}
    with pytest.raises(ValueError, match="语言不受支持"):
        projected_dialogue_timing(value, "zh-CN")
    script = {"episodes": [{"ep": 1, "scenes": [{"flow": [value]}]}]}
    with pytest.raises(ValueError, match="语言不受支持"):
        freeze_f5_dialogue_timing(script, script_content_hash="a"*64, language="zh-CN")


def test_source_directed_multilingual_line_has_explicit_semantic_and_frozen_timing_binding():
    original = original_request("script")
    original.source["adaptationIntent"] = "Mara speaks English at the door."
    line = {"speaker": "VO", "line": "Open the door.", "language": "en-US"}
    candidate = {"lang": "zh", "episodes": [{"ep": 1, "scenes": [{"flow": [line]}]}]}
    request = checking_request(original, candidate)
    result = result_for(request)
    with pytest.raises(ValueError, match="foreign dialogue"):
        bind_language_result(request, result)
    field = next(item for item in result["coverage"] if item["path"].endswith(".line"))
    field["exceptions"] = [{"kind": "intentional_foreign_speech", "language": "en-US",
        "candidateSpan": {"path": field["path"], "start": 0, "end": len(line["line"]), "text": line["line"]},
        "sourceSpan": {"path": "$.source.adaptationIntent", "start": 0,
            "end": len(original.source["adaptationIntent"]), "text": original.source["adaptationIntent"]}}]
    assert bind_language_result(request, result).verdict == "pass"
    timing = projected_dialogue_timing(line, "zh-CN")
    assert timing["language"] == "en-US"
    assert timing["estimatedDurationUnits"] == projected_dialogue_timing({"line": line["line"]}, "en-US")["estimatedDurationUnits"]
    frozen = freeze_f5_dialogue_timing(candidate, script_content_hash="b"*64, language="zh-CN")
    assert frozen.lines[0].minimum_duration_units == timing["estimatedDurationUnits"]
    bad = deepcopy(result)
    bad["coverage"] = [item | {"exceptions": []} if item["path"] == field["path"] else item for item in bad["coverage"]]
    with pytest.raises(ValueError, match="foreign dialogue"):
        bind_language_result(request, bad)
