"""Final dispatch admission and background failure isolation, fake transport only."""
from contextlib import closing
from threading import Event

import pytest
from sqlalchemy.exc import SQLAlchemyError

from plotloom.autopilot_contracts import LaunchRequest, RunControlRequest
from plotloom.exceptions import InvalidTransitionError
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_package_publication import publish_package
from tests.autopilot_controller_fixtures import environment


@pytest.mark.parametrize("stage", ["outline", "bridge-intent"])
@pytest.mark.parametrize("action", ["pause", "takeover", "cancel", "brief-edit", "pin-change", "binding-change"])
def test_current_authority_required_at_final_send(tmp_path, monkeypatch, stage, action):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch)
    try:
        assert service.acquire_controller()
        for _ in range(40):
            service.step(view.project_id)
            with closing(storage.projects.open(view.project_id)) as store:
                current = store.repository.autopilot.current(view.project_id)
            checkpoint = next((item for item in current.checkpoints if item["operationKey"] == stage), None)
            if checkpoint is not None:
                break
        assert checkpoint["state"] == "prepared"
        original_dispatch = registry.dispatch

        def dispatch(role, **kwargs):
            if action == "binding-change":
                with registry.lock():
                    data = registry._read()
                    data["settings"]["image"]["taskId"] = "00000000-0000-4000-8000-000000000001"
                    registry._write(data)
            else:
                before_send = kwargs["before_send"]

                def intervene():
                    if action in {"pause", "takeover", "cancel"}:
                        service.control(view.project_id, RunControlRequest(expected_revision=current.revision, action=action))
                    elif action == "brief-edit":
                        with closing(storage.projects.open(view.project_id)) as store:
                            project = store.project()
                            store.update_brief(project.brief.model_copy(update={"synopsis": project.brief.synopsis + "调整"}), expected_revision=project.revision)
                    else:
                        from plotloom.creative_handoff_exchange import CreativeHandoffExchange
                        monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda *_: {"upstreamRevision": "d" * 40})
                    before_send()

                kwargs["before_send"] = intervene
            return original_dispatch(role, **kwargs)

        monkeypatch.setattr(registry, "dispatch", dispatch)
        original_calls = list(calls)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            result = store.repository.autopilot.current(view.project_id)
            retained = next(item for item in result.checkpoints if item["operationKey"] == stage)
        assert retained["state"] == "prepared"
        assert retained["evidence"]["jobId"] == checkpoint["evidence"]["jobId"]
        assert calls == original_calls
        assert not registry.view()["busy"]
    finally:
        service.close()


def test_unsafe_controller_lock_keeps_supervisor_alive_without_claim(tmp_path, monkeypatch):
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch)
    refused = Event()
    def acquire():
        refused.set()
        raise InvalidTransitionError("unsafe controller lease")
    monkeypatch.setattr(service, "acquire_controller", acquire)
    service.interval_seconds = 0.02
    try:
        service.start()
        assert refused.wait(5)
        service.close()
        assert service.controller_blocker["code"] == "controller_storage_unavailable"
        with closing(storage.projects.open(view.project_id)) as store:
            assert not store.repository.autopilot.current(view.project_id).checkpoints
        assert not calls
    finally:
        service.close()


@pytest.mark.parametrize("closed,has_run", [(False, False), (True, False), (True, True)])
def test_controller_inspects_idle_or_closed_folders_without_writing(tmp_path, monkeypatch, closed, has_run):
    import sqlite3
    from plotloom.autopilot_service import AutopilotService
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    from plotloom.project_storage import ProjectFolderStorage
    from plotloom.specialist_settings import SpecialistRegistry

    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home, database = store.manifest.project_id, store.home, store.database_path
    service = AutopilotService(storage, SpecialistRegistry(storage.application.root))
    if has_run:
        from tests.autopilot_controller_fixtures import PIN
        from tests.test_specialist_settings import configured
        registry, _settings = configured(storage.application.root)
        service = AutopilotService(storage, registry)
        from plotloom.creative_handoff_exchange import CreativeHandoffExchange
        monkeypatch.setattr(CreativeHandoffExchange, "_pinned_execution", staticmethod(lambda _: PIN))
        view = service.launch(project_id, LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic"))
        service.control(project_id, RunControlRequest(expected_revision=view.revision, action="cancel"))
    if closed:
        storage.projects.close_project(project_id)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode=DELETE").fetchone() == ("delete",)
    lock_path = home / ".project-operation.lock"
    lock_path.unlink()
    original_bytes = database.read_bytes()
    monkeypatch.setattr(storage.projects, "open", lambda *_: pytest.fail("idle/closed scan cannot acquire editing admission"))
    try:
        assert service.acquire_controller()
        service.step(project_id)
        service._record_failure(project_id, code="controller_failure", message="fixture failure")
        assert database.read_bytes() == original_bytes
        assert not lock_path.exists()
        assert not database.with_name(database.name + "-wal").exists()
        assert not database.with_name(database.name + "-shm").exists()
        assert not service._unrecorded_failures
    finally:
        service.close()


def test_controller_observes_normal_closed_wal_folder_with_retained_lock_without_mutation(tmp_path, monkeypatch):
    import sqlite3
    from plotloom.autopilot_service import AutopilotService
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    from plotloom.project_storage import ProjectFolderStorage
    from plotloom.specialist_settings import SpecialistRegistry

    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home, database = store.manifest.project_id, store.home, store.database_path
    storage.projects.close_project(project_id)
    lock_path = home / ".project-operation.lock"
    assert lock_path.is_file()
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    before = {path.relative_to(home): path.read_bytes() for path in home.rglob("*") if path.is_file()}
    service = AutopilotService(storage, SpecialistRegistry(storage.application.root))
    monkeypatch.setattr(storage.projects, "open", lambda *_: pytest.fail("closed observation cannot acquire editing admission"))
    try:
        assert service.acquire_controller()
        assert len(storage.projects.discover(passive=True)) == 1
        service.step(project_id)
        service._record_failure(project_id, code="controller_failure", message="fixture failure")
        assert {path.relative_to(home): path.read_bytes() for path in home.rglob("*") if path.is_file()} == before
        assert not service._unrecorded_failures
    finally:
        service.close()


@pytest.mark.parametrize("foreign", [False, True])
def test_crash_orphan_reclaims_only_original_static_bytes(tmp_path, foreign):
    package = tmp_path / "job" / "package"
    digest = "a" * 64
    orphan = package.parent / f".package-{digest}-{'b' * 32}"
    orphan.mkdir(parents=True)
    files = {"request.json": b"original", "inputs/source.json": b"source"}
    (orphan / "request.json").write_bytes(b"foreign" if foreign else files["request.json"])
    def write_once(path, content):
        with path.open("xb") as stream:
            stream.write(content)
    if foreign:
        with pytest.raises(CreativeHandoffError, match="unknown or changed"):
            publish_package(package, digest=digest, files=files, write_once=write_once)
        assert orphan.exists() and not package.exists()
    else:
        publish_package(package, digest=digest, files=files, write_once=write_once)
        assert not orphan.exists()
        assert all((package / name).read_bytes() == content for name, content in files.items())


@pytest.mark.parametrize("failure", [OSError("disk full"), SQLAlchemyError("database unavailable"), RuntimeError("unexpected owner failure")])
def test_background_storage_failure_preserves_job_and_other_project_progress(tmp_path, monkeypatch, failure):
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    second_progress = Event()
    with closing(storage.projects.open(view.project_id)) as store:
        brief = store.project().brief
    with closing(storage.projects.create(brief)) as store:
        other_id = store.manifest.project_id
    service.launch(other_id, LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic"))
    original_advance = service.controller.advance

    def advance(store, current, claim):
        if current.project_id == other_id:
            if not second_progress.is_set():
                original_advance(store, current, claim)
                second_progress.set()
            return
        if current.state == "blocked":
            return
        # Preparation is durably committed before static publication fails.
        exchange_type = type(store.creative_handoff_exchange())
        monkeypatch.setattr(exchange_type, "write_package", lambda *_: (_ for _ in ()).throw(failure))
        original_advance(store, current, claim)

    monkeypatch.setattr(service.controller, "advance", advance)
    service.interval_seconds = 0.02
    blocked = Event()
    original_record = service._record_failure
    def record(project_id, **kwargs):
        original_record(project_id, **kwargs)
        blocked.set()
    monkeypatch.setattr(service, "_record_failure", record)
    try:
        service.start()
        assert second_progress.wait(5)
        # Wake after the second source adoption, allowing the first project to
        # hit its prepared-package boundary regardless of discovery order.
        service._wake.set()
        assert blocked.wait(5)
        assert service._thread.is_alive()
        with closing(storage.projects.open(view.project_id)) as store:
            result = store.repository.autopilot.current(view.project_id)
        expected = "controller_failure" if isinstance(failure, RuntimeError) else "storage_failure"
        assert result.state == "blocked" and result.blocker["code"] == expected
        assert next(item for item in result.checkpoints if item["operationKey"] == "outline")["state"] == "prepared"
        with closing(storage.projects.open(other_id)) as store:
            assert store.source_outline_state().source is not None
        assert not calls
    finally:
        service.close()
