"""Actual Git identity and independently pinned current workflow bytes."""
import json
import subprocess
from hashlib import sha256
from pathlib import Path

WORKFLOW_FILES = (
    "capsule.mjs", "node_helper.mjs", "handoff_files.py", "handoff_phase.py",
    "handoff_receiver.py", "handoff_process.py", "handoff_qa.py", "handoff_source.py",
    "handoff_launch.py", "handoff_plan.py", "proof_launch.py", "proof_receiver.py", "paid_launch.py", "paid_receiver.py",
    "paid_outline_contracts.py", "paid_outline_prepare.py", "paid_outline_run.py",
    "paid_outline_state.py", "paid_outline_composition.py",
)
ENTRY_REGISTRY = {"handoff_proof_only": "proof_launch.py", "paid_outline": "paid_launch.py"}
RECEIVER_REGISTRY = {"handoff_proof_only": "proof_receiver.py", "paid_outline": "paid_receiver.py"}


def git_value(root, *args):
    value = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
        check=True, timeout=10)
    return value.stdout.decode("utf-8", "strict").strip()


def source_identity(root, *, require_committed=False):
    """HEAD/tree and current closure are distinct facts, never canary constants."""
    root = Path(root).resolve(strict=True)
    paths = ["scripts/autopilot/handoff/" + name for name in WORKFLOW_FILES]
    paths.append("scripts/autopilot/handoff_bundle.py")
    entries = {}
    for name in paths:
        path = root / name
        if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != path:
            raise RuntimeError("owned workflow source unavailable: " + name)
        entries[name] = sha256(path.read_bytes()).hexdigest()
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", "--", *paths],
        capture_output=True, check=False, timeout=10).returncode == 0
    clean = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", *paths],
        capture_output=True, check=False, timeout=10).returncode == 0
    if require_committed and not (tracked and clean):
        raise RuntimeError("paid Outline requires committed owned workflow source")
    raw = (json.dumps(entries, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return {"version": 1, "kind": "plotloom.handoff-source.v1", "repositoryRoot": str(root),
        "revision": git_value(root, "rev-parse", "HEAD"),
        "tree": git_value(root, "rev-parse", "HEAD^{tree}"),
        "files": entries, "closureSha256": sha256(raw).hexdigest(), "committed": tracked and clean}


def require_committed_profile_sources(root):
    """The production profile remains the owner of its validator/source list."""
    from plotloom.codex_exec_profile import INSTRUCTION_FILES, VALIDATOR_FILES
    paths = sorted(set(INSTRUCTION_FILES) | set(VALIDATOR_FILES))
    # The profile additionally binds the entire current Python source tree.
    paths.extend(str(path.relative_to(root)) for path in (root / "src/plotloom").rglob("*.py"))
    git_value(root, "ls-files", "--error-unmatch", "--", *paths)
    subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", *paths],
        capture_output=True, check=True, timeout=10)
