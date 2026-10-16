"""Prospective Outline schema identity and intentional native plan error order."""
from pathlib import Path

import pytest

from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.creative_handoff_contracts import (
    CreativeHandoffError,
    CreativeHandoffRequest,
)
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.outline_report_metadata import (
    OUTLINE_REPORT_SCHEMA_FILENAME,
    outline_report_metadata_schema,
)

PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
REVISION = "d" * 40


def _request(artifacts):
    return CreativeHandoffRequest(job_id="ch_" + "a" * 20, project_id="project", section_id="story",
        stage="outline", expected_stage_revision=0, source={"text": "source"},
        input_artifacts=artifacts, creative_brief="candidate only")


@pytest.mark.parametrize("fault,code", [("pin", "execution_pin_missing"), ("revision", "executor_revision_missing")])
def test_native_pin_and_revision_precede_missing_artifact(tmp_path, fault, code):
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    with pytest.raises(CreativeHandoffError) as error:
        exchange.write_package(_request({}), {} if fault == "pin" else PIN,
            executor_backend="codex_exec", plotloom_code_revision=None if fault == "revision" else REVISION)
    assert error.value.code == code


def test_direct_plan_pin_and_revision_precede_bad_artifact():
    with pytest.raises(ValueError, match="execution pin"):
        build_text_validation_plan(_request({}), execution_pin={}, source_revision=REVISION)
    with pytest.raises(ValueError, match="source revision"):
        build_text_validation_plan(_request({}), execution_pin=PIN, source_revision="invalid")


def test_native_plan_precondition_precedes_frozen_package_and_manifest(tmp_path):
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    request = _request({OUTLINE_REPORT_SCHEMA_FILENAME: outline_report_metadata_schema()})
    paths = exchange.write_package(request, PIN, executor_backend="codex_exec", plotloom_code_revision=REVISION)
    (Path(paths["packagePath"]) / "request.json").write_text("broken")
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    (delivery / "completion.json").write_text('{"jobId":"foreign"}')
    with pytest.raises(CreativeHandoffError) as error:
        exchange.read_delivery(request.model_copy(update={"input_artifacts": {}}), PIN,
            executor_backend="codex_exec", plotloom_code_revision=REVISION)
    assert error.value.code == "outline_report_schema_missing"


@pytest.mark.parametrize("backend", ["specialist_chat", "codex_exec"])
def test_new_publication_requires_schema_without_repair(tmp_path, backend):
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    with pytest.raises(CreativeHandoffError) as error:
        exchange.write_package(_request({}), PIN, executor_backend=backend, plotloom_code_revision=REVISION)
    assert error.value.code == "outline_report_schema_missing"
    assert not (exchange.root / "jobs" / ("ch_" + "a" * 20) / "package").exists()


@pytest.mark.parametrize("recovery", ["write_package", "verified_package_paths"])
def test_existing_manual_package_requires_current_schema_after_package_checks(tmp_path, monkeypatch, recovery):
    import plotloom.outline_report_metadata as metadata

    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    request = _request({OUTLINE_REPORT_SCHEMA_FILENAME: outline_report_metadata_schema()})
    paths = exchange.write_package(request, PIN)
    monkeypatch.setattr(metadata, "outline_report_metadata_schema", lambda: {"new": "schema"})
    with pytest.raises(CreativeHandoffError) as error:
        getattr(exchange, recovery)(request, PIN)
    assert error.value.code == "outline_report_schema_stale"
    (Path(paths["packagePath"]) / "COPY_ASSIGNMENT.txt").write_text("changed")
    with pytest.raises(CreativeHandoffError) as error:
        getattr(exchange, recovery)(request, PIN)
    assert error.value.code == "package_conflict"


def test_schema_is_hashed_and_other_stages_keep_their_language_domain():
    request = _request({OUTLINE_REPORT_SCHEMA_FILENAME: outline_report_metadata_schema()})
    plan = build_text_validation_plan(request, execution_pin=PIN, source_revision=REVISION)
    assert [item.filename for item in plan.inputs] == [OUTLINE_REPORT_SCHEMA_FILENAME]
    assert [(step.step_id, step.program, step.argv[1:]) for step in plan.steps] == [
        ("validate", "node", ("validate", "{candidate}")),
        ("render", "node", ("render", "{candidate}", "--html")),
    ]
    other = request.model_copy(update={"stage": "art", "input_artifacts": {"cast.json": {}, "art-style-contract.json": {}}})
    assert build_text_validation_plan(other, execution_pin=PIN, source_revision=REVISION).stage == "art"
