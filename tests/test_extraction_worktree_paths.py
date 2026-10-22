"""Extraction walkers distinguish declared root-local state from product files."""
from pathlib import Path

import pytest

from tests.extraction_worktree_paths import (
    _find_named_files,
    _present_forbidden_repository_roots,
    _unexpected_tracked_roots,
    _unexpected_worktree_roots,
)


@pytest.mark.parametrize("local", [".local", "outputs", ".playwright-cli", "data"])
def test_declared_root_runtime_clones_are_outside_prompt_authority(tmp_path, local):
    owned = tmp_path / "src/plotloom/prompt_templates/media_image.yaml"
    clone = tmp_path / local / "clone/src/plotloom/prompt_templates/media_image.yaml"
    for path in (owned, clone):
        path.parent.mkdir(parents=True)
        path.touch()
    assert _find_named_files(tmp_path, {owned.name}) == {owned}
    assert _unexpected_worktree_roots(tmp_path) == []
    assert _unexpected_tracked_roots([clone.relative_to(tmp_path)]) == [local]


@pytest.mark.parametrize("directory", ["src/plotloom/duplicate", "undeclared", ".undeclared", "src/plotloom/.local"])
def test_product_and_undeclared_prompt_duplicates_remain_visible(tmp_path, directory):
    duplicate = tmp_path / directory / "media_image.yaml"
    duplicate.parent.mkdir(parents=True)
    duplicate.touch()
    assert _find_named_files(tmp_path, {duplicate.name}) == {duplicate}
    expected = [] if directory.startswith("src/") else [directory]
    assert _unexpected_worktree_roots(tmp_path) == expected


def test_forbidden_roots_and_any_depth_dependency_pruning_remain_strict(tmp_path):
    forbidden = tmp_path / "backend/media_image.yaml"
    cached = tmp_path / "src/plotloom/node_modules/copy/media_image.yaml"
    for path in (forbidden, cached):
        path.parent.mkdir(parents=True)
        path.touch()
    assert _find_named_files(tmp_path, {forbidden.name}) == {forbidden}
    assert _unexpected_worktree_roots(tmp_path) == ["backend"]
    assert _unexpected_tracked_roots([Path("backend/media_image.yaml")]) == ["backend"]
    assert _present_forbidden_repository_roots(tmp_path) == ["backend"]
