"""Quiescent real geometry seeds for isolated ordinary-open corruption checks."""
from contextlib import ExitStack, closing, contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
from pathlib import Path
import shutil
import stat

import pytest

from plotloom.project_storage import ProjectFolderStorage
from tests.autopilot_image_fixtures import image_environment


def first_geometry_frame(storage, service, view):
    for _ in range(30):
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            result = store.repository.autopilot.current(view.project_id)
        if result.frames:
            return result
        assert result.state in {"running", "waiting"}, result.blocker
    raise AssertionError("first geometry frame not selected")


def mismatch(*, context):
    return (941, 1672) if "shot" in context["request"]["frozenSnapshot"] else None


def seed_files(root):
    """Hash every regular file; a seed must not hide mutable or external state."""
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("geometry seed root must be a real directory")
    files = {}
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("geometry seed cannot contain links")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("geometry seed requires independent regular files")
        if path.name.endswith(("-wal", "-shm", "-journal")):
            raise ValueError("geometry seed retained SQLite sidecars")
        files[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return tuple(files.items())


@dataclass(frozen=True)
class GeometryFrameSeed:
    root: Path
    project_id: str
    home_name: str
    files: tuple[tuple[str, str], ...]


@contextmanager
def _exclusive_seed(seed):
    # Existing OS locks prove no controller or project handle still owns this
    # fixture. Keep them held through physical copying; never create lock files.
    with ExitStack() as stack:
        for path in (
            seed.root / "application/.autopilot-controller.lock",
            seed.root / "outputs" / seed.home_name / ".project-operation.lock",
        ):
            handle = stack.enter_context(path.open("rb"))
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError("geometry seed still has active resources") from error
        yield


def build_geometry_frame_seed(root):
    with pytest.MonkeyPatch.context() as patch:
        storage, registry, service, view, _calls, _text = image_environment(root, patch, geometry=mismatch)
        try:
            result = first_geometry_frame(storage, service, view)
            assert len(result.frames) == 1 and result.frames[0].geometry_preparation is not None
            host = registry._codex_exec_test_host
            assert not host.pending and not registry.view()["busy"]
            assert all(status.state in {"completed", "failed", "settled"} for status in host.statuses.values())
            with closing(storage.projects.open(view.project_id)) as store:
                home_name = store.home.name
                with store.repository.engine.connect() as connection:
                    assert connection.exec_driver_sql(
                        "SELECT count(*) FROM v2_autopilot_exec_attempts "
                        "WHERE state NOT IN ('completed','failed','settled') OR image_budget_state='reserved'"
                    ).scalar() == 0
        finally:
            service.close()
        assert service._thread is None and service._descriptor is None
    seed = GeometryFrameSeed(root, view.project_id, home_name, seed_files(root))
    with _exclusive_seed(seed):
        assert seed.files == seed_files(root)
    return seed


def copy_geometry_frame_seed(seed, destination):
    # Refuse replaced links/special files before opening even the lock paths.
    if seed_files(seed.root) != seed.files:
        raise ValueError("geometry seed changed after closure")
    with _exclusive_seed(seed):
        if seed_files(seed.root) != seed.files:
            raise ValueError("geometry seed changed after closure")
        shutil.copytree(seed.root, destination)
        if seed_files(destination) != seed.files:
            raise ValueError("geometry copy differs from its complete seed")
        for relative, _digest in seed.files:
            source, copied = (seed.root / relative).stat(), (destination / relative).stat()
            if (source.st_dev, source.st_ino) == (copied.st_dev, copied.st_ino):
                raise ValueError("geometry copy shares a file with its seed")
    storage = ProjectFolderStorage(
        outputs_root=destination / "outputs", application_data_root=destination / "application",
    )
    with closing(storage.projects.open(seed.project_id)) as store:
        view = store.repository.autopilot.current(seed.project_id)
        assert store.home == destination / "outputs" / seed.home_name
    return storage, view
