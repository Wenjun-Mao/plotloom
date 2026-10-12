"""Application-owned serial controller; browser presence is not execution."""
from contextlib import closing
import fcntl
import os
import stat
import logging
from threading import Event, Thread
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError

from .autopilot_launch import freeze_launch_policy, assert_frozen_execution
from .autopilot_text_controller import AutopilotTextController
from .autopilot_image_controller import AutopilotImageController
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .project_storage import ProjectStorageError, ProjectBusyError, ProjectClosedError

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
                if request.action in {"cancel", "takeover"}:
                    self.controller.cancel_pending(store, view)
                    self.image_controller.cancel_pending(store, view)
            result = store.repository.autopilot.current(project_id)
        self._wake.set()
        return result

    def acquire_controller(self):
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
        if self._descriptor is not None:
            fcntl.flock(self._descriptor, fcntl.LOCK_UN)
            os.close(self._descriptor)
            self._descriptor = None

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
            with closing(self.storage.projects.inspect(project_id)) as inspection:
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
        view = store.repository.autopilot.current(project_id)
        return view is not None and view.state != "handed_off" and view.id not in store.repository.autopilot.recovered_run_ids()

    def _step(self, project_id):
        # Discovery is observation: closed/manual folders must not gain locks or WAL.
        with closing(self.storage.projects.inspect(project_id)) as inspection:
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
                    self.controller.advance(store, view, self.claim)
            except ImageJobError as error:
                waiting = error.code in {"specialist_busy", "image_dispatch_busy", "image_dispatch_outcome_unknown", "specialist_already_sent"}
                store.repository.autopilot.blocker(project_id, code=error.code, message=str(error), waiting=waiting)
            except (InvalidTransitionError, ValueError) as error:
                store.repository.autopilot.blocker(project_id, code="contract_blocked", message=str(error))

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._loop, name="plotloom-pre-video-controller", daemon=True)
        self._thread.start()

    def _loop(self):
        try:
            while not self._stop.is_set():
                self._wake.clear()
                try:
                    homes = self.storage.projects.discover() if self.acquire_controller() else []
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
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        else:
            self.release_controller()
