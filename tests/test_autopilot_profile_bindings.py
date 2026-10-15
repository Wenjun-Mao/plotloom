"""Real validation paths retain SQL, failure priority and fresh trust boundaries."""
from contextlib import closing
import inspect
import json
import sqlite3
from uuid import uuid4

import pytest

from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.persistence.project import autopilot_bindings as bindings
from plotloom.persistence.project.autopilot_profile_construction import _ProfileConstruction
from plotloom.project_storage import autopilot_validation as validation
from tests.autopilot_profile_fixtures import observe_constructions, seed_profile_graph


@pytest.fixture
def graph(tmp_path):
    with closing(sqlite3.connect(tmp_path / "profile.sqlite3")) as connection:
        yield connection, seed_profile_graph(connection)


def binding(connection, graph, slot=None, *, state="prepared"):
    if slot is None:
        return bindings.assert_checkpoint_binding(connection, graph.project_id, state,
            graph.evidence, run_id=graph.run_id, operation_key="outline")
    return bindings._assert_checkpoint_binding(connection, graph.project_id, state,
        graph.evidence, run_id=graph.run_id, operation_key="outline", profile_construction=slot)


def observed(connection, callback):
    trace, before = [], connection.total_changes
    connection.set_trace_callback(trace.append)
    try:
        try:
            result = ("return", callback())
        except Exception as error:
            result = ("error", type(error), str(error))
    finally:
        connection.set_trace_callback(None)
    assert connection.total_changes == before
    return trace, result


def test_public_signature_and_standalone_calls_remain_fresh(graph, monkeypatch):
    connection, data = graph
    assert list(inspect.signature(bindings.assert_checkpoint_binding).parameters) == [
        "connection", "project_id", "state", "evidence", "run_id", "operation_key", "asset_home"]
    calls = observe_constructions(monkeypatch)
    for _ in range(2):
        assert binding(connection, data) is None
    assert len(calls) == 4
    calls.clear()
    slot = _ProfileConstruction()
    private = observed(connection, lambda: binding(connection, data, slot))
    public = observed(connection, lambda: binding(connection, data))
    assert private == public and private[1] == ("return", None)
    assert len(calls) == 3


@pytest.mark.parametrize("defect", [
    "malformed-policy", "null-policy", "wrong-project", "missing-attempt",
    "invalid-snapshot", "invalid-profile", "invalid-state", "invalid-receipt", "wrong-request",
])
def test_private_path_preserves_native_errors_and_validation_order(graph, monkeypatch, defect):
    connection, data = graph
    if defect in {"malformed-policy", "null-policy", "invalid-profile"}:
        raw = "{" if defect == "malformed-policy" else "null" if defect == "null-policy" else json.dumps(
            data.policy.model_dump(mode="json", by_alias=True) | {"executorBinding": {}})
        connection.execute("UPDATE v2_autopilot_runs SET policy=?", (raw,))
    elif defect == "wrong-project":
        connection.execute("UPDATE v2_autopilot_runs SET project_id=?", (str(uuid4()),))
    elif defect == "missing-attempt":
        connection.execute("DELETE FROM v2_autopilot_exec_attempts")
    elif defect == "invalid-snapshot":
        connection.execute("UPDATE v2_autopilot_exec_attempts SET snapshot='{}'")
        raw = data.policy.model_dump(mode="json", by_alias=True) | {"executorBinding": {}}
        connection.execute("UPDATE v2_autopilot_runs SET policy=?", (json.dumps(raw),))
    elif defect == "invalid-receipt":
        connection.execute("UPDATE v2_autopilot_exec_attempts SET receipt='{}'")
    elif defect == "wrong-request":
        request = json.loads(connection.execute("SELECT request FROM v2_source_outline_candidates").fetchone()[0])
        request["projectId"] = "different-project"
        connection.execute("UPDATE v2_source_outline_candidates SET request=?", (json.dumps(request),))
    connection.commit()
    connection.execute("PRAGMA query_only=ON")
    state = "delivered" if defect == "invalid-state" else "prepared"
    calls = observe_constructions(monkeypatch)
    public = observed(connection, lambda: binding(connection, data, state=state))
    public_count = len(calls)
    calls.clear()
    private = observed(connection, lambda: binding(connection, data, _ProfileConstruction(), state=state))
    assert private == public and private[1][0] == "error"
    assert len(calls) == public_count == (1 if defect in {
        "invalid-profile", "invalid-state", "invalid-receipt", "wrong-request"} else 0)


def test_validator_shares_only_direct_passes_and_discards_on_each_invocation(graph, monkeypatch):
    connection, _data = graph
    connection.execute("PRAGMA query_only=ON")
    calls = observe_constructions(monkeypatch)

    def fresh(*args, profile_construction, **kwargs):
        return bindings.assert_checkpoint_binding(*args, **kwargs)

    with monkeypatch.context() as baseline:
        baseline.setattr(validation, "_assert_checkpoint_binding", fresh)
        public = observed(connection, lambda: validation.assert_autopilot_contracts(connection))
    assert len(calls) == 4
    calls.clear()
    for _ in range(2):
        private = observed(connection, lambda: validation.assert_autopilot_contracts(connection))
        assert private == public and private[1] == ("return", None)
    assert len(calls) == 2
    assert connection.in_transaction is False


def test_same_policy_across_runs_still_checks_each_attempt_and_independent_connection(graph, monkeypatch):
    connection, _data = graph
    seed_profile_graph(connection, run_id=str(uuid4()), project_id=str(uuid4()))
    calls = observe_constructions(monkeypatch)
    attempts, original = [], bindings.CodexExecAttempt.model_validate

    def validate(cls, value, **options):
        attempts.append(value["attemptId"])
        return original(value, **options)

    monkeypatch.setattr(bindings.CodexExecAttempt, "model_validate", classmethod(validate))
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as independent:
        for current in (connection, independent):
            validation.assert_autopilot_contracts(current)
    assert len(calls) == 2
    assert len(attempts) == 12 and len(set(attempts)) == 2


def test_nested_public_calls_inside_outer_pass_have_no_ambient_slot(graph, monkeypatch):
    from plotloom.project_storage import bridge_adoption_validation
    connection, data = graph
    original = bridge_adoption_validation.assert_bridge_adoption_contracts

    def nested(current):
        original(current)
        binding(current, data)
        binding(current, data)

    monkeypatch.setattr(bridge_adoption_validation, "assert_bridge_adoption_contracts", nested)
    calls = observe_constructions(monkeypatch)
    validation.assert_autopilot_contracts(connection)
    assert len(calls) == 5  # One private construction and four nested public ones.


def test_reentrant_validation_gets_an_independent_owner(graph, monkeypatch):
    connection, _data = graph
    original, calls, entered = CodexExecProfile.model_validate, [], False
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as independent:
        def validate(cls, value, **options):
            nonlocal entered
            calls.append(value)
            if not entered:
                entered = True
                validation.assert_autopilot_contracts(independent)
            return original(value, **options)

        monkeypatch.setattr(CodexExecProfile, "model_validate", classmethod(validate))
        validation.assert_autopilot_contracts(connection)
    assert entered and len(calls) == 2
