"""Read-only source and retained-evidence guards; credentials are never opened."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from pair_context import CONTROLS, current
WORK = current().campaign
ROOT = current().source


def sha(path):
    if path.name == "auth.json" or "token" in path.name.lower() or "sessions" in path.parts:
        raise RuntimeError("credential paths must never be read or hashed")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_identity(path, expected):
    if isinstance(expected, dict) and expected.get("kind") == "symlink":
        if not path.is_symlink() or hashlib.sha256(os.readlink(path).encode()).hexdigest() != expected["targetSha256"]:
            raise RuntimeError("retained helper-link identity changed")
    elif isinstance(expected, dict):
        if path.is_symlink() or sha(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
            raise RuntimeError("pinned file identity changed")
    elif path.is_symlink() or sha(path) != expected:
        raise RuntimeError("pinned file hash changed")


def require_historical_tree(root, expected):
    # Match the qualified F5 historical_snapshot exclusions exactly. New files
    # matter as much as missing or changed files in these frozen roots.
    actual = {str(path.relative_to(root)): {"sha256": sha(path), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts
        and path.name != "auth.json" and "token" not in path.name.lower() and "sessions" not in path.parts}
    if actual != expected:
        raise RuntimeError("frozen historical root path inventory or bytes changed")


def require_current_source_inputs(current, historical, *, revision, source_tree, dirty):
    if current["historicalDescriptor"] != "preservation_inputs.json" or sha(WORK / current["historicalDescriptor"]) != current["historicalDescriptorSha256"]:
        raise RuntimeError("immutable historical descriptor changed")
    if historical["sourceRevision"] != current["historicalSourceRevision"]:
        raise RuntimeError("historical source label differs")
    if revision != current["sourceRevision"] or source_tree != current["sourceTree"] or dirty:
        raise RuntimeError("fresh campaign requires the exact clean current source")
    for relative, expected in current["currentSourceInputs"].items():
        require_identity(ROOT / relative, expected)
    # Historical sourceInputs remain inside their hashed evidence. They are not
    # assertions about the repaired live checkout.
    return len(current["currentSourceInputs"])


def require_original_offline_inputs(baseline,pins):
    # These names were frozen relative to the retained campaign's historical
    # container, never relative to a later qualification's mutable work root.
    relative=Path(pins['oldCampaignRoot'])
    if relative.is_absolute() or '..' in relative.parts:
        raise RuntimeError('retained campaign root must stay source-relative')
    historical_root=(ROOT/relative).parent
    for name,digest in baseline['originalOfflineInputsAndProof'].items():
        item=Path(name)
        if item.is_absolute() or '..' in item.parts or sha(historical_root/item)!=digest:
            raise RuntimeError('original failed offline evidence changed: '+name)


def require_preserved_inputs():
    if Path(sys.prefix).resolve() != Path(json.loads((CONTROLS / "qa-interpreter.json").read_bytes())["prefix"]).resolve():
        raise RuntimeError("campaign driver requires the exact project Python environment")
    refused = ("PYTHONPATH", "UV_PROJECT_ENVIRONMENT", "UV_PYTHON", "UV_PROJECT", "UV_WORKING_DIRECTORY",
        "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DEBUG_TEMPROOT", "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "PYTEST_XDIST_AUTO_NUM_WORKERS", "VITEST_FILTER", "VITEST_GREP", "PLAYWRIGHT_GREP", "PLAYWRIGHT_SHARD",
        "PWTEST_GREP", "PWTEST_SHARD_INDEX", "PWTEST_SHARD_TOTAL", "BROWSER_SHARD")
    if any(os.environ.get(name) for name in refused) or os.environ.get("BROWSER_GREP") not in {None, "", ".*"}:
        raise RuntimeError("campaign refuses ambient source, interpreter, plugin or selection overrides")
    current = json.loads((WORK / "current_source.json").read_text())
    pins = json.loads((WORK / "preservation_inputs.json").read_text())
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)
    source_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    source_count = require_current_source_inputs(current, pins, revision=revision, source_tree=source_tree, dirty=dirty)
    for relative, digest in pins["pinnedFiles"].items():
        if sha(ROOT / relative) != digest:
            raise RuntimeError("retained offline/campaign proof changed: " + relative)
    baseline = json.loads((ROOT / pins["baselinePath"]).read_text())
    if sha(Path(current["cli"]["path"])) != current["cli"]["sha256"]:
        raise RuntimeError("current CLI binary differs")
    for relative, expected in current["qualifiedCurrentEvidence"].items():
        require_identity(ROOT / relative, expected)
    manifest_path = ROOT / current["historicalHashManifest"]
    require_identity(manifest_path, current["historicalHashManifestSha256"])
    historical = json.loads(manifest_path.read_text())["historical_evidence"]
    for relative, expected in historical["files"].items():
        require_identity(ROOT / relative, expected)
    for directory, inventory in historical["roots"].items():
        require_historical_tree(ROOT / directory, inventory)
    require_original_offline_inputs(baseline,pins)
    original = ROOT / pins["oldCampaignRoot"]
    exclusions = {"serial/private/bridge-token", "parallel/private/bridge-token"}
    for relative, digest in baseline["retainedEvidence"].items():
        if relative in exclusions:
            raise RuntimeError("retained credential path must not appear in hash inputs")
        path = original / relative
        if isinstance(digest, dict):
            if (not path.is_symlink() or digest.get("kind") != "symlink"
                    or hashlib.sha256(os.readlink(path).encode()).hexdigest() != digest["targetSha256"]):
                raise RuntimeError("retained helper-link identity changed")
        elif sha(path) != digest:
            raise RuntimeError("retained campaign evidence or parked asset changed: " + relative)
    parked = json.loads((original / "post_exit_safe_parking.json").read_text())
    if not parked["parkedAllDispatchDisabled"] or len(parked["parkedAttemptIds"]) != 5:
        raise RuntimeError("original five-job safe parking proof differs")
    return {"sourceRevision": revision, "sourceInputs": source_count,
        "historicalSourceRevision": pins["sourceRevision"], "currentDescriptorSha256": sha(WORK / "current_source.json"),
        "retainedCampaignFiles": len(baseline["retainedEvidence"]),
        "oldParkedAttempts": parked["parkedAttemptIds"], "additionalOldDispatches": 0,
        "historicalLiveness": "UNKNOWN",
        "generationDispatches": 0, "credentialPathsExcluded": sorted(exclusions)}
