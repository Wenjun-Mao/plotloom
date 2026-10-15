"""Independent WAL commits preserve original SQLite observations and failures."""
from contextlib import closing
import json
import sqlite3
from uuid import uuid4

import pytest

from plotloom.persistence.project import autopilot_bindings as bindings
from plotloom.persistence.project.autopilot_profile_construction import _ProfileConstruction
from tests.autopilot_profile_fixtures import seed_profile_graph


class ObservedConnection:
    """Observe existing policy fetches without changing cursor/transaction lifetime."""
    def __init__(self, connection, commit):
        self.connection, self.commit = connection, commit
        self.observations = []
        self.committed = False

    def execute(self, sql, values=()):
        if sql.startswith('SELECT * FROM "v2_source_outline_candidates"') and not self.committed:
            # The attempt helper has returned; commit before the creative branch's
            # later policy SELECT. No extra read, cursor close or transaction.
            self.commit()
            self.committed = True
        cursor = self.connection.execute(sql, values)
        if sql.startswith(("SELECT project_id,policy FROM", "SELECT policy FROM")):
            return ObservedPolicyCursor(cursor, self.observations)
        return cursor


class ObservedPolicyCursor:
    def __init__(self, cursor, observations):
        self.cursor, self.observations = cursor, observations

    @property
    def description(self):
        return self.cursor.description

    def fetchone(self):
        row = self.cursor.fetchone()
        self.observations.append(row[-1] if row else None)
        return row


@pytest.mark.parametrize("held_cursor", [False, True])
@pytest.mark.parametrize("caller_transaction", [False, True])
@pytest.mark.parametrize("change", ["unrelated", "invalid-profile", "malformed-json"])
def test_policy_drift_matches_public_observations_without_forcing_visibility(
        tmp_path, held_cursor, caller_transaction, change):
    results = []
    # Same IDs and bytes on independent disposable databases make traces exact.
    second_run, second_project = str(uuid4()), str(uuid4())
    for private in (False, True):
        path = tmp_path / f"{private}.sqlite3"
        with closing(sqlite3.connect(path)) as setup:
            assert setup.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
            graph = seed_profile_graph(setup)
            seed_profile_graph(setup, run_id=second_run, project_id=second_project)
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as reader, closing(sqlite3.connect(path)) as writer:
            original = writer.execute("SELECT policy FROM v2_autopilot_runs WHERE id=?", (graph.run_id,)).fetchone()[0]
            value = json.loads(original)
            if change == "unrelated":
                value["maxJobs"] += 1
            elif change == "invalid-profile":
                value["executorBinding"]["model"] = "sk-proj-privatecredential"
            changed = "{" if change == "malformed-json" else json.dumps(value)

            def commit():
                writer.execute("UPDATE v2_autopilot_runs SET policy=? WHERE id=?", (changed, graph.run_id))
                writer.commit()

            if caller_transaction:
                reader.execute("BEGIN")
            active = reader.execute("SELECT policy FROM v2_autopilot_runs") if held_cursor else None
            if active is not None:
                assert active.fetchone() is not None  # Leave another row unconsumed.
            trace, before = [], reader.total_changes
            reader.set_trace_callback(trace.append)
            observed = ObservedConnection(reader, commit)
            kwargs = {"run_id": graph.run_id, "operation_key": "outline"}
            validate = bindings.assert_checkpoint_binding
            if private:
                validate = bindings._assert_checkpoint_binding
                kwargs["profile_construction"] = _ProfileConstruction()
            try:
                result = ("return", validate(observed, graph.project_id, "prepared", graph.evidence, **kwargs))
            except Exception as error:
                result = ("error", type(error), str(error))
            finally:
                reader.set_trace_callback(None)
            assert observed.committed
            assert reader.total_changes == before
            assert reader.in_transaction is caller_transaction
            assert writer.execute("SELECT policy FROM v2_autopilot_runs WHERE id=?", (graph.run_id,)).fetchone()[0] == changed
            results.append((observed.observations, trace, result))
            if active is not None:
                active.close()
            reader.rollback()
    assert results[0] == results[1]
    assert len(results[0][0]) == 2
    if not held_cursor and not caller_transaction:
        assert results[0][0] == [original, changed]
        assert results[0][2][0] == ("return" if change == "unrelated" else "error")
