"""The source and candidate span coordinate systems are frozen explicitly."""

import pytest

from plotloom.content_language_contract import CHECK_INPUT, bind_language_result, language_result_schema
from tests.content_language_fixtures import checking_request, original_request, result_for
from tests.test_content_language_service import check_environment as _check_environment

check_environment = _check_environment


def nested_check():
    original = original_request("branches")
    original.source = {"outline": {"outline": {"adaptation": {"keep": [
        {"evidence": "她把安字留在杯上。"}]}}}}
    candidate = {"lang": "en", "nodes": [{"id": "start", "title": "A cup marked 安"}]}
    from plotloom.language_policy import freeze_request_language
    freeze_request_language(original, "en-US")
    request = checking_request(original, candidate)
    result = result_for(request)
    field = next(item for item in result["coverage"] if item["path"] == "$.nodes[0].title")
    field["exceptions"] = [{"kind": "literal_visible_text",
        "candidateSpan": {"path": field["path"], "start": 13, "end": 14, "text": "安"},
        "sourceSpan": {"path": "$.source.outline.outline.adaptation.keep[0].evidence",
                       "start": 2, "end": 3, "text": "安"}}]
    return request, result, field


def test_canonical_nested_unicode_source_span_binds_and_schema_separates_roots():
    request, result, _field = nested_check()
    assert bind_language_result(request, result).verdict == "pass"
    schema = language_result_schema(request.input_artifacts[CHECK_INPUT])
    fields = schema["$defs"]["LanguageException"]["properties"]
    source_paths = fields["sourceSpan"]["properties"]["path"]["enum"]
    candidate_paths = fields["candidateSpan"]["properties"]["path"]["enum"]
    assert source_paths == ["$.source.outline.outline.adaptation.keep[0].evidence"]
    assert candidate_paths == ["$.nodes[0].title"]
    assert "enum" not in schema["$defs"]["LanguageCoverage"]["properties"]["path"]
    assert "enum" not in schema["$defs"]["LanguageSpan"]["properties"]["path"]
    # A caller editing one coordinate definition cannot mutate the other.
    fields["sourceSpan"]["properties"]["path"]["enum"].append("$.wrong")
    assert candidate_paths == ["$.nodes[0].title"]


@pytest.mark.parametrize("field,path", [
    ("sourceSpan", "$.sources.source.outline.outline.adaptation.keep[0].evidence"),
    ("sourceSpan", "$.nodes[0].title"),
    ("candidateSpan", "$.candidate.nodes[0].title"),
    ("candidateSpan", "$.source.outline.outline.adaptation.keep[0].evidence"),
])
def test_wrapper_or_cross_coordinate_paths_still_fail_without_normalization(field, path):
    request, result, coverage = nested_check()
    coverage["exceptions"][0][field]["path"] = path
    with pytest.raises(ValueError, match="exact Unicode"):
        bind_language_result(request, result)


def test_empty_eligible_coordinates_use_false_schema_without_empty_enum():
    original = original_request()
    original.source = {"numericFact": 1}
    request = checking_request(original, {"lang": "zh", "emptyExtra": " "})
    schema = language_result_schema(request.input_artifacts[CHECK_INPUT])
    fields = schema["$defs"]["LanguageException"]["properties"]
    for field in ("sourceSpan", "candidateSpan"):
        path = fields[field]["properties"]["path"]
        assert "enum" not in path and path["not"] == {}
    assert bind_language_result(request, result_for(request)).verdict == "pass"



def test_actual_check_api_freezes_independent_coordinate_schema_in_package(check_environment, monkeypatch):
    from contextlib import contextmanager
    import json
    from pathlib import Path
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from plotloom.api.project_folder_content_language import register_content_language_routes
    from plotloom.codex_exec_contracts import CodexExecHostStatus
    from tests.test_content_language_service import _ready

    _storage, store, registry = check_environment
    original, _candidate = _ready(store, monkeypatch)
    registry.codex_exec_status = lambda _identifier: CodexExecHostStatus(state="not_found")
    registry.codex_exec_admit = lambda attempt: CodexExecHostStatus(state="spawn_intent", attempt=attempt)

    @contextmanager
    def opened(_project_id):
        yield store
    app = FastAPI()
    register_content_language_routes(app, opened, registry)
    route = f"/api/v2/projects/{original.project_id}/content-language/outline/{original.job_id}/check"
    response = TestClient(app).post(route)
    assert response.status_code == 200, response.text
    request, _data = store.repository.content_language.load(original.project_id, response.json()["checkJobId"])
    expected = language_result_schema(request.input_artifacts[CHECK_INPUT])
    assert request.input_artifacts["content-language-schema.json"] == expected
    paths = store.creative_handoff_exchange().root / "jobs" / request.job_id / "package" / "inputs"
    assert json.loads((Path(paths) / "content-language-schema.json").read_text()) == expected
    assert "$.source.text" in expected["$defs"]["LanguageException"]["properties"]["sourceSpan"]["properties"]["path"]["enum"]
