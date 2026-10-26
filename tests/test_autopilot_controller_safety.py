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


def _current(storage, view):
    with closing(storage.projects.open(view.project_id)) as store:
        return store.repository.autopilot.current(view.project_id)


@pytest.mark.parametrize("readiness_state", ["not_authenticated", "unavailable"])
def test_launch_requires_usable_cli_login_before_creating_frozen_run(tmp_path, monkeypatch, readiness_state):
    from plotloom.autopilot_contracts import LaunchRequest
    from plotloom.autopilot_service import AutopilotService
    from plotloom.story_workloads import FIXED_CHINESE_BRIEF
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from plotloom.image_job_contracts import ImageJobError
    from plotloom.codex_exec_contracts import CodexExecReadiness
    from plotloom.project_storage import ProjectFolderStorage
    from tests.autopilot_controller_fixtures import PIN
    from tests.codex_exec_fixtures import install_profile
    from tests.test_specialist_settings import configured

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id = store.manifest.project_id
    registry, _settings = configured(storage.application.root)
    install_profile(registry)
    registry.host_client.codex_exec_readiness = lambda: CodexExecReadiness(state=readiness_state)
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda *_: PIN)
    service = AutopilotService(storage, registry)
    request = LaunchRequest(
        expected_brief_revision=1,
        render_style="realistic",
        art_render_style="realistic",
    )
    try:
        with pytest.raises(ImageJobError) as error:
            service.launch(project_id, request)
        assert error.value.code == "codex_exec_not_ready"
        with closing(storage.projects.open(project_id)) as store:
            assert store.repository.autopilot.current(project_id) is None
    finally:
        service.close()


@pytest.mark.parametrize("stage", ["outline", "bridge-intent"])
@pytest.mark.parametrize("drift", ["pin", "profile"])
def test_frozen_cli_configuration_rechecked_at_final_spawn_gate(tmp_path, monkeypatch, stage, drift):
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from plotloom import autopilot_text_controller

    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=True)
    try:
        assert service.acquire_controller()
        for _ in range(80):
            service.step(view.project_id)
            with closing(storage.projects.open(view.project_id)) as store:
                current = store.repository.autopilot.current(view.project_id)
            checkpoint = next((item for item in current.checkpoints if item["operationKey"] == stage), None)
            if checkpoint is not None and checkpoint["state"] == "prepared":
                break
        assert checkpoint is not None and checkpoint["state"] == "prepared"
        calls_before = list(calls)
        admissions_before = registry._codex_exec_test_host.admissions
        original_gate = autopilot_text_controller.assert_frozen_execution
        gate_calls = 0

        def intervene_at_final_gate(store, owner_registry, policy):
            nonlocal gate_calls
            gate_calls += 1
            if gate_calls == 2:
                if drift == "pin":
                    monkeypatch.setattr(
                        CreativeHandoffExchange,
                        "current_execution_pin",
                        lambda *_: {"upstreamRevision": "d" * 40},
                    )
                else:
                    profile = owner_registry.codex_exec_profile()
                    monkeypatch.setattr(
                        owner_registry,
                        "codex_exec_profile",
                        lambda: profile.model_copy(update={"model": "changed-at-final-gate"}),
                    )
            return original_gate(store, owner_registry, policy)

        monkeypatch.setattr(autopilot_text_controller, "assert_frozen_execution", intervene_at_final_gate)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            result = store.repository.autopilot.current(view.project_id)
            retained = next(item for item in result.checkpoints if item["operationKey"] == stage)
            attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                result.id, retained["operationKey"]
            )
        assert result.state == "blocked" and result.blocker["code"] == "contract_blocked"
        assert retained["state"] == "prepared"
        assert retained["evidence"]["jobId"] == checkpoint["evidence"]["jobId"]
        assert calls == calls_before
        assert registry._codex_exec_test_host.admissions == admissions_before
        assert attempt is None
    finally:
        service.close()


def test_lost_cli_login_readiness_does_not_reserve_or_admit_prepared_job(tmp_path, monkeypatch):
    from plotloom.codex_exec_contracts import CodexExecReadiness

    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=True)
    try:
        assert service.acquire_controller()
        for _ in range(80):
            service.step(view.project_id)
            current = _current(storage, view)
            checkpoint = next((item for item in current.checkpoints if item["operationKey"] == "outline"), None)
            if checkpoint is not None and checkpoint["state"] == "prepared":
                break
        assert checkpoint is not None and checkpoint["state"] == "prepared"

        admissions_before = registry._codex_exec_test_host.admissions
        calls_before = list(calls)
        registry.host_client.codex_exec_readiness = lambda: CodexExecReadiness(state="not_authenticated")
        service.step(view.project_id)

        current = _current(storage, view)
        retained = next(item for item in current.checkpoints if item["operationKey"] == "outline")
        with closing(storage.projects.open(view.project_id)) as store:
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                current.id, "outline"
            )
        assert current.state == "blocked" and current.blocker["code"] == "codex_exec_not_ready"
        assert retained["state"] == "prepared" and retained["evidence"].get("executorAttemptId") is None
        assert attempt is None and receipt is None
        assert registry._codex_exec_test_host.admissions == admissions_before
        assert calls == calls_before
    finally:
        service.close()


@pytest.mark.parametrize("stage", ["outline", "bridge-intent"])
@pytest.mark.parametrize("action", ["pause", "takeover", "cancel"])
def test_stopped_run_does_not_admit_prepared_cli_job(tmp_path, monkeypatch, stage, action):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=True)
    try:
        assert service.acquire_controller()
        for _ in range(80):
            service.step(view.project_id)
            current = _current(storage, view)
            checkpoint = next((item for item in current.checkpoints if item["operationKey"] == stage), None)
            if checkpoint is not None and checkpoint["state"] == "prepared":
                break
        assert checkpoint is not None and checkpoint["state"] == "prepared"
        calls_before = list(calls)
        admissions_before = registry._codex_exec_test_host.admissions
        stopped = service.control(
            view.project_id,
            RunControlRequest(expected_revision=current.revision, action=action),
        )
        service.step(view.project_id)
        result = _current(storage, view)
        assert result.state == {"pause": "paused", "takeover": "taken_over", "cancel": "cancelled"}[action]
        assert next(item for item in result.checkpoints if item["operationKey"] == stage)["state"] == "prepared"
        assert calls == calls_before
        assert registry._codex_exec_test_host.admissions == admissions_before
        assert stopped.revision >= current.revision
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
    from plotloom.story_workloads import FIXED_CHINESE_BRIEF
    from plotloom.project_storage import ProjectFolderStorage
    from plotloom.specialist_settings import SpecialistRegistry

    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home, database = store.manifest.project_id, store.home, store.database_path
    service = AutopilotService(storage, SpecialistRegistry(storage.application.root))
    if has_run:
        from tests.autopilot_controller_fixtures import PIN
        from tests.test_specialist_settings import configured
        from tests.codex_exec_fixtures import install_profile
        registry, _settings = configured(storage.application.root)
        install_profile(registry)
        service = AutopilotService(storage, registry)
        from plotloom.creative_handoff_exchange import CreativeHandoffExchange
        monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: PIN)
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
    from plotloom.story_workloads import FIXED_CHINESE_BRIEF
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
        monkeypatch.setattr(
            exchange_type,
            "write_package",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(failure),
        )
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
