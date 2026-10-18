"""Application-owned serial controller; browser presence is not execution."""
import fcntl
import logging
import os
import stat
from contextlib import closing, contextmanager
from threading import Event, Lock, RLock, Thread
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from .autopilot_exec import suspend_pending_codex_exec
from .autopilot_image_controller import AutopilotImageController
from .autopilot_launch import assert_frozen_execution, freeze_launch_policy
from .autopilot_text_controller import AutopilotTextController
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .project_storage import ProjectBusyError, ProjectClosedError, ProjectStorageError

logger = logging.getLogger(__name__)
STORAGE_FAILURE_MESSAGE = "自动素材因存储错误暂停。请检查磁盘空间和项目存储，再恢复原运行；不要重复发送任务。"


class AutopilotService:
    """Process lease precedes claims; existing native reservations never expire."""
    def __init__(self, storage, registry, *, interval_seconds=5):
        self.storage, self.registry = storage, registry
        self.controller = AutopilotTextController(storage, registry)
        self.image_controller = AutopilotImageController(registry)
        self.claim = uuid4().hex
        self.interval_seconds = interval_seconds
        self._wake = Event()
        self._stop = Event()
        self._thread = None
        self._descriptor = None
        self._lifecycle_lock = RLock()
        self._descriptor_lock = Lock()
        self._runtime_owners = 0
        self._unrecorded_failures = {}
        self.controller_blocker = None

    def launch(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store:
            existing = store.repository.autopilot.current(project_id)
            if existing is not None:
                return existing
            policy = freeze_launch_policy(store, self.registry, request)
            result = store.repository.autopilot.start(project_id,
                expected_brief_revision=request.expected_brief_revision, policy=policy)
        self._wake.set()
        return result

    def control(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store:
            view = store.repository.autopilot.current(project_id)
            if view is None:
                raise InvalidTransitionError("项目没有自动素材运行。")
            if request.action == "resume":
                assert_frozen_execution(store, self.registry, view.policy)
            with store.repository.manual_command():
                store.repository.autopilot.control(project_id,
                    expected_revision=request.expected_revision, action=request.action)
                if request.action == "pause":
                    suspend_pending_codex_exec(store, self.registry, view)
                if request.action in {"cancel", "takeover"}:
                    self.controller.cancel_pending(store, view)
                    self.image_controller.cancel_pending(store, view)
            result = store.repository.autopilot.current(project_id)
        self._wake.set()
        return result

    def continue_material(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store:
            policy = freeze_launch_policy(store, self.registry, request)
            result = store.repository.autopilot.continue_material(project_id, request=request, policy=policy)
        self._wake.set()
        return result

    def acquire_controller(self):
        with self._descriptor_lock:
            return self._acquire_controller()

    def _acquire_controller(self):
        if self._descriptor is not None:
            return True
        path = self.storage.application.root / ".autopilot-controller.lock"
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            os.close(descriptor)
            raise InvalidTransitionError("controller lease must be one confined regular file")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return False
        self._descriptor = descriptor
        return True

    def release_controller(self):
        with self._descriptor_lock:
            if self._descriptor is not None:
                descriptor, self._descriptor = self._descriptor, None
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def step(self, project_id):
        if self._descriptor is None:
            raise InvalidTransitionError("controller process lease is required before claiming a run")
        if project_id in self._unrecorded_failures:
            self._record_failure(project_id, **self._unrecorded_failures[project_id])
            return
        try:
            self._step(project_id)
        except (OSError, SQLAlchemyError):
            # A fresh session follows any rolled-back owner transaction. Never
            # reconstruct a job or infer that failed I/O means no dispatch.
            self._record_storage_failure(project_id)

    def _record_storage_failure(self, project_id):
        self._record_failure(project_id, code="storage_failure", message=STORAGE_FAILURE_MESSAGE)

    def _record_failure(self, project_id, *, code, message):
        self._unrecorded_failures[project_id] = {"code": code, "message": message}
        try:
            with closing(self.storage.projects.inspect(project_id, passive=True)) as inspection:
                if not self._can_advance(inspection, project_id):
                    self._unrecorded_failures.pop(project_id, None)
                    return
            with closing(self.storage.projects.open(project_id)) as store:
                if self._can_advance(store, project_id):
                    store.repository.autopilot.blocker(project_id, code=code, message=message)
        except Exception:
            # Keep this project quarantined until its failure can be recorded;
            # unrelated projects continue. SQL/paths may contain credentials.
            logger.error("Autopilot storage failure; pending safe project failure recording")
        else:
            self._unrecorded_failures.pop(project_id, None)

    @staticmethod
    def _can_advance(store, project_id):
        state, _revision = store.repository.operational_state()
        if state != "open" or store.project().lifecycle_status.value != "active":
            return False
        return store.repository.autopilot.controller_execution_eligible(project_id)

    def _step(self, project_id):
        # Discovery is observation: closed/manual folders must not gain locks or WAL.
        with closing(self.storage.projects.inspect(project_id, passive=True)) as inspection:
            if not self._can_advance(inspection, project_id):
                return
        with closing(self.storage.projects.open(project_id)) as store:
            if not self._can_advance(store, project_id):
                return
            store.repository.autopilot.claim(project_id, self.claim)
            view = store.repository.autopilot.current(project_id)
            try:
                if any(item["operationKey"] == "installation" for item in view.checkpoints):
                    self.image_controller.advance(store, view, self.claim)
                else:
                    if view.state in {"running", "waiting"}:
                        from .autopilot_early_references import advance_early_references
                        assert_frozen_execution(store, self.registry, view.policy)
                        advance_early_references(self.image_controller, store, view, self.claim)
                        view = store.repository.autopilot.current(project_id)
                    else:
                        self.image_controller.reconcile_inactive(store, view, self.claim)
                        view = store.repository.autopilot.current(project_id)
                    self.controller.advance(store, view, self.claim)
            except ImageJobError as error:
                waiting = error.code in {"specialist_busy", "image_dispatch_busy", "image_dispatch_outcome_unknown", "specialist_already_sent", "codex_exec_outcome_unknown", "codex_exec_capacity_deferred"}
                store.repository.autopilot.blocker(project_id, code=error.code, message=str(error), waiting=waiting)
            except (InvalidTransitionError, ValueError) as error:
                store.repository.autopilot.blocker(project_id, code="contract_blocked", message=str(error))

    def start(self):
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = Thread(target=self._loop, name="plotloom-pre-video-controller", daemon=True)
            try:
                self._thread.start()
            except BaseException:
                self._thread = None
                self._stop.set()
                raise

    @contextmanager
    def runtime_owner(self):
        with self._lifecycle_lock:
            if self._runtime_owners == 0:
                self.start()
            self._runtime_owners += 1
        try:
            yield
        finally:
            with self._lifecycle_lock:
                self._runtime_owners -= 1
                if self._runtime_owners == 0:
                    self.close()

    def _loop(self):
        try:
            while not self._stop.is_set():
                self._wake.clear()
                try:
                    homes = self.storage.projects.discover(passive=True) if self.acquire_controller() else []
                    self.controller_blocker = None
                except (OSError, SQLAlchemyError, ProjectStorageError, InvalidTransitionError):
                    self.controller_blocker = {"code": "controller_storage_unavailable", "message": "自动素材控制器无法安全访问存储。请检查应用存储和控制器锁；未取得新运行权限。"}
                    logger.error("Autopilot controller storage unavailable; discovery will retry")
                    homes = []
                for home in homes:
                    if self._stop.is_set():
                        break
                    try:
                        self.step(home.manifest.project_id)
                    except (ProjectStorageError, ProjectBusyError, ProjectClosedError):
                        # Unsupported/closed homes cannot gain new dispatch;
                        # they stay available through ordinary operator reads.
                        continue
                    except Exception as error:
                        # Last supervisor boundary for unexpected owner failures.
                        # Preserve the same job; logging only its exception type
                        # avoids exposing arbitrary provider/SQL error values.
                        logger.error("Autopilot owner failed: %s", type(error).__name__)
                        self._record_failure(home.manifest.project_id, code="controller_failure",
                            message="自动素材控制器遇到错误，原任务和证据已保留。请检查错误或接管；不要重复发送任务。")
                self._wake.wait(self.interval_seconds)
        finally:
            self.release_controller()

    def close(self):
        # Worker finalization uses only the descriptor lock, never this lock.
        with self._lifecycle_lock:
            self._stop.set()
            self._wake.set()
            if self._thread is not None:
                self._thread.join()
                self._thread = None
            else:
                self.release_controller()
