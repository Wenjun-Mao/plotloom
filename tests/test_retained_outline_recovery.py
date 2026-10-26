"""Passive historical Outline representation stays distinct from live admission."""
import json
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from plotloom.autopilot_contracts import CheckpointEvidence
from plotloom.codex_exec_delivery import publish_creative_completion
from plotloom.codex_exec_runtime import package_tree_hash
from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.creative_package_projection import project_creative_package
from plotloom.creative_exchange_files import creative_job_root
from plotloom.creative_handoff_identity import canonical_json
from plotloom.persistence.project.autopilot_bindings import assert_checkpoint_binding
from plotloom.project_storage import ProjectStorageCorruptionError
from plotloom.project_storage.autopilot_validation import assert_autopilot_contracts
from plotloom.project_storage.creative_evidence_inventory import (
    _codex_creative_jobs,
    _retained_codex_request_projection,
    creative_evidence_paths,
)
from tests.autopilot_controller_fixtures import UPSTREAM_PIN
from tests.retained_outline_fixtures import (
    REVISION,
    digest,
    historical_package,
    historical_profile,
    historical_request,
    stopped_native_outline,
    storage_at,
)
from tests.source_outline_fixtures import _material, _request


@pytest.mark.parametrize("version", [6, 7, 8])
@pytest.mark.parametrize("schema", ["missing", "different"])
def test_passive_outline_projection_preserves_original_schema_and_plan(tmp_path, version, schema):
    request = historical_request(_request("project", _material()), schema)
    original = request.model_dump_json(by_alias=True)
    projected = _retained_codex_request_projection(request, UPSTREAM_PIN, historical_profile(version),
        CreativeHandoffExchange(tmp_path).root, plotloom_code_revision=REVISION)
    assert projected == historical_package(request, UPSTREAM_PIN)
    assert request.model_dump_json(by_alias=True) == original


@pytest.mark.parametrize("version", [6, 7, 8])
def test_current_outline_projection_matches_live_package(tmp_path, version):
    request = _request("project", _material())
    exchange = CreativeHandoffExchange(tmp_path)
    expected, *_ = project_creative_package(creative_job_root(exchange.root, request.job_id), request, UPSTREAM_PIN, executor_backend="codex_exec", plotloom_code_revision=REVISION)
    assert _retained_codex_request_projection(request, UPSTREAM_PIN, historical_profile(version),
        exchange.root, plotloom_code_revision=REVISION) == expected


@pytest.mark.parametrize("boundary,allowed", [("inputs", True), ("inputs", False), ("filename", True), ("filename", False), ("size", True), ("size", False)])
def test_historical_expected_plan_retains_plan_v1_structural_limits(tmp_path, boundary, allowed):
    if boundary == "inputs":
        artifacts = {f"input-{index:02}.json": {} for index in range(64 if allowed else 65)}
    elif boundary == "filename":
        artifacts = {"n" * ((180 if allowed else 181) - len(".json")) + ".json": {}}
    else:
        size = 1_000_000 if allowed else 1_000_001
        artifacts = {"input.json": {"value": "x" * (size - len(canonical_json({"value": ""})))}}
        assert len(canonical_json(artifacts["input.json"])) == size
    request = _request("project", _material()).model_copy(update={"input_artifacts": artifacts})
    def project():
        return _retained_codex_request_projection(request, UPSTREAM_PIN, historical_profile(8),
            CreativeHandoffExchange(tmp_path).root, plotloom_code_revision=REVISION)
    if allowed:
        assert project() == historical_package(request, UPSTREAM_PIN)
    else:
        with pytest.raises(ProjectStorageCorruptionError, match="package projection"):
            project()


def _creative_hashes(home):
    return {path.relative_to(home).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in (home / "outputs/creative-handoff").rglob("*") if path.is_file()}


def _native_binding(home, request):
    with sqlite3.connect(home / "project.sqlite3") as connection:
        return _codex_creative_jobs(connection)[request.job_id]


def test_fresh_current_schema_native_fixture_satisfies_database_and_restore_contracts(tmp_path):
    storage, project_id, home, request, _pin, _profile, attempt, receipt = stopped_native_outline(
        tmp_path / "original", schema="current")
    original = _creative_hashes(home)
    snapshot = storage.recovery.create_snapshot(project_id)
    snapshot_home = storage_at(tmp_path / "snapshot-restored").recovery.restore(Path(snapshot.location))
    folder_home = storage_at(tmp_path / "folder-restored").recovery.restore(home)
    for retained in (snapshot_home, folder_home):
        assert _creative_hashes(retained) == original
        binding = _native_binding(retained, request)
        assert binding["attempt"] == attempt
        assert binding["receipt"] == receipt


@pytest.mark.parametrize("version", [6, 7, 8])
@pytest.mark.parametrize("schema", ["missing", "different"])
def test_stopped_native_snapshot_and_folder_restore_keep_original_bytes_and_identities(tmp_path, monkeypatch, version, schema):
    storage, project_id, home, request, pin, profile, attempt, receipt = stopped_native_outline(
        tmp_path / "original", version=version, schema=schema)
    original = _creative_hashes(home)

    def forbidden(*args, **kwargs):
        pytest.fail("passive recovery invoked live projection, validation or a process")

    monkeypatch.setattr("plotloom.codex_exec_validation.build_text_validation_plan", forbidden)
    monkeypatch.setattr("plotloom.creative_handoff_package_exchange.project_creative_package", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    storage.projects.reopen_project(project_id)
    with closing(storage.projects.open(project_id)) as store:
        assert str(store.manifest.project_id) == project_id
        assert store.repository.autopilot.current(project_id).checkpoints[0]["evidence"]["jobId"] == request.job_id
    with closing(storage.projects.inspect(project_id, passive=True)) as store:
        assert str(store.manifest.project_id) == project_id
    storage.projects.close_project(project_id)
    snapshot = storage.recovery.create_snapshot(project_id)
    assert original.items() <= {(item.relative_path, item.content_hash) for item in snapshot.manifest.files}
    snapshot_home = storage_at(tmp_path / "snapshot-restored").recovery.restore(Path(snapshot.location))
    folder_home = storage_at(tmp_path / "folder-restored").recovery.restore(home)
    for retained in (home, snapshot_home, folder_home):
        assert _creative_hashes(retained) == original
        binding = _native_binding(retained, request)
        assert binding["attempt"] == attempt
        assert binding["receipt"] == receipt
        assert binding["profile"] == profile
        package = json.loads((retained / "outputs/creative-handoff/jobs" / request.job_id / "package/request.json").read_bytes())
        assert package == historical_package(request, pin)


@pytest.mark.parametrize("version", [6, 7, 8])
@pytest.mark.parametrize("schema,code", [("missing", "outline_report_schema_missing"), ("different", "outline_report_schema_stale")])
def test_passively_recoverable_request_still_fails_all_live_package_paths(tmp_path, version, schema, code):
    _storage, project_id, home, request, pin, profile, attempt, receipt = stopped_native_outline(tmp_path, version=version, schema=schema)
    exchange = CreativeHandoffExchange(home / "outputs/creative-handoff")
    with pytest.raises(CreativeHandoffError) as error:
        build_text_validation_plan(request, execution_pin=pin, source_revision=REVISION)
    assert error.value.code == code
    with sqlite3.connect(home / "project.sqlite3") as connection:
        evidence = CheckpointEvidence.model_validate_json(connection.execute("SELECT evidence FROM v2_autopilot_checkpoints").fetchone()[0])
        with pytest.raises(CreativeHandoffError) as error:
            assert_checkpoint_binding(connection, project_id, "delivered", evidence,
                run_id=str(attempt.run_id), operation_key="outline")
        assert error.value.code == code
    for method in (exchange.write_package, exchange.verified_package_paths, exchange.read_delivery):
        with pytest.raises(CreativeHandoffError) as error:
            method(request, pin, executor_backend="codex_exec", plotloom_code_revision=REVISION)
        assert error.value.code == code
    with pytest.raises(CreativeHandoffError) as error:
        publish_creative_completion(request=request, execution_pin=pin, code_revision=REVISION,
            job_root=exchange.root / "jobs" / request.job_id, attempt=attempt, profile=profile, receipt=receipt)
    assert error.value.code == code


@pytest.mark.parametrize("version", [6, 7, 8])
@pytest.mark.parametrize("schema", ["missing", "different"])
def test_both_passive_checkpoint_and_decision_consumers_avoid_live_plan(tmp_path, monkeypatch, version, schema):
    _storage, _project_id, home, _request, _pin, _profile, _attempt, _receipt = stopped_native_outline(
        tmp_path, version=version, schema=schema)
    import plotloom.project_storage.autopilot_validation as validation

    calls = []
    retained = validation._assert_checkpoint_binding
    def record(*args, **kwargs):
        assert kwargs["validation_plan_for_request"] is validation._retained_checkpoint_validation_plan
        calls.append((args[2], kwargs["operation_key"]))
        return retained(*args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail("passive checkpoint/decision validation used live plan or process")
    monkeypatch.setattr(validation, "_assert_checkpoint_binding", record)
    monkeypatch.setattr("plotloom.codex_exec_validation.build_text_validation_plan", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        assert_autopilot_contracts(connection)
    assert calls == [("delivered", "outline"), ("delivered", "outline")]


@pytest.mark.parametrize("mutation", ["decision_policy", "decision_owner", "decision_delivery", "checkpoint_identity", "receipt", "plan", "source", "pin"])
def test_passive_database_validation_retains_checkpoint_and_decision_corruption_guards(tmp_path, mutation):
    _storage, _project_id, home, _request, _pin, _profile, _attempt, _receipt = stopped_native_outline(tmp_path)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        if mutation.startswith("decision_"):
            def mutate(item):
                if mutation == "decision_policy":
                    item["policyHash"] = "f" * 64
                elif mutation == "decision_owner":
                    item["evidence"]["owner"] = "characters"
                else:
                    item["evidence"]["deliveryHash"] = "f" * 64
            _update_json(connection, "v2_autopilot_decisions", "decision", mutate)
        elif mutation == "checkpoint_identity":
            _update_json(connection, "v2_autopilot_checkpoints", "evidence", lambda item: item.update(requestHash="f" * 64))
        elif mutation == "receipt":
            _update_json(connection, "v2_autopilot_exec_attempts", "receipt", lambda item: item.update(sessionId=str(uuid4())))
        elif mutation == "plan":
            _update_json(connection, "v2_autopilot_exec_attempts", "snapshot", lambda item: item.update(validationPlanHash="f" * 64))
        elif mutation == "source":
            _update_json(connection, "v2_autopilot_runs", "policy", lambda item: item.update(codeRevision="f" * 40))
        else:
            _update_json(connection, "v2_creative_handoff_execution_pins", "execution_pin", lambda item: item.update(upstreamSkillHash="f" * 64))
        with pytest.raises(ProjectStorageCorruptionError, match="persisted autopilot authority"):
            assert_autopilot_contracts(connection)


def _update_json(connection, table, column, mutate):
    value = json.loads(connection.execute(f"SELECT {column} FROM {table}").fetchone()[0])
    mutate(value)
    connection.execute(f"UPDATE {table} SET {column}=?", (json.dumps(value),))


@pytest.mark.parametrize("mutation", ["argv", "route"])
def test_recorded_plan_self_hash_and_rebound_package_cannot_authorize_changed_commands(tmp_path, mutation):
    _storage, _project_id, home, request, _pin, profile, _attempt, _receipt = stopped_native_outline(tmp_path)
    job = home / "outputs/creative-handoff/jobs" / request.job_id
    path = job / "package/request.json"
    value = json.loads(path.read_bytes())
    if mutation == "argv":
        value["validationPlan"]["steps"][0]["argv"][0] = "{source}/scripts/other-validator.mjs"
    else:
        value["validationPlan"]["route"] = "plotloom_native"
    value["validationPlanHash"] = digest(value["validationPlan"])
    path.write_text(json.dumps(value))
    package_hash = package_tree_hash(job, max_total_bytes=profile.max_output_bytes)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        # Rebind the outer package hash so the independent expected-plan comparison is exercised.
        _update_json(connection, "v2_autopilot_exec_attempts", "snapshot", lambda item: item.update(packageHash=package_hash))
        _update_json(connection, "v2_autopilot_exec_attempts", "receipt",
            lambda item: (item.update(packageHash=package_hash), item["textValidation"].update(packageHash=package_hash)))
    with pytest.raises(ProjectStorageCorruptionError, match="frozen request/pin"):
        creative_evidence_paths(home, home / "project.sqlite3")


@pytest.mark.parametrize("mutation", ["package", "request", "pin", "source", "input", "attempt", "receipt", "candidate", "report", "plan_binding"])
def test_historical_outline_inventory_keeps_original_corruption_guards(tmp_path, mutation):
    _storage, _project_id, home, request, _pin, _profile, _attempt, _receipt = stopped_native_outline(tmp_path)
    job = home / "outputs/creative-handoff/jobs" / request.job_id
    if mutation in {"package", "input", "candidate", "report"}:
        path = {"package": job / "package/COPY_ASSIGNMENT.txt", "input": next((job / "package/inputs").iterdir()),
            "candidate": job / "delivery/outline.json", "report": job / "delivery/report.html"}[mutation]
        path.write_bytes(path.read_bytes() + b" ")
    else:
        with sqlite3.connect(home / "project.sqlite3") as connection:
            if mutation == "request":
                _update_json(connection, "v2_source_outline_candidates", "request", lambda item: item.update(creativeBrief="changed"))
            elif mutation == "pin":
                _update_json(connection, "v2_creative_handoff_execution_pins", "execution_pin", lambda item: item.update(upstreamSkillHash="f" * 64))
            elif mutation == "source":
                _update_json(connection, "v2_autopilot_runs", "policy", lambda item: item.update(codeRevision="b" * 40))
            elif mutation == "attempt":
                _update_json(connection, "v2_autopilot_exec_attempts", "snapshot", lambda item: item.update(requestHash="f" * 64))
            elif mutation == "plan_binding":
                _update_json(connection, "v2_autopilot_exec_attempts", "snapshot", lambda item: item.update(validationPlanHash="f" * 64))
            else:
                _update_json(connection, "v2_autopilot_exec_attempts", "receipt", lambda item: item.update(sessionId=str(uuid4())))
    with pytest.raises(ProjectStorageCorruptionError):
        creative_evidence_paths(home, home / "project.sqlite3")
