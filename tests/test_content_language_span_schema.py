"""The source and candidate span coordinate systems are frozen explicitly."""

from copy import deepcopy

import pytest

from plotloom.content_language_classifier import string_leaves
from plotloom.content_language_contract import (
    CHECK_INPUT,
    ContentLanguageResult,
    bind_language_result,
    language_check_instructions,
    language_result_schema,
)
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
    coordinates = [fields[field] for field in ("sourceSpan", "candidateSpan")]
    coordinates.append(schema["$defs"]["LanguageFinding"]["properties"]["span"])
    for coordinate in coordinates:
        path = coordinate["properties"]["path"]
        assert "enum" not in path and path["not"] == {}
    assert bind_language_result(request, result_for(request)).verdict == "pass"


def test_provider_technical_literal_exception_is_owned_by_literal_review():
    from tests.provider_literal_fixtures import add_fact, claim, literal_source

    original = original_request("characters")
    original.source = {"text": "A cup follows the agreed source direction."}
    literal_source(original)
    fact = add_fact(original)
    candidate = {"lang": "zh", "characters": [{"id": "keeper", "name": "Mara", "image": {
        "prompt": "黄色杯子贴着安字。", "sheet": "Technical sheet showing the exact label 安."}}]}
    technical_path = "$.characters[0].image.sheet"
    claim(original, candidate, technical_path, fact=fact)
    request = checking_request(original, candidate)
    frozen = request.input_artifacts[CHECK_INPUT]
    result = result_for(request)
    technical = next(row for row in result["coverage"] if row["path"] == technical_path)
    assert technical["role"] == "provider_technical" and technical["verdict"] == "pass"
    assert result["literalReview"]["claims"][0]["verdict"] == "pass"
    assert result["literalReview"]["facts"][0]["verdict"] == "pass"
    assert bind_language_result(request, result).verdict == "pass"

    source_path = "$.source.text"
    source_text = dict(string_leaves(frozen["sources"]))[source_path]
    candidate_text = dict(string_leaves(frozen["candidate"]))[technical_path]
    reviewed_technical = deepcopy(result)
    next(row for row in reviewed_technical["coverage"] if row["path"] == technical_path)["verdict"] = "reject"
    reviewed_technical["verdict"] = "reject"
    reviewed_technical["findings"] = [{"code": "wrong_language",
        "span": {"path": technical_path, "start": 0, "end": len(candidate_text), "text": candidate_text},
        "explanation": "Synthetic test finding; technical provider language still receives semantic review."}]
    assert bind_language_result(request, reviewed_technical).verdict == "reject"

    offset = candidate_text.index("安")
    source_offset = source_text.index("安")
    failed_response = deepcopy(result)
    failed_row = next(row for row in failed_response["coverage"] if row["path"] == technical_path)
    failed_row["exceptions"] = [{"kind": "literal_visible_text",
        "candidateSpan": {"path": technical_path, "start": offset, "end": offset + 1, "text": "安"},
        "sourceSpan": {"path": source_path, "start": source_offset, "end": source_offset + 1, "text": "安"}}]

    # The previous dynamic candidate-span enum included provider technical paths.
    previous_candidate_paths = [row["path"] for row in frozen["inventory"]
        if row["role"] in {"authored_prose", "provider_technical"}
        and dict(string_leaves(frozen["candidate"]))[row["path"]].strip()]
    assert technical_path in previous_candidate_paths

    schema = language_result_schema(frozen)
    exception_path_enum = schema["$defs"]["LanguageException"]["properties"]["candidateSpan"]["properties"]["path"]["enum"]
    finding_path_enum = schema["$defs"]["LanguageFinding"]["properties"]["span"]["properties"]["path"]["enum"]
    assert technical_path not in exception_path_enum
    assert technical_path in finding_path_enum
    conditions = schema["properties"]["coverage"]["items"]["allOf"]
    assert conditions[1]["if"]["properties"]["role"]["enum"] == [
        "exact_source", "provider_technical", "stable_identity"]
    assert conditions[1]["then"]["properties"]["exceptions"]["maxItems"] == 0
    assert conditions[2]["if"]["properties"]["verdict"]["const"] == "not_applicable"
    assert conditions[2]["then"]["properties"]["exceptions"]["maxItems"] == 0
    assert conditions[3]["then"]["properties"]["verdict"]["enum"] == ["pass", "reject", "uncertain"]

    # The generic model accepts this otherwise well-formed row; the frozen schema and binder reject it.
    assert ContentLanguageResult.model_validate(failed_response).verdict == "pass"
    with pytest.raises(ValueError, match="only authored prose can carry explicit semantic exceptions"):
        bind_language_result(request, failed_response)
    instructions = language_check_instructions(frozen)
    assert "Only nonempty authored_prose coverage rows may contain exceptions" in instructions
    assert "provider_technical, exact_source, stable_identity and not_applicable rows must have empty exceptions" in instructions
    assert "literal semantics belong in the required literalReview" in instructions



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
