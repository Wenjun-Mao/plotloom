"""Event-gated worker/descriptor ownership; no provider or native execution."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Event, Thread
import fcntl
import os

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_service import AutopilotService
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import ProjectAccessLease
from plotloom.project_storage.operational_state import ProjectBusyError
from plotloom.specialist_settings import SpecialistRegistry


def runtime(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    return storage, AutopilotService(storage, SpecialistRegistry(storage.application.root))


def test_concurrent_start_publishes_one_worker_before_thread_start_returns(tmp_path, monkeypatch):
    _storage, service = runtime(tmp_path)
    published, second_attempt, second_published, release = Event(), Event(), Event(), Event()
    workers = []
    class GatedWorker(Thread):
        def start(self):
            workers.append(self)
            if len(workers) == 1:
                published.set()
                assert release.wait(5)
            else:
                second_published.set()
            super().start()
    monkeypatch.setattr("plotloom.autopilot_service.Thread", GatedWorker)
    monkeypatch.setattr(service, "_loop", lambda: service._stop.wait(5))
    def second():
        second_attempt.set()
        service.start()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.start)
            assert published.wait(5)
            other = pool.submit(second)
            assert second_attempt.wait(5)
            second_published.wait(0.1)
            release.set()
            first.result(timeout=5); other.result(timeout=5)
        assert len(workers) == 1
    finally:
        release.set(); service._stop.set()
        for worker in workers:
            worker.join(timeout=5)
        service.close()


def test_concurrent_release_closes_the_exact_descriptor_once(tmp_path, monkeypatch):
    _storage, service = runtime(tmp_path)
    assert service.acquire_controller()
    descriptor = service._descriptor
    entered, second_attempt, second_unlock, release = Event(), Event(), Event(), Event()
    original_flock, original_close = fcntl.flock, os.close
    unlocked, closed = [], []
    def unlock(fd, operation):
        if fd == descriptor and operation == fcntl.LOCK_UN:
            unlocked.append(fd)
            if len(unlocked) == 1:
                entered.set()
                assert release.wait(5)
            else:
                second_unlock.set()
        return original_flock(fd, operation)
    def close(fd):
        if fd == descriptor:
            closed.append(fd)
        return original_close(fd)
    monkeypatch.setattr(fcntl, "flock", unlock)
    monkeypatch.setattr(os, "close", close)
    def second():
        second_attempt.set()
        service.release_controller()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.release_controller)
            assert entered.wait(5)
            other = pool.submit(second)
            assert second_attempt.wait(5)
            second_unlock.wait(0.1)
            release.set()
            first.result(timeout=5); other.result(timeout=5)
        assert unlocked == [descriptor] and closed == [descriptor]
        assert service._descriptor is None
    finally:
        release.set()
        # Use the original primitive only for a still-owned test descriptor.
        if service._descriptor is not None:
            try:
                original_close(service._descriptor)
            except OSError:
                pass
            service._descriptor = None


def test_overlapping_app_lifespans_stop_only_after_final_owner_exits(tmp_path):
    storage, _unused = runtime(tmp_path)
    app = create_project_folder_authoring_app(storage)
    service = app.state.autopilot_service
    first_entered, second_entered, leave_first, leave_second = (Event() for _ in range(4))
    def lifespan(entered, leave):
        with TestClient(app) as client:
            assert client.get("/api/v2/autopilot/controller").status_code == 200
            entered.set()
            assert leave.wait(5)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(lifespan, first_entered, leave_first)
            assert first_entered.wait(5)
            second = pool.submit(lifespan, second_entered, leave_second)
            assert second_entered.wait(5)
            try:
                tracked = service._thread
                leave_first.set(); first.result(timeout=5)
                assert service._thread is tracked and tracked.is_alive()
            finally:
                leave_second.set()
            second.result(timeout=5)
        assert service._thread is None and service._descriptor is None
    finally:
        leave_first.set(); leave_second.set(); service.close()


@pytest.mark.parametrize("phase", ["discover", "inspect"])
def test_real_passive_shared_lease_finishes_before_explicit_reopen(tmp_path, monkeypatch, phase):
    storage, service = runtime(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = store.manifest.project_id, store.home
    storage.projects.close_project(project_id)
    assert (home / ".project-operation.lock").exists()
    observed, exclusive_attempt, transition_finished, release = Event(), Event(), Event(), Event()
    original = ProjectAccessLease.acquire
    holders = []
    def acquire(path, *, mode, **kwargs):
        if mode == "exclusive":
            exclusive_attempt.set()
        lease = original(path, mode=mode, **kwargs)
        if mode == "shared" and kwargs.get("create") is False and not observed.is_set():
            from threading import current_thread
            holders.append((os.getpid(), current_thread().name, phase, lease.descriptor))
            observed.set()
            assert release.wait(5)
        return lease
    monkeypatch.setattr(ProjectAccessLease, "acquire", staticmethod(acquire))
    if phase == "inspect":
        assert service.acquire_controller()
    def observer():
        if phase == "discover":
            service.start()
        else:
            service.step(project_id)
    def reopen():
        try:
            return storage.projects.reopen_project(project_id)
        finally:
            transition_finished.set()
    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"passive-{phase}") as pool:
            observation = pool.submit(observer)
            assert observed.wait(5)
            print({"passive_holder": holders, "site": phase}, flush=True)
            reopened = pool.submit(reopen)
            assert exclusive_attempt.wait(5)
            # The transition must wait for this proven passive holder, not fail
            # its nonblocking OS lease while the observer is admitted.
            try:
                assert not transition_finished.wait(0.1)
            finally:
                release.set()
            observation.result(timeout=5)
            assert reopened.result(timeout=5) >= 1
        assert holders and holders[0][3] >= 0
    finally:
        release.set(); service.close()


def test_pending_transition_blocks_new_passive_reads_until_exclusive_release(tmp_path, monkeypatch):
    storage, _service = runtime(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        home = store.home
    first = ProjectAccessLease.acquire(home, mode="shared", create=False, passive=True)
    gate = first.observation_admission.gate
    waiting_transition, waiting_observer, exclusive_acquired, leave_exclusive, observer_acquired = (Event() for _ in range(5))
    original_wait = gate.condition.wait_for
    def wait(predicate):
        from threading import current_thread
        if current_thread().name == "explicit-transition":
            waiting_transition.set()
        elif current_thread().name == "new-observer":
            waiting_observer.set()
        return original_wait(predicate)
    monkeypatch.setattr(gate.condition, "wait_for", wait)
    errors = []
    def transition():
        try:
            with closing(ProjectAccessLease.acquire(home, mode="exclusive")):
                exclusive_acquired.set()
                assert leave_exclusive.wait(5)
        except BaseException as error:
            errors.append(error)
    def observe():
        try:
            with closing(ProjectAccessLease.acquire(home, mode="shared", create=False, passive=True)):
                observer_acquired.set()
        except BaseException as error:
            errors.append(error)
    writer, reader = Thread(target=transition, name="explicit-transition"), Thread(target=observe, name="new-observer")
    try:
        writer.start(); assert waiting_transition.wait(5)
        reader.start(); assert waiting_observer.wait(5)
        assert not observer_acquired.is_set() and not exclusive_acquired.is_set()
        first.close(); assert exclusive_acquired.wait(5)
        assert not observer_acquired.is_set()
        leave_exclusive.set(); assert observer_acquired.wait(5)
    finally:
        first.close(); leave_exclusive.set()
        writer.join(timeout=5)
        if reader.ident is not None:
            reader.join(timeout=5)
    assert not writer.is_alive() and not reader.is_alive() and not errors


def test_passive_arbitration_preserves_foreground_writer_lease_refusal(tmp_path):
    storage, _service = runtime(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = store.manifest.project_id, store.home
    storage.projects.close_project(project_id)
    with closing(ProjectAccessLease.acquire(home, mode="shared", create=False)):
        with pytest.raises(ProjectBusyError):
            storage.projects.reopen_project(project_id)
    assert storage.projects.reopen_project(project_id) >= 1
