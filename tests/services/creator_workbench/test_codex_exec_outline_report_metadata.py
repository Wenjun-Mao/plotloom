"""Outline metadata fails before trusted subprocesses, preserving guard priority."""
import json
from pathlib import Path

import pytest
from codex_exec_supervisor_errors import CodexExecValidationFailure
from codex_exec_supervisor_test_support import _prepared_text_job

from plotloom.codex_exec_resources import codex_exec_source_resources
from plotloom.outline_report_metadata import OUTLINE_REPORT_SCHEMA_FILENAME


def _candidate(supervisor, tmp_path, monkeypatch, raw=b'{"lang":"zh-CN"}'):
    _exchange, _request, _pin, job, attempt, profile = _prepared_text_job(supervisor, tmp_path)
    package = json.loads((job / "package/request.json").read_bytes())
    resources = codex_exec_source_resources(supervisor.source_root, package)
    (job / "delivery").mkdir()
    (job / "delivery/outline.json").write_bytes(raw)
    private = tmp_path / "validation-attempt"
    private.mkdir()
    monkeypatch.setattr(supervisor, "_spawn_validation_process", lambda *_a: pytest.fail("must not spawn"))
    return job, attempt, profile, package, private, resources


@pytest.mark.parametrize("raw", [b'{"lang":"zh-CN"}', b'{"lang":false}', b'[]', b'null', b'{invalid'])
def test_invalid_metadata_has_no_spawn_report_or_receipt(supervisor, tmp_path, monkeypatch, raw):
    job, attempt, profile, package, private, resources = _candidate(supervisor, tmp_path, monkeypatch, raw)
    with pytest.raises(CodexExecValidationFailure, match="outline_report_metadata_invalid"):
        supervisor._validate_text_delivery(attempt, profile, package, job, private, resources)
    assert (job / "delivery/outline.json").read_bytes() == raw
    assert sorted(p.name for p in (job / "delivery").iterdir()) == ["outline.json"]
    assert not (private / "validation").exists()
    assert not (private / "sandbox-home").exists()
    assert supervisor._row(attempt.attempt_id) is None


def test_native_bad_artifact_precedes_changed_package_and_foreign_manifest(supervisor, tmp_path, monkeypatch):
    job, attempt, profile, package, private, resources = _candidate(supervisor, tmp_path, monkeypatch)
    package["inputArtifacts"][OUTLINE_REPORT_SCHEMA_FILENAME] = {}
    (job / "package/request.json").write_bytes(b"broken package")
    (job / "delivery/completion.json").write_text('{"jobId":"foreign"}')
    with pytest.raises(CodexExecValidationFailure, match="validation_plan_invalid"):
        supervisor._validate_text_delivery(attempt, profile, package, job, private, resources)


def test_candidate_digest_precedes_bad_metadata(supervisor, tmp_path, monkeypatch):
    import plotloom.codex_exec_files as files

    job, attempt, profile, package, private, resources = _candidate(supervisor, tmp_path, monkeypatch)
    monkeypatch.setattr(files, "read_confined_regular_file", lambda *_a, **_k: b'{"lang":"en-US"}')
    with pytest.raises(CodexExecValidationFailure, match="validation_candidate_changed"):
        supervisor._validate_text_delivery(attempt, profile, package, job, private, resources)


def test_confined_reader_rejects_parent_link_race(supervisor, tmp_path, monkeypatch):
    import plotloom.codex_exec_files as files

    job, attempt, profile, package, private, resources = _candidate(supervisor, tmp_path, monkeypatch)
    real_read = files.read_confined_regular_file

    def race(root: Path, relative: str, **options):
        assert root == job and relative == "delivery/outline.json"
        (job / "delivery").rename(job / "original-delivery")
        (job / "delivery").symlink_to(job / "original-delivery", target_is_directory=True)
        return real_read(root, relative, **options)

    monkeypatch.setattr(files, "read_confined_regular_file", race)
    with pytest.raises(CodexExecValidationFailure, match="candidate_read_invalid"):
        supervisor._validate_text_delivery(attempt, profile, package, job, private, resources)


def test_existing_inventory_failure_precedes_metadata(supervisor, tmp_path, monkeypatch):
    job, attempt, profile, package, private, resources = _candidate(supervisor, tmp_path, monkeypatch)
    (job / "delivery/report.html").write_bytes(b"")
    with pytest.raises(CodexExecValidationFailure, match="candidate_inventory_invalid"):
        supervisor._validate_text_delivery(attempt, profile, package, job, private, resources)
