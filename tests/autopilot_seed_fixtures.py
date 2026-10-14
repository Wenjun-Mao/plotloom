"""Closed physical roots shared by the geometry and handoff fixture seeds."""
from contextlib import ExitStack, closing, contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
from pathlib import Path
import shutil
import stat

from plotloom.project_storage import ProjectFolderStorage


def seed_files(root):
    """Hash every regular file; a seed must not hide mutable or external state."""
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("autopilot seed root must be a real directory")
    files = {}
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("autopilot seed cannot contain links")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("autopilot seed requires independent regular files")
        if path.name.endswith(("-wal", "-shm", "-journal")):
            raise ValueError("autopilot seed retained SQLite sidecars")
        files[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return tuple(files.items())


@dataclass(frozen=True)
class ClosedAutopilotSeed:
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
                raise ValueError("autopilot seed still has active resources") from error
        yield


def freeze_closed_autopilot_seed(root, project_id, home_name):
    seed = ClosedAutopilotSeed(root, project_id, home_name, seed_files(root))
    with _exclusive_seed(seed):
        assert seed.files == seed_files(root)
    return seed


def copy_closed_autopilot_seed(seed, destination):
    # Refuse replaced links/special files before opening even the lock paths.
    if seed_files(seed.root) != seed.files:
        raise ValueError("autopilot seed changed after closure")
    with _exclusive_seed(seed):
        if seed_files(seed.root) != seed.files:
            raise ValueError("autopilot seed changed after closure")
        shutil.copytree(seed.root, destination)
        if seed_files(destination) != seed.files:
            raise ValueError("autopilot copy differs from its complete seed")
        for relative, _digest in seed.files:
            source, copied = (seed.root / relative).stat(), (destination / relative).stat()
            if (source.st_dev, source.st_ino) == (copied.st_dev, copied.st_ino):
                raise ValueError("autopilot copy shares a file with its seed")
    storage = ProjectFolderStorage(
        outputs_root=destination / "outputs", application_data_root=destination / "application",
    )
    with closing(storage.projects.open(seed.project_id)) as store:
        view = store.repository.autopilot.current(seed.project_id)
        assert store.home == destination / "outputs" / seed.home_name
    return storage, view
