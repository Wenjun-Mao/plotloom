"""Keep ADR 0033/0095 service owners explicit and source-only."""

from pathlib import Path
import subprocess

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SERVICE_DIRECTORIES = {"minimax_h3_gateway", "creator_workbench"}


def _assert_declared_services(root: Path, tracked_paths: list[Path]) -> None:
    services_root = root / "services"
    assert services_root.is_dir() and not services_root.is_symlink(), (
        "services must be a real directory"
    )
    children = {path.name for path in services_root.iterdir()}
    assert children == ALLOWED_SERVICE_DIRECTORIES, (
        "services permits only the declared gateway and creator workbench: "
        + ", ".join(sorted(children))
    )
    for name in ALLOWED_SERVICE_DIRECTORIES:
        service = services_root / name
        assert service.is_dir() and not service.is_symlink(), (
            f"the admitted {name} service must be a real directory"
        )

    tracked_service_paths = {
        path for path in tracked_paths if path.parts and path.parts[0] == "services"
    }
    invalid_tracked_paths = sorted(
        path.as_posix() for path in tracked_service_paths
        if len(path.parts) < 3 or path.parts[1] not in ALLOWED_SERVICE_DIRECTORIES
    )
    assert not invalid_tracked_paths, (
        "tracked files outside the admitted service subtrees: "
        + ", ".join(invalid_tracked_paths)
    )
    actual_service_paths = {
        path.relative_to(root)
        for path in services_root.rglob("*")
        # Service imports create ignored bytecode, not additional source owners.
        if (path.is_file() or path.is_symlink())
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and path.name != ".DS_Store"
    }
    assert actual_service_paths == tracked_service_paths, (
        "services must contain only tracked service files; unexpected: "
        + ", ".join(sorted(path.as_posix() for path in actual_service_paths - tracked_service_paths))
        + "; missing: "
        + ", ".join(sorted(path.as_posix() for path in tracked_service_paths - actual_service_paths))
    )


def test_repository_contains_only_declared_tracked_services() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPOSITORY_ROOT, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    tracked = [Path(value.decode()) for value in result.stdout.split(b"\0") if value]
    _assert_declared_services(REPOSITORY_ROOT, tracked)


@pytest.fixture
def service_tree(tmp_path: Path) -> tuple[Path, list[Path]]:
    tracked = []
    for name in ALLOWED_SERVICE_DIRECTORIES:
        relative = Path("services") / name / "README.md"
        (tmp_path / relative).parent.mkdir(parents=True)
        (tmp_path / relative).write_text("fixture service", encoding="utf-8")
        tracked.append(relative)
    _assert_declared_services(tmp_path, tracked)
    return tmp_path, tracked


@pytest.mark.parametrize("name", sorted(ALLOWED_SERVICE_DIRECTORIES))
def test_each_service_rejects_untracked_and_missing_files(service_tree, name):
    root, tracked = service_tree
    service = root / "services" / name
    extra = service / "local.env"
    extra.write_text("fixture only", encoding="utf-8")
    with pytest.raises(AssertionError, match="only tracked service files; unexpected:"):
        _assert_declared_services(root, tracked)
    extra.unlink()
    (service / "README.md").unlink()
    with pytest.raises(AssertionError, match="missing: services/"):
        _assert_declared_services(root, tracked)


@pytest.mark.parametrize("child", ["unrelated.py", "unknown-service"])
def test_unknown_service_children_and_tracked_paths_are_rejected(service_tree, child):
    root, tracked = service_tree
    unexpected = root / "services" / child
    unexpected.mkdir() if child == "unknown-service" else unexpected.touch()
    with pytest.raises(AssertionError, match="permits only"):
        _assert_declared_services(root, tracked)
    unexpected.rmdir() if unexpected.is_dir() else unexpected.unlink()
    with pytest.raises(AssertionError, match="outside the admitted service subtrees"):
        _assert_declared_services(root, tracked + [Path("services") / child / "file.py"])


@pytest.mark.parametrize("name", sorted(ALLOWED_SERVICE_DIRECTORIES))
def test_each_service_root_must_not_be_a_symlink(service_tree, name):
    root, tracked = service_tree
    service = root / "services" / name
    relocated = root / name
    service.rename(relocated)
    service.symlink_to(relocated, target_is_directory=True)
    with pytest.raises(AssertionError, match="must be a real directory"):
        _assert_declared_services(root, tracked)
