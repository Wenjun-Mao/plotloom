"""Admitted image preparation owns the truthful active phase atomically."""

from contextlib import closing

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.persistence.project.autopilot import AutopilotPersistence
from tests.autopilot_installed_text_fixtures import installed_text_image_environment
from tests.test_autopilot_images import current


def references_ready(storage, service, view):
    for _ in range(30):
        service.step(view.project_id)
        retained = current(storage, view)
        refs = [
            item
            for item in retained.checkpoints
            if item["evidence"]["owner"] in {"character-reference", "art-reference"}
        ]
        # The fixture has exactly one Cast subject and one Art scene.
        if len(refs) == 2 and all(item["state"] == "adopted" for item in refs):
            return retained
        assert retained.state in {"running", "waiting"}, retained.blocker
    raise AssertionError("fixture references did not settle")


def test_first_frame_prepared_sent_restart_delivery_and_pause_keep_exact_phase_identity(
    tmp_path, monkeypatch, installed_text_prefix
):
    storage, registry, service, view, calls, _text = installed_text_image_environment(
        tmp_path, monkeypatch, installed_text_prefix
    )
    resumed = None
    try:
        retained = references_ready(storage, service, view)
        assert retained.phase == "references" and not retained.frames
        service.step(view.project_id)
        prepared = current(storage, view)
        checkpoint = next(
            item
            for item in prepared.checkpoints
            if item["evidence"]["owner"] == "image"
        )
        assert (
            checkpoint["state"] == "prepared"
            and prepared.phase == "first-frames"
            and not prepared.frames
        )
        assert len(calls) == 2
        service.step(view.project_id)
        sent = current(storage, view)
        assert sent.phase == "first-frames" and not sent.frames and len(calls) == 3
        service.close()
        resumed = AutopilotService(storage, registry)
        assert resumed.acquire_controller()
        resumed.step(view.project_id)
        delivered = current(storage, view)
        assert delivered.phase == "first-frames" and not delivered.frames
        assert (
            next(
                item for item in delivered.checkpoints if item["id"] == checkpoint["id"]
            )["evidence"]["jobId"]
            == calls[-1]
        )
        resumed.control(
            view.project_id,
            RunControlRequest(expected_revision=delivered.revision, action="pause"),
        )
        resumed.step(view.project_id)
        paused = current(storage, view)
        assert (
            paused.state == "paused"
            and paused.phase == "first-frames"
            and not paused.frames
        )
        assert len(calls) == len(set(calls)) == 3
    finally:
        service.close()
        if resumed:
            resumed.close()


def test_waiting_first_frame_restart_keeps_prepared_identity_without_resend(
    tmp_path, monkeypatch, installed_text_prefix
):
    from plotloom.image_job_contracts import ImageJobError

    storage, registry, service, view, calls, _text = installed_text_image_environment(
        tmp_path, monkeypatch, installed_text_prefix
    )
    resumed = None
    try:
        references_ready(storage, service, view)
        service.step(view.project_id)
        prepared = current(storage, view)
        checkpoint = next(
            item
            for item in prepared.checkpoints
            if item["evidence"]["owner"] == "image"
        )

        admit = registry.codex_exec_admit

        def occupied(attempt):
            if attempt.domain == "image":
                raise ImageJobError("image_dispatch_busy", "fixture occupied image role")
            return admit(attempt)

        with monkeypatch.context() as busy:
            busy.setattr(registry, "codex_exec_admit", occupied)
            service.step(view.project_id)
            waiting = current(storage, view)
            assert (
                waiting.state == "waiting"
                and waiting.phase == "first-frames"
                and not waiting.frames
            )
            waiting_checkpoint = next(
                item for item in waiting.checkpoints if item["id"] == checkpoint["id"]
            )
            assert waiting_checkpoint["state"] == "sent"
            attempt_id = waiting_checkpoint["evidence"]["executorAttemptId"]
            service.close()
            resumed = AutopilotService(storage, registry)
            assert resumed.acquire_controller()
            resumed.step(view.project_id)
            retained = current(storage, view)
            assert retained.state == "waiting" and retained.phase == "first-frames"
            retained_checkpoint = next(
                item for item in retained.checkpoints if item["id"] == checkpoint["id"]
            )
            assert retained_checkpoint["state"] == "sent"
            assert retained_checkpoint["evidence"]["jobId"] == checkpoint["evidence"]["jobId"]
            assert retained_checkpoint["evidence"]["executorAttemptId"] == attempt_id
            assert len(calls) == 2
        resumed.step(view.project_id)
        sent = current(storage, view)
        assert sent.phase == "first-frames" and not sent.frames
        assert calls[-1] == checkpoint["evidence"]["jobId"] and len(calls) == 3
    finally:
        service.close()
        if resumed:
            resumed.close()


def test_phase_failure_rolls_back_prepared_job_checkpoint_and_can_retry(
    tmp_path, monkeypatch, installed_text_prefix
):
    storage, _registry, service, view, calls, _text = installed_text_image_environment(
        tmp_path, monkeypatch, installed_text_prefix
    )
    try:
        before = references_ready(storage, service, view)
        real_progress = AutopilotPersistence.progress

        def fail_after_phase(self, phase):
            real_progress(self, phase)
            if phase == "first-frames":
                raise RuntimeError("injected prepared-phase rollback")

        with monkeypatch.context() as fault:
            fault.setattr(AutopilotPersistence, "progress", fail_after_phase)
            with pytest.raises(RuntimeError, match="prepared-phase rollback"):
                service.step(view.project_id)
        retained = current(storage, view)
        assert (
            retained.phase == before.phase == "references"
            and retained.checkpoints == before.checkpoints
        )
        with (
            closing(storage.projects.open(view.project_id)) as store,
            store.repository.engine.connect() as connection,
        ):
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM v2_image_jobs"
                ).scalar()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM v2_production_units"
                ).scalar()
                == 0
            )
        assert len(calls) == 2
        service.step(view.project_id)
        retry = current(storage, view)
        assert retry.phase == "first-frames" and not retry.frames
        assert (
            len(
                [
                    item
                    for item in retry.checkpoints
                    if item["evidence"]["owner"] == "image"
                ]
            )
            == 1
        )
        assert len(calls) == 2
    finally:
        service.close()
