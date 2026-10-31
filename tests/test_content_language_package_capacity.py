"""Complete checker envelopes have bounded transport capacity, never live proof."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.content_language_contract import (
    CHECK_INPUT,
    freeze_language_candidate,
    language_result_schema,
)
from plotloom.content_language_persistence import check_rows
from plotloom.content_language_service import ContentLanguageService
from plotloom.creative_handoff_identity import canonical_json
from plotloom.creative_handoff_package_exchange import _json_file_limit
from plotloom.creative_package_projection import project_creative_package
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.creative_execution_pins import freeze_execution_pin
from tests.content_language_fixtures import checking_request, original_request
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION
from tests.test_content_language_contract import CANDIDATES
from tests.test_content_language_persistence import (
    check_environment as _check_environment,
)

check_environment = _check_environment


def _original(project_id, size):
    original = original_request("storyboard", project_id=project_id)
    candidate = deepcopy(CANDIDATES["storyboard"])
    # Source response-schema context is retained in the complete original request,
    # but cannot masquerade as narrative evidence in the semantic checker.
    original.input_artifacts["storyboard-schema.json"] = {"description": ""}
    initial = len(canonical_json(freeze_language_candidate(original, candidate)))
    original.input_artifacts["storyboard-schema.json"]["description"] = "x" * (size - initial)
    assert len(canonical_json(freeze_language_candidate(original, candidate))) == size
    return original, candidate


def _schema(frozen, size):
    schema = language_result_schema(frozen)
    schema["description"] = ""
    schema["description"] = "y" * (size - len(canonical_json(schema)))
    assert len(canonical_json(schema)) == size
    return schema


def _project(request, root):
    return project_creative_package(root, request, PIN,
        executor_backend="codex_exec", plotloom_code_revision=SOURCE_REVISION)[0]


def _envelope(project_id, root, size):
    original, candidate = _original(project_id, 999_000)
    request = checking_request(original, candidate)
    schema = request.input_artifacts["content-language-schema.json"]
    schema["description"] = ""
    remaining = size - len(canonical_json(_project(request, root)))
    assert remaining > 0
    schema["description"] = "z" * remaining
    # The native input-size metadata can gain a decimal digit after padding.
    remaining += size - len(canonical_json(_project(request, root)))
    schema["description"] = "z" * remaining
    assert all(len(canonical_json(value)) <= 1_000_000 for value in request.input_artifacts.values())
    assert len(canonical_json(_project(request, root))) == size
    return original, candidate, request


def test_complete_check_over_one_mb_prepares_publishes_and_reopens_without_dispatch(check_environment, monkeypatch):
    storage, store, registry = check_environment
    original, candidate = _original(store.manifest.project_id, 700_000)
    monkeypatch.setattr("plotloom.content_language_service.language_result_schema",
        lambda frozen: _schema(frozen, 500_000))
    registry.codex_exec_admit = lambda *_args: pytest.fail("unexpected native submission")
    with store.repository._write() as session:
        freeze_execution_pin(session, original, PIN)
    service = ContentLanguageService(registry)
    job = service.prepare(store, original, candidate, code_revision=SOURCE_REVISION, automatic_retry_limit=0)
    request, data = store.repository.content_language.load(original.project_id, job)
    exchange = store.creative_handoff_exchange()
    paths = exchange.write_package(request, PIN, executor_backend="codex_exec",
        plotloom_code_revision=SOURCE_REVISION)
    package = Path(paths["packagePath"])
    encoded = (package / "request.json").read_bytes()
    assert 1_000_000 < len(encoded) <= 2_000_000
    assert len(encoded) > len(encoded.decode("utf-8"))
    assert encoded == canonical_json(_project(request, package.parent))
    assert (package / "inputs" / CHECK_INPUT).read_bytes() == canonical_json(request.input_artifacts[CHECK_INPUT])
    assert request.input_artifacts[CHECK_INPUT]["originalRequest"] == original.model_dump(mode="json", by_alias=True)
    with closing(storage.projects.open(original.project_id)) as reopened:
        retained, retained_data = reopened.repository.content_language.load(original.project_id, job)
        assert retained == request and retained_data["attempt"] == data["attempt"]
        assert reopened.creative_handoff_exchange().verified_package_paths(retained, PIN,
            executor_backend="codex_exec", plotloom_code_revision=SOURCE_REVISION) == paths
    assert _json_file_limit(original) == 1_000_000
    bridge = original.model_copy(update={"stage": "bridge-intent"})
    assert _json_file_limit(bridge) == 2_000_000


@pytest.mark.parametrize("difference", [0, 1])
def test_envelope_boundary_is_complete_and_refuses_before_publication(check_environment, difference):
    _storage, store, _registry = check_environment
    _original_request, _candidate, request = _envelope(store.manifest.project_id,
        store.home / "capacity-projection", 2_000_000 + difference)
    exchange = store.creative_handoff_exchange()
    if difference:
        with pytest.raises(ValueError, match="file limit"):
            exchange.write_package(request, PIN, executor_backend="codex_exec",
                plotloom_code_revision=SOURCE_REVISION)
        assert not (exchange.root / "jobs" / request.job_id).exists()
    else:
        paths = exchange.write_package(request, PIN, executor_backend="codex_exec",
            plotloom_code_revision=SOURCE_REVISION)
        assert len((Path(paths["packagePath"]) / "request.json").read_bytes()) == 2_000_000
        assert exchange.verified_package_paths(request, PIN, executor_backend="codex_exec",
            plotloom_code_revision=SOURCE_REVISION) == paths


def test_oversize_envelope_refuses_before_attempt_or_publication(check_environment, monkeypatch):
    _storage, store, registry = check_environment
    original, candidate, checking = _envelope(store.manifest.project_id,
        store.home / "capacity-projection", 2_000_001)
    schema = checking.input_artifacts["content-language-schema.json"]
    monkeypatch.setattr("plotloom.content_language_service.language_result_schema", lambda _frozen: schema)
    observed = {}
    def project(*args, **kwargs):
        result = project_creative_package(*args, **kwargs)
        observed["bytes"] = len(canonical_json(result[0]))
        return result
    monkeypatch.setattr("plotloom.content_language_service.project_creative_package", project)
    registry.codex_exec_admit = lambda *_args: pytest.fail("unexpected native submission")
    with store.repository._write() as session:
        freeze_execution_pin(session, original, PIN)
    with pytest.raises(InvalidTransitionError, match="单文件容量"):
        ContentLanguageService(registry).prepare(store, original, candidate, code_revision=SOURCE_REVISION)
    assert observed["bytes"] > 2_000_000
    with store.repository._read() as session:
        assert check_rows(session, original.project_id) == []
    assert not list(store.creative_handoff_exchange().root.glob("jobs/*/package"))


def test_individual_check_input_limit_remains_one_mb(check_environment, monkeypatch):
    _storage, store, registry = check_environment
    original, candidate = _original(store.manifest.project_id, 100_000)
    monkeypatch.setattr("plotloom.content_language_service.language_result_schema",
        lambda frozen: _schema(frozen, 1_000_001))
    registry.codex_exec_admit = lambda *_args: pytest.fail("unexpected native submission")
    with store.repository._write() as session:
        freeze_execution_pin(session, original, PIN)
    with pytest.raises(ValueError, match="1000000"):
        ContentLanguageService(registry).prepare(store, original, candidate, code_revision=SOURCE_REVISION)
    with store.repository._read() as session:
        assert check_rows(session, original.project_id) == []
    assert not list(store.creative_handoff_exchange().root.glob("jobs/*/package"))
