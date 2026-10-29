"""Committed profile resources must be proven in their actual owning Git trees."""
import subprocess
from pathlib import Path

import pytest

from scripts.autopilot.handoff.handoff_source import require_committed_profile_sources


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
        capture_output=True, text=True).stdout.strip()


def initialize(root):
    root.mkdir(parents=True)
    git(root, "init", "--quiet")
    git(root, "config", "user.name", "Synthetic fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")


def commit(root):
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "Synthetic source topology")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def source(tmp_path, monkeypatch):
    import plotloom.codex_exec_profile as profile
    root = tmp_path / "source"
    initialize(root)
    (root / "owner.py").write_text("# parent resource\n")
    (root / "src/plotloom").mkdir(parents=True)
    (root / "src/plotloom/current.py").write_text("# full Python closure\n")
    fork = root / "third_party/shuohao-skills"
    initialize(fork)
    (fork / "provider-literals.mjs").write_text("// fork resource\n")
    revision = commit(fork)
    git(root, "add", "owner.py", "src")
    git(root, "update-index", "--add", "--cacheinfo", "160000", revision, "third_party/shuohao-skills")
    git(root, "commit", "--quiet", "-m", "Synthetic parent with exact fork")
    monkeypatch.setattr(profile, "INSTRUCTION_FILES", ("owner.py",))
    monkeypatch.setattr(profile, "VALIDATOR_FILES", ("third_party/shuohao-skills/provider-literals.mjs",))
    return root, fork


def test_committed_parent_and_exact_fork_resources_pass(source):
    root, _fork = source
    require_committed_profile_sources(root)


@pytest.mark.parametrize("change", ["parent-dirty", "parent-staged", "python-untracked",
    "fork-dirty", "fork-staged", "fork-untracked", "fork-owned-untracked",
    "fork-head", "parent-staged-gitlink", "parent-not-gitlink"])
def test_unproven_source_resources_fail_closed(source, change):
    root, fork = source
    if change.startswith("parent-") and change in {"parent-dirty", "parent-staged"}:
        (root / "owner.py").write_text("# changed\n")
        if change == "parent-staged":
            git(root, "add", "owner.py")
    elif change == "python-untracked":
        (root / "src/plotloom/new.py").write_text("# untracked Python owner\n")
    elif change in {"fork-dirty", "fork-staged"}:
        (fork / "provider-literals.mjs").write_text("// changed\n")
        if change == "fork-staged":
            git(fork, "add", ".")
    elif change == "fork-untracked":
        (fork / "untracked.mjs").write_text("// untracked\n")
    elif change == "fork-owned-untracked":
        git(fork, "rm", "--cached", "provider-literals.mjs")
    elif change in {"fork-head", "parent-staged-gitlink"}:
        (fork / "provider-literals.mjs").write_text("// new committed fork\n")
        commit(fork)
        if change == "parent-staged-gitlink":
            git(root, "add", "third_party/shuohao-skills")
    else:
        git(root, "rm", "--cached", "third_party/shuohao-skills")
        git(root, "commit", "--quiet", "-m", "Remove registered fork ownership")
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        require_committed_profile_sources(root)
