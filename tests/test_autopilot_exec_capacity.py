"""Typed capacity refusal is one durable exact-attempt admission permission."""
from contextlib import closing
import json
import sqlite3

import pytest

from plotloom.autopilot_exec import reconcile_codex_exec
from plotloom.codex_exec_contracts import CodexExecHostStatus
from plotloom.image_job_contracts import ImageJobError
from tests.test_autopilot_exec_staged import prepared


@pytest.mark.parametrize("second_reply", ["missing", "lost", "found"])
@pytest.mark.parametrize("blocker", [None, "unrelated_wait"])
def test_exact_capacity_permission_is_committed_before_retry_and_never_reused(
    tmp_path, monkeypatch, second_reply, blocker
):
    with prepared(tmp_path, monkeypatch) as (storage, registry, service, store, view, _checkpoint, attempt, kwargs, _calls):
        admissions = []
        host = registry._codex_exec_test_host

        def admit(value):
            admissions.append(value)
            if len(admissions) == 1:
                return CodexExecHostStatus(state="not_found", capacityDeferred=True)
            assert len(admissions) == 2 and value.attempt_id == attempt.attempt_id
            # A separate SQLite connection can see the spend before this RPC.
            # This fails for a pop that remains in an outer uncommitted command.
            with sqlite3.connect(store.repository.engine.url.database) as connection:
                raw = connection.execute("SELECT evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key='outline'",
                    (str(view.id),)).fetchone()[0]
            assert "executorAdmissionDeferral" not in json.loads(raw)
            if second_reply == "lost":
                raise OSError("lost second admission acknowledgement")
            if second_reply == "found":
                status = CodexExecHostStatus(state="spawn_intent", attempt=value)
                host.statuses[str(value.attempt_id)] = status
                return status
            return CodexExecHostStatus(state="not_found")

        monkeypatch.setattr(registry, "codex_exec_admit", admit)

        def cycle():
            # Reopen for every step so the permission must survive persistence.
            with closing(storage.projects.open(view.project_id)) as reopened:
                current = reopened.repository.autopilot.current(view.project_id)
                checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
                return reconcile_codex_exec(reopened, registry, current, service.claim, checkpoint,
                    domain="text", **kwargs)

        with pytest.raises(ImageJobError, match="capacity"):
            cycle()
        if blocker:
            store.repository.autopilot.blocker(view.project_id, code=blocker, message="other wait", waiting=True)
        if second_reply == "lost":
            with pytest.raises(OSError, match="second admission"):
                cycle()
        else:
            cycle()
        cycle()
        if second_reply == "found":
            host.statuses.clear()
            cycle()
        retained = store.repository.autopilot.exec_attempt_for_operation(view.id, "outline")
        assert retained.state == "outcome_unknown"
        assert admissions == [admissions[0], admissions[0]]
        current = store.repository.autopilot.current(view.project_id)
        checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
        assert "executorAdmissionDeferral" not in checkpoint["evidence"]
