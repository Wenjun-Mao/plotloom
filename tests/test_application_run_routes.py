"""Real installation transactions fence frozen-profile deletion and run routing."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.project_storage.application_run_routes import ApplicationRunRoute
from plotloom.project_storage.application_store import ApplicationStore
from plotloom.project_storage.format import ProjectStorageCorruptionError


def application(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    store = ApplicationStore(tmp_path)
    store.save_profile('fixture', {'model': 'fixture'}, expected_revision=0)
    return store


def test_pending_reservation_refuses_deletion_then_completion_rebuild_and_reopen(tmp_path):
    store = application(tmp_path)
    route = ApplicationRunRoute('run-1', 'project-1', 'fixture', 'running')
    store.reserve_run_route(route)
    with pytest.raises(InvalidTransitionError, match='nonterminal run'):
        store.delete_text_profile_record('fixture', 1)
    # Failure to confirm cannot erase the pre-project reservation.
    with pytest.raises(ProjectStorageCorruptionError):
        store.confirm_run_route('missing-run', status='running')
    reopened = ApplicationStore(tmp_path)
    assert reopened.project_for_run('run-1') == 'project-1'
    with pytest.raises(InvalidTransitionError):
        reopened.delete_text_profile_record('fixture', 1)
    reopened.replace_run_index([route])
    reopened.discard_pending_run_route('run-1')
    assert reopened.project_for_run('run-1') == 'project-1'
    reopened.confirm_run_route('run-1', status='succeeded')
    reopened.delete_text_profile_record('fixture', 1)
    assert reopened.project_for_run('run-1') == 'project-1'


def test_profile_guard_uses_deletion_connection_and_blocks_competing_reservation(tmp_path, monkeypatch):
    store = application(tmp_path)
    entered, release, attempting = Event(), Event(), Event()
    original = store.run_routes.require_profile_unreferenced

    def held_guard(connection, profile_id):
        assert connection.in_transaction
        original(connection, profile_id)
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(store.run_routes, 'require_profile_unreferenced', held_guard)

    def reserve():
        attempting.set()
        store.reserve_run_route(ApplicationRunRoute('late-run', 'project-1', 'fixture', 'running'))

    with ThreadPoolExecutor(max_workers=2) as workers:
        deletion = workers.submit(store.delete_text_profile_record, 'fixture', 1)
        assert entered.wait(5)
        reservation = workers.submit(reserve)
        assert attempting.wait(5)
        try:
            assert not reservation.done()
        finally:
            release.set()
        deletion.result(timeout=5)
        with pytest.raises(NotFoundError):
            reservation.result(timeout=5)
    assert store.project_for_run('late-run') is None
