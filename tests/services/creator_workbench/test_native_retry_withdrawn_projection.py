"""Withdrawn retry authority changes reads, never physical attempt evidence."""
# ruff: noqa: F811 -- Imported pytest fixture is injected by argument name.
from contextlib import closing
from copy import deepcopy

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
from tests.services.creator_workbench.test_text_content_correction import _failed_outline_fixture
from tests.test_autopilot_view_checkpoints import render, view_context  # noqa: F401


@pytest.mark.parametrize("kind,limit,stopped,initial", [
    ("runtime", 0, True, "exhausted"),
    ("runtime", 1, False, "retry_pending"),
    ("unknown", 1, False, "retry_pending"),
    ("refusal", 1, True, "stopped"),
])
def test_cancelled_failure_reads_stopped_without_host_calls(tmp_path, monkeypatch, kind, limit, stopped, initial):
    storage, registry, service, run, calls = _failed_outline_fixture(tmp_path, monkeypatch,
        kind=kind, local_stopped=stopped, limits={"automatic_retry_limit": limit})
    host = registry._codex_exec_test_host
    try:
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            before = store.repository.autopilot.current(run.project_id)
            checkpoint = next(c for c in before.checkpoints if c["operationKey"] == "outline")
            assert checkpoint["retry"]["state"] == initial
            failed = store.repository.autopilot.exec_attempt_for_operation(run.id, "outline")
        cancelled = service.control(run.project_id,
            RunControlRequest(action="cancel", expected_revision=before.revision))
        assert cancelled.state == "cancelled"
        with closing(storage.projects.open(run.project_id)) as store:
            physical = store.repository.autopilot.exec_attempt_for_operation(run.id, "outline")
        if kind != "unknown":
            assert physical == failed  # Terminal cancellation preserves the original failure.
        assert physical.attempt_id == failed.attempt_id and physical.job_id == failed.job_id
        admissions, identities, dispatches = host.admissions, set(host.statuses), tuple(calls)
        def no_host(*_args):
            pytest.fail("withdrawn projection polled or admitted host work")
        monkeypatch.setattr(registry, "codex_exec_status", no_host)
        monkeypatch.setattr(registry, "codex_exec_admit", no_host)
        for _ in range(2):
            with closing(storage.projects.open(run.project_id)) as store:
                observed = store.repository.autopilot.current(run.project_id)
                assert store.repository.autopilot.exec_attempt_for_operation(run.id, "outline") == physical
            actual = next(c for c in observed.checkpoints if c["operationKey"] == "outline")
            assert actual["retry"] == checkpoint["retry"] | {"state": "stopped"}
            assert actual["evidence"] == checkpoint["evidence"]
            assert observed.revision == cancelled.revision and observed.state == "cancelled"
        assert host.admissions == admissions and set(host.statuses) == identities and tuple(calls) == dispatches
    finally:
        service.close()


@pytest.mark.parametrize("disposition", ["cancelled", "taken_over", "stale", "handed_off"])
@pytest.mark.parametrize("exhausted", [False, True])
def test_effective_withdrawn_disposition_preserves_unknown_cost_and_exhaustion(view_context, disposition, exhausted):
    context = view_context
    attempt = transition_exec_attempt(CodexExecAttempt.model_validate(context.attempt.snapshot),
        state="outcome_unknown", execution_failure="transient")
    context.attempt.state = attempt.state
    context.attempt.snapshot = attempt.model_dump(mode="json", by_alias=True)
    checkpoint = context.checkpoints[0]
    checkpoint.state = "outcome_unknown"
    checkpoint.evidence = deepcopy(checkpoint.evidence)
    if exhausted:
        checkpoint.evidence["result"]["executionRetryExhausted"] = True
    context.row.policy = context.row.policy | {"automaticRetryLimit": 1}
    if disposition == "stale":
        context.row.expected_closure = "different from current material"
    else:
        context.row.state = disposition
    saved = deepcopy((context.attempt.snapshot, checkpoint.evidence))
    for _ in range(2):
        view = render(context)
        projected = next(c for c in view.checkpoints if c["operationKey"] == "outline")
        assert view.state == disposition and projected["retry"]["state"] == "stopped"
        assert projected["retry"]["possiblePriorCost"] is True
        assert projected["retry"]["automaticRetryLimit"] == 1
        assert projected["retry"]["automaticRetriesUsed"] == 0
        assert projected["retry"]["predecessorJobIds"] == []
        assert projected["evidence"] == checkpoint.evidence
        assert (context.attempt.snapshot, checkpoint.evidence) == saved
