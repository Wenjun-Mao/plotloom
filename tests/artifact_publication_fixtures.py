"""Abrupt process death at actual artifact I/O boundaries, on disposable roots."""

import multiprocessing
import os
import signal


def kill_at_publication(boundary):
    import plotloom.project_storage.artifact_publication as publication

    if boundary == "partial_write":
        original = publication.os.fdopen

        class PartialWrite:
            def __init__(self, descriptor, **kwargs):
                self.handle = original(descriptor, "wb", **kwargs)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.handle.close()

            def write(self, content):
                self.handle.write(content[:17])
                self.handle.flush()
                os.fsync(self.handle.fileno())
                os.kill(os.getpid(), signal.SIGKILL)

            def flush(self):
                self.handle.flush()

            def fileno(self):
                return self.handle.fileno()

        publication.os.fdopen = lambda descriptor, mode, **kwargs: (
            PartialWrite(descriptor, **kwargs)
            if mode == "wb"
            else original(descriptor, mode, **kwargs)
        )
    else:
        original = publication.rename_exclusive

        def interrupted(*args):
            if boundary == "after_promotion":
                original(*args)
            os.kill(os.getpid(), signal.SIGKILL)

        publication.rename_exclusive = interrupted


def child_process(callback):
    process = multiprocessing.get_context("fork").Process(target=callback)
    process.start()
    try:
        process.join(timeout=20)
        assert not process.is_alive(), "bounded publication child did not finish"
        return process.exitcode
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        process.close()
