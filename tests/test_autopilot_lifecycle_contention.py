"""A real competing SQLite writer defers exact completed-image adoption."""
import sqlite3
from contextlib import closing

from tests.autopilot_installed_text_fixtures import installed_text_image_environment
from tests.test_autopilot_image_safety import reach
from tests.test_autopilot_images import current


def test_sqlite_writer_contention_keeps_run_and_receipt_then_adopts_without_readmission(
    tmp_path, monkeypatch, installed_text_prefix,
):
    storage, registry, service, view, calls, _text = installed_text_image_environment(
        tmp_path, monkeypatch, installed_text_prefix)
    try:
        before, checkpoint = reach(storage, service, view, "image", "delivered")
        assert before.state == "running" and not before.frames
        with closing(storage.projects.open(view.project_id)) as store:
            home = store.home
            original_attempt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                view.id, checkpoint["operationKey"])
        admissions = registry._codex_exec_test_host.admissions
        old_calls = list(calls)
        # Same cross-process lease failure as the observed foreground control
        # race, with no synthetic provider failure or simulated receipt.
        with closing(sqlite3.connect(home / "project.sqlite3")) as writer:
            writer.execute("BEGIN IMMEDIATE")
            service.step(view.project_id)
            writer.rollback()
        held = current(storage, view)
        assert (held.state, held.revision, held.blocker, held.checkpoints, held.frames) == (
            before.state, before.revision, before.blocker, before.checkpoints, before.frames)
        assert not service._unrecorded_failures
        assert registry._codex_exec_test_host.admissions == admissions and calls == old_calls
        service.step(view.project_id)
        resumed = current(storage, view)
        adopted = next(item for item in resumed.checkpoints if item["operationKey"] == checkpoint["operationKey"])
        assert resumed.state == "running" and resumed.blocker is None and adopted["state"] == "adopted"
        assert len(resumed.frames) == 1 and resumed.frames[0].job_id == checkpoint["evidence"]["jobId"]
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.repository.autopilot.exec_attempt_evidence_for_operation(
                view.id, checkpoint["operationKey"]) == original_attempt
        assert registry._codex_exec_test_host.admissions == admissions and calls == old_calls
    finally:
        service.close()
