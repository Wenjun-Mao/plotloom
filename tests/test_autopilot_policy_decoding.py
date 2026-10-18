"""Each freshly selected policy is decoded once without caching observations."""
import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.autopilot_contracts import CheckpointEvidence
from plotloom.persistence.project import autopilot_bindings as bindings
from tests.autopilot_geometry_fixtures import copy_geometry_frame_seed
from tests.autopilot_policy_fixtures import seed_text_graph
from tests.autopilot_seed_fixtures import seed_files

POLICY_SQL = "SELECT project_id,policy FROM v2_autopilot_runs WHERE id=?"


def observe(connection, callback):
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


def decode_spy(monkeypatch, policies, *, on_first=None):
    decoded = []

    def loads(raw):
        if raw in policies:
            decoded.append(raw)
            if len(decoded) == 1 and on_first is not None:
                on_first()
        return json.loads(raw)

    monkeypatch.setattr(bindings, "json", SimpleNamespace(loads=loads))
    return decoded


def bind(connection, data, *, private=False):
    kwargs = dict(run_id=data.run_id, operation_key=data.operation_key, asset_home=None)
    if hasattr(data, "asset_home"):
        kwargs["asset_home"] = data.asset_home
    if private:
        return bindings._assert_checkpoint_binding(connection, data.project_id, data.state,
            data.evidence, validation_plan_for_request=bindings._current_checkpoint_validation_plan, **kwargs)
    return bindings.assert_checkpoint_binding(connection, data.project_id, data.state, data.evidence, **kwargs)


@pytest.fixture
def text_graph(tmp_path, request):
    version = getattr(request, "param", 8)
    with closing(sqlite3.connect(tmp_path / "policy.sqlite3")) as connection:
        graph = seed_text_graph(connection, version=version)
        graph.state, graph.operation_key = "prepared", "outline"
        graph.raw_policy = connection.execute("SELECT policy FROM v2_autopilot_runs").fetchone()[0]
        yield connection, graph


@pytest.fixture
def image_graph(tmp_path, geometry_frame_seed, request):
    owner = getattr(request, "param", "image")
    storage, view = copy_geometry_frame_seed(geometry_frame_seed, tmp_path / "copy")
    with closing(storage.projects.open(view.project_id)) as store:
        checkpoint = next(item for item in view.checkpoints if item["evidence"]["owner"] == owner)
        data = SimpleNamespace(run_id=str(view.id), project_id=view.project_id, owner=owner,
            state=checkpoint["state"], operation_key=checkpoint["operationKey"],
            evidence=CheckpointEvidence.model_validate(checkpoint["evidence"]),
            asset_home=store.home, database=store.database_path)
    # Existing seed closure proves no host/lease remains. Each ordinary-opened
    # independent copy below feeds only read-only binding validation; consumers
    # create no controller, host, dispatch, or fresh image operation.
    with closing(sqlite3.connect(data.database)) as connection:
        assert connection.execute("SELECT count(*) FROM v2_autopilot_exec_attempts "
            "WHERE state NOT IN ('completed','failed','settled') OR image_budget_state='reserved'").fetchone()[0] == 0
        assert set(bindings.IMAGE_OWNERS) <= {item["evidence"]["owner"] for item in view.checkpoints}
        data.raw_policy = connection.execute("SELECT policy FROM v2_autopilot_runs WHERE id=?", (data.run_id,)).fetchone()[0]
        _table, deliveries, foreign_key = bindings.IMAGE_OWNERS[owner]
        data.delivery_id = connection.execute(
            f'SELECT id FROM "{deliveries}" WHERE "{foreign_key}"=? AND manifest_hash=?',
            (data.evidence.job_id, data.evidence.delivery_hash)).fetchone()[0]
        connection.execute("PRAGMA query_only=ON")
        yield connection, data
    assert seed_files(geometry_frame_seed.root) == geometry_frame_seed.files


def text_sql(data):
    trace = [
        inheritance_sql(data),
        f"SELECT project_id,policy FROM v2_autopilot_runs WHERE id='{data.run_id}'",
        f"SELECT * FROM v2_autopilot_exec_attempts WHERE id='{data.evidence.executor_attempt_id}'",
        f'SELECT * FROM "v2_source_outline_candidates" WHERE job_id=\'{data.evidence.job_id}\'',
        f"SELECT * FROM v2_creative_handoff_execution_pins WHERE job_id='{data.evidence.job_id}'",
        f"SELECT policy FROM v2_autopilot_runs WHERE id='{data.run_id}'",
    ]
    return trace


def inheritance_sql(data):
    return f"SELECT origin_checkpoint_id,evidence_hash,project_id FROM v2_autopilot_inheritance WHERE run_id='{data.run_id}' AND operation_key='{data.operation_key}'"


def image_sql(data):
    table, deliveries, foreign_key = bindings.IMAGE_OWNERS[data.owner]
    candidates = deliveries.replace("deliveries", "candidates")
    return [
        inheritance_sql(data),
        f"SELECT project_id,policy FROM v2_autopilot_runs WHERE id='{data.run_id}'",
        f"SELECT * FROM v2_autopilot_exec_attempts WHERE id='{data.evidence.executor_attempt_id}'",
        f'SELECT * FROM "{table}" WHERE id=\'{data.evidence.job_id}\'',
        f"SELECT project_id,policy FROM v2_autopilot_runs WHERE id='{data.run_id}'",
        f'SELECT manifest_hash,manifest,id,state FROM "{deliveries}" WHERE "{foreign_key}"=\'{data.evidence.job_id}\' AND manifest_hash IS NOT NULL',
        f'SELECT candidate.asset_id,candidate.output_filename,candidate.output_hash,candidate.role,asset.project_id,asset.original_hash FROM "{candidates}" AS candidate JOIN v2_managed_assets AS asset ON asset.id=candidate.asset_id WHERE candidate."{foreign_key}"=\'{data.evidence.job_id}\' AND candidate.delivery_id=\'{data.delivery_id}\'',
    ]


class BeforeSecondPolicyRead:
    """Commit through a separate writer without altering reader cursors or SQL."""

    def __init__(self, connection, commit):
        self.connection, self.commit, self.reads = connection, commit, 0

    def execute(self, sql, values=()):
        if sql == POLICY_SQL:
            self.reads += 1
            if self.reads == 2:
                self.commit()
        return self.connection.execute(sql, values)


@pytest.mark.parametrize("text_graph", [5, 6, 7, 8], indirect=True)
@pytest.mark.parametrize("private", [False, True])
def test_text_binding_decodes_each_selected_policy_and_preserves_sql(text_graph, monkeypatch, private):
    connection, data = text_graph
    decoded = decode_spy(monkeypatch, {data.raw_policy})
    trace, result = observe(connection, lambda: bind(connection, data, private=private))
    assert result == ("return", None)
    assert trace == text_sql(data)
    assert decoded == [data.raw_policy] * 2


@pytest.mark.parametrize("image_graph", ["image", "character-reference", "art-reference"], indirect=True)
@pytest.mark.parametrize("private", [False, True])
def test_completed_native_image_keeps_two_policy_reads_and_receipt_queries(image_graph, monkeypatch, private):
    connection, data = image_graph
    decoded = decode_spy(monkeypatch, {data.raw_policy})
    trace, result = observe(connection, lambda: bind(connection, data, private=private))
    assert result == ("return", None)
    assert trace == image_sql(data)
    assert decoded == [data.raw_policy, data.raw_policy]


@pytest.mark.parametrize("raw,error", [("{", json.JSONDecodeError), ("null", AttributeError)])
def test_attempt_policy_decode_still_precedes_wrong_project(text_graph, monkeypatch, raw, error):
    connection, data = text_graph
    connection.execute("UPDATE v2_autopilot_runs SET policy=?,project_id=?", (raw, str(uuid4())))
    connection.commit()
    decoded = decode_spy(monkeypatch, {raw})
    trace, result = observe(connection, lambda: bind(connection, data))
    assert result[0:2] == ("error", error)
    assert trace == text_sql(data)[:2]
    assert decoded == [raw]


def test_image_wrong_project_still_precedes_malformed_second_policy(image_graph, monkeypatch):
    connection, data = image_graph
    with closing(sqlite3.connect(data.database)) as writer:
        def commit():
            writer.execute("UPDATE v2_autopilot_runs SET project_id=?,policy='{' WHERE id=?",
                (str(uuid4()), data.run_id))
            writer.commit()

        observed = BeforeSecondPolicyRead(connection, commit)
        decoded = decode_spy(monkeypatch, {data.raw_policy, "{"})
        trace, result = observe(connection, lambda: bind(observed, data))
    assert result == ("error", ValueError, "image checkpoint execution differs from frozen launch policy")
    assert observed.reads == 2 and trace == image_sql(data)[:5]
    assert decoded == [data.raw_policy]


@pytest.mark.parametrize("caller_transaction", [False, True])
def test_second_policy_read_uses_its_own_sqlite_observation(image_graph, monkeypatch, caller_transaction):
    connection, data = image_graph
    changed = json.loads(data.raw_policy)
    changed["executionPins"]["image"]["skillHash"] = "f" * 64
    raw = json.dumps(changed)
    with closing(sqlite3.connect(data.database)) as writer:
        assert writer.execute("PRAGMA journal_mode").fetchone()[0] == "wal"

        def commit():
            writer.execute("UPDATE v2_autopilot_runs SET policy=? WHERE id=?", (raw, data.run_id))
            writer.commit()

        if caller_transaction:
            connection.execute("BEGIN")
        observed = BeforeSecondPolicyRead(connection, commit)
        decoded = decode_spy(monkeypatch, {data.raw_policy, raw})
        trace, result = observe(connection, lambda: bind(observed, data))
        assert writer.execute("SELECT policy FROM v2_autopilot_runs WHERE id=?", (data.run_id,)).fetchone()[0] == raw
    assert observed.reads == 2 and connection.in_transaction is caller_transaction
    if caller_transaction:
        assert result == ("return", None) and trace == image_sql(data)
        assert decoded == [data.raw_policy, data.raw_policy]
    else:
        assert result == ("error", ValueError, "image checkpoint execution differs from frozen launch policy")
        assert trace == image_sql(data)[:5] and decoded == [data.raw_policy, raw]
    connection.rollback()


def test_success_failure_and_independent_calls_do_not_retain_policy(text_graph, monkeypatch):
    connection, data = text_graph
    changed = json.loads(data.raw_policy) | {"codeRevision": "f" * 40}
    raw = json.dumps(changed)
    decoded = decode_spy(monkeypatch, {data.raw_policy, raw})
    assert observe(connection, lambda: bind(connection, data)) == (text_sql(data), ("return", None))
    assert decoded == [data.raw_policy] * 2
    connection.execute("UPDATE v2_autopilot_runs SET policy=?", (raw,))
    connection.commit()
    trace, result = observe(connection, lambda: bind(connection, data))
    assert trace == text_sql(data)[:3]
    assert result == ("error", ValueError, "Codex Exec checkpoint differs from its immutable project attempt")
    assert decoded == [data.raw_policy] * 2 + [raw]
    connection.execute("UPDATE v2_autopilot_runs SET policy=?", (data.raw_policy,))
    connection.commit()
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as independent:
        assert observe(independent, lambda: bind(independent, data)) == (text_sql(data), ("return", None))
    assert decoded == [data.raw_policy] * 2 + [raw] + [data.raw_policy] * 2


def test_nested_binding_on_independent_connection_decodes_fresh(text_graph, monkeypatch):
    connection, data = text_graph
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as independent:
        nested = []
        decoded = decode_spy(monkeypatch, {data.raw_policy},
            on_first=lambda: nested.append(observe(independent, lambda: bind(independent, data))))
        assert observe(connection, lambda: bind(connection, data)) == (text_sql(data), ("return", None))
    assert nested == [(text_sql(data), ("return", None))]
    assert decoded == [data.raw_policy] * 4


def test_malformed_native_receipt_still_fails_before_image_queries(image_graph, monkeypatch):
    connection, data = image_graph
    with closing(sqlite3.connect(data.database)) as writer:
        writer.execute("UPDATE v2_autopilot_exec_attempts SET receipt='{}' WHERE id=?",
            (str(data.evidence.executor_attempt_id),))
        writer.commit()
    decoded = decode_spy(monkeypatch, {data.raw_policy})
    trace, result = observe(connection, lambda: bind(connection, data))
    assert result[0:2] == ("error", ValidationError)
    assert trace == image_sql(data)[:3] and decoded == [data.raw_policy]
