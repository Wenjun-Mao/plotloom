"""Controller metadata keeps lifecycle locking, returned evidence and rollback."""

from contextlib import closing, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from threading import RLock
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.contract_identity import new_id, utc_now
from plotloom.exceptions import InvalidTransitionError, LifecycleContentionError
from plotloom.persistence.project.command_transactions import ProjectCommandTransactions
from plotloom.persistence.schema import AutopilotCheckpointRow, AutopilotFrameRow
from plotloom.project_storage import ProjectFolderStorage
from tests.autopilot_fixtures import authority, start_run


@pytest.fixture
def store(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as owned:
        yield owned


def _snapshot(store):
    with store.repository._read() as session:
        row = store.repository.autopilot.row(session, store.manifest.project_id)
        return deepcopy({column.name: getattr(row, column.name) for column in row.__table__.columns}) if row else None


@pytest.mark.parametrize("state", ["running", "waiting", "paused", "blocked", "cancelled", "taken_over", "stale", "awaiting_review"])
def test_claim_changes_only_metadata_and_identical_claim_is_a_noop(store, monkeypatch, state):
    start_run(store)
    owner, project_id = store.repository.autopilot, store.manifest.project_id
    with store.repository._write() as session:
        row = owner.row(session, project_id)
        row.state = state
        row.blocker = {"code": "retained", "message": "Keep existing reconciliation evidence."}
    before = _snapshot(store)
    changed_at = utc_now()
    monkeypatch.setattr("plotloom.persistence.project.autopilot.utc_now", lambda: changed_at)
    view = owner.claim(project_id, "next-controller")
    changed = _snapshot(store)
    assert view.revision == before["revision"] + 1
    assert changed["claim"] == "next-controller"
    assert changed["updated_at"] == changed_at.replace(tzinfo=None)
    assert {key: value for key, value in changed.items() if key not in {"claim", "revision", "updated_at"}} == {
        key: value for key, value in before.items() if key not in {"claim", "revision", "updated_at"}
    }
    unchanged = owner.claim(project_id, "next-controller")
    assert (unchanged.revision, unchanged.state) == (view.revision, view.state)
    assert _snapshot(store) == changed


def test_claim_keeps_one_return_closure_and_next_read_is_fresh(store, monkeypatch):
    start_run(store)
    from plotloom.persistence.project import autopilot, autopilot_closure

    original, calls = autopilot.material_closure, []

    def returned_closure(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(autopilot, "material_closure", returned_closure)
    monkeypatch.setattr(autopilot_closure, "material_closure", lambda *_args, **_kwargs: pytest.fail("claim used manual material comparison"))
    owner, project_id = store.repository.autopilot, store.manifest.project_id
    assert owner.claim(project_id, "next-controller").state == "running"
    assert len(calls) == 1
    with store.repository._write() as session:
        owner.row(session, project_id).expected_closure = "0" * 64
    assert owner.current(project_id).state == "stale"
    assert len(calls) == 2
    assert owner.claim(project_id, "late-reconciliation").state == "stale"
    assert len(calls) == 3


@pytest.mark.parametrize("condition", ["missing", "recovered", "handed_off", "recovered_and_handed_off"])
def test_refused_claims_keep_order_and_make_no_changes(store, monkeypatch, condition):
    owner, project_id = store.repository.autopilot, store.manifest.project_id
    if condition != "missing":
        run = start_run(store)
        with store.repository._write() as session:
            row = owner.row(session, project_id)
            row.expected_closure = "0" * 64  # UI staleness cannot hide durable handoff.
            if "handed_off" in condition:
                row.state = "handed_off"
        if "recovered" in condition:
            owner.recovered_run_ids = lambda: {run.id}
    before = _snapshot(store)
    monkeypatch.setattr(owner, "view_in_session", lambda *_: pytest.fail("refused claim reached its view"))
    expected = "missing" if condition == "missing" else "portable restored" if "recovered" in condition else "completed human handoff"
    with pytest.raises(InvalidTransitionError, match=expected):
        owner.claim(project_id, "forbidden-controller")
    assert _snapshot(store) == before


@pytest.mark.parametrize("defect", ["policy", "checkpoint", "frame", "material"])
def test_return_validation_failure_rolls_back_claim_metadata(store, monkeypatch, defect):
    run = start_run(store)
    owner, project_id = store.repository.autopilot, store.manifest.project_id
    if defect == "policy":
        with store.repository._write() as session:
            owner.row(session, project_id).policy = {}
    elif defect == "checkpoint":
        with store.repository._write() as session:
            now = utc_now()
            session.add(AutopilotCheckpointRow(id=new_id(), run_id=run.id, project_id=project_id,
                operation_key="malformed-return", revision=1, state="prepared", evidence={}, created_at=now, updated_at=now))
    elif defect == "frame":
        original = Session.scalars

        def malformed_frame(session, statement, *args, **kwargs):
            if statement.column_descriptions[0].get("entity") is AutopilotFrameRow:
                return SimpleNamespace(all=lambda: [SimpleNamespace(frame={})])
            return original(session, statement, *args, **kwargs)

        monkeypatch.setattr(Session, "scalars", malformed_frame)
    else:
        def unreadable(*_args):
            raise OSError("material storage unavailable")
        monkeypatch.setattr("plotloom.persistence.project.autopilot.material_closure", unreadable)
    before = _snapshot(store)
    with pytest.raises(OSError if defect == "material" else ValidationError):
        owner.claim(project_id, "must-roll-back")
    assert _snapshot(store) == before


@pytest.mark.parametrize("command", ["manual", "autopilot"])
@pytest.mark.parametrize("rollback", [False, True])
def test_nested_claim_joins_command_session_and_outer_transaction(store, command, rollback):
    run = start_run(store)
    repository, project_id = store.repository, store.manifest.project_id
    before = _snapshot(store)
    context = repository.manual_command() if command == "manual" else repository.autopilot_command(authority(run))

    def exercise():
        with context as session:
            with repository._controller_claim_write() as claim_session:
                assert claim_session is session
            repository.autopilot.claim(project_id, "joined-controller")
            assert repository.autopilot.current(project_id).revision == before["revision"] + 1
            with repository.engine.connect() as independent:
                assert independent.exec_driver_sql("SELECT claim FROM v2_autopilot_runs").scalar_one() == before["claim"]
            if rollback:
                raise RuntimeError("outer command rollback")

    if rollback:
        with pytest.raises(RuntimeError, match="outer command rollback"):
            exercise()
        assert _snapshot(store) == before
    else:
        exercise()
        after = _snapshot(store)
        assert after["claim"] == "joined-controller"
        assert after["revision"] == before["revision"] + (2 if command == "autopilot" else 1)
        assert after["expected_closure"] == before["expected_closure"]


def test_manual_command_still_detects_material_mutation_around_claim(store):
    start_run(store)
    repository, project_id = store.repository, store.manifest.project_id
    before = _snapshot(store)
    with repository.manual_command() as session:
        repository.autopilot.claim(project_id, "joined-controller")
        project = repository._project_access.rows.project(session, project_id)
        project.brief = project.brief | {"title": "Changed by the enclosing manual command"}
    after = _snapshot(store)
    assert after["state"] == "taken_over"
    assert after["revision"] == before["revision"] + 2
    assert after["blocker"]["code"] == "manual_takeover"


def test_claim_retains_sqlite_lifecycle_contention_error_and_no_change(store):
    start_run(store)
    repository, project_id = store.repository, store.manifest.project_id
    before = _snapshot(store)
    with repository.engine.connect() as held:
        held.exec_driver_sql("BEGIN IMMEDIATE")
        with pytest.raises(LifecycleContentionError) as caught:
            repository.autopilot.claim(project_id, "contending-controller")
        assert caught.value.retry_after_seconds == repository._bootstrap_retry_after_seconds
        held.rollback()
    assert _snapshot(store) == before


@pytest.mark.parametrize("fail", [False, True])
def test_non_sqlite_claim_uses_normal_write_lease(fail):
    events, session = [], object()

    @contextmanager
    def begin():
        events.append("begin")
        try:
            yield session
        except RuntimeError:
            events.append("rollback")
            raise
        else:
            events.append("commit")

    owner = SimpleNamespace(_command_context=ContextVar("non-sqlite-claim", default=None),
        _sessions=SimpleNamespace(begin=begin), _write_lock=RLock(),
        engine=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        _bootstrap_retry_after_seconds=3, _is_sqlite_lock_contention=lambda _: pytest.fail("SQLite-only contention classifier"))

    def exercise():
        with ProjectCommandTransactions._controller_claim_write(owner) as actual:
            assert actual is session
            if fail:
                raise RuntimeError("non-SQLite failure")

    if fail:
        with pytest.raises(RuntimeError, match="non-SQLite failure"):
            exercise()
    else:
        exercise()
    assert events == ["begin", "rollback" if fail else "commit"]


def test_noncontention_operational_failure_propagates_and_rolls_back(store, monkeypatch):
    start_run(store)
    before = _snapshot(store)
    failure = OperationalError("material read", {}, OSError("storage unavailable"))

    def unavailable(*_args):
        raise failure

    monkeypatch.setattr("plotloom.persistence.project.autopilot.material_closure", unavailable)
    with pytest.raises(OperationalError) as caught:
        store.repository.autopilot.claim(store.manifest.project_id, "must-roll-back")
    assert caught.value is failure
    assert _snapshot(store) == before
