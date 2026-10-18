"""One installation process lease; durable project facts survive browser/process exit."""
import fcntl
import logging
import os
import stat
from contextlib import contextmanager, closing
from threading import Event, Thread, Lock
from .exceptions import InvalidTransitionError

logger = logging.getLogger(__name__)

class VideoBatchRuntime:
    def __init__(self, service, *, interval_seconds=3):
        self.service = service
        self.interval_seconds = interval_seconds
        self.stop = Event()
        self.thread = None
        self.descriptor = None
        self.owners = 0
        self.owner_lock = Lock()

    def acquire(self):
        if self.descriptor is not None:
            return True
        path = self.service.storage.application.root / ".video-batch-controller.lock"
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            os.close(descriptor)
            raise InvalidTransitionError("video batch process lease is not confined")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return False
        self.descriptor = descriptor
        return True

    def step(self, project_id):
        if not self.acquire():
            raise InvalidTransitionError("another video batch controller owns execution")
        self.service.step(project_id)

    def loop(self):
        try:
            while not self.stop.is_set():
                try:
                    homes = self.service.storage.projects.discover(passive=True) if self.acquire() else []
                    for home in homes:
                        if self.stop.is_set():
                            break
                        try:
                            with closing(self.service.storage.projects.inspect(home.manifest.project_id, passive=True)) as store:
                                if store.repository.operational_state()[0] != "open" or store.repository.video_batches.current(home.manifest.project_id) is None:
                                    continue
                            self.step(home.manifest.project_id)
                        except Exception as error:
                            # No transport error content or secrets enter logs.
                            logger.error("Video batch controller held project: %s", type(error).__name__)
                except Exception as error:
                    logger.error("Video batch discovery unavailable: %s", type(error).__name__)
                self.stop.wait(self.interval_seconds)
        finally:
            if self.descriptor is not None:
                os.close(self.descriptor)
                self.descriptor = None

    @contextmanager
    def runtime_owner(self):
        with self.owner_lock:
            if self.owners == 0:
                self.stop.clear()
                self.thread = Thread(target=self.loop, name="plotloom-video-batch", daemon=True)
                self.thread.start()
            self.owners += 1
        try:
            yield
        finally:
            with self.owner_lock:
                self.owners -= 1
                if self.owners == 0:
                    self.stop.set()
                    self.thread.join()
                    self.thread = None
