"""Explicit repository-root policy shared by extraction scans."""
from __future__ import annotations

import os
import re
from pathlib import Path

FORBIDDEN_REPOSITORY_PATHS = {
    "app.py",
    "backend",
    "static",
    "src/narrative_forge",
    "projects",
}
ALLOWED_REPOSITORY_ROOTS = {
    ".agents",
    ".env.example",
    ".github",
    ".gitignore",
    ".gitmodules",
    ".python-version",
    "AGENTS.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "docs",
    "frontend",
    "pyproject.toml",
    "scripts",
    "services",
    "src",
    "tests",
    "third_party",
    "uv.lock",
}
IGNORED_WORKTREE_ROOTS = {
    ".gates.jsonl",
    ".env",
    ".git",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "data",
    "dist",
    "htmlcov",
    "node_modules",
    "output",
    "test-results",
}
LOCAL_WORKTREE_DOTENV_PATTERN = re.compile(r"^\.env(?:\..+)?\.local$")
APPROVED_UNTRACKED_WORKTREE_ROOTS = {".playwright-cli", "outputs"}


IGNORED_SEARCH_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}

def _is_approved_untracked_worktree_root(path: Path) -> bool:
    """Permit only declared local runtime state in the filesystem-only scan."""

    return (
        path.name in IGNORED_WORKTREE_ROOTS
        or path.name in APPROVED_UNTRACKED_WORKTREE_ROOTS
        or LOCAL_WORKTREE_DOTENV_PATTERN.fullmatch(path.name) is not None
    )


def _unexpected_worktree_roots(root: Path) -> list[str]:
    return sorted(
        path.name
        for path in root.iterdir()
        if not _is_approved_untracked_worktree_root(path)
        and path.name != ".DS_Store"
        and not path.name.startswith(".coverage")
        and path.name not in ALLOWED_REPOSITORY_ROOTS
    )


def _unexpected_tracked_roots(tracked_paths: list[Path]) -> list[str]:
    return sorted({path.parts[0] for path in tracked_paths} - ALLOWED_REPOSITORY_ROOTS)


def _present_forbidden_repository_roots(root: Path) -> list[str]:
    return sorted(path for path in FORBIDDEN_REPOSITORY_PATHS if (root / path).exists())


def _find_named_files(root: Path, filenames: set[str]) -> set[Path]:
    matches: set[Path] = set()
    for directory, child_directories, child_filenames in os.walk(root):
        directory_path = Path(directory)
        child_directories[:] = [
            name for name in child_directories
            if name not in IGNORED_SEARCH_DIRECTORIES
            and not (
                directory_path == root
                and _is_approved_untracked_worktree_root(directory_path / name)
            )
        ]
        matches.update(directory_path / name for name in child_filenames if name in filenames)
    return matches
