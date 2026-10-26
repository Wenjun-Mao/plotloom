"""Bind native Alpha to its actual clean source, CLI and checked toolchain."""
import json
import platform
import subprocess
from hashlib import sha256
from pathlib import Path

from .alpha_review_templates import COMMIT_SHA_PATTERN
from .autopilot_launch import image_execution_pin
from .alpha_workloads import ALPHA_ACCEPTANCE_VERSION, ALPHA_STORIES, NATIVE_OPERATIONS
from .codex_exec_auth import check_codex_exec_readiness
from .codex_exec_profile import build_codex_exec_profile
from .codex_exec_python_environment import inspect_checked_python_environment
from .creative_handoff_exchange import CreativeHandoffExchange
from .generation.prompts import canonical_json, sha256_text


def validate_commit_sha(value):
    if not isinstance(value, str) or not COMMIT_SHA_PATTERN.fullmatch(value):
        raise ValueError("commit must be a 40-character hexadecimal Git commit SHA")
    return value.lower()


def source_checkout_root():
    root = Path(__file__).resolve().parents[2]
    actual = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if actual != root:
        raise ValueError("Alpha must execute its owning source checkout")
    return root


def _git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments], check=True,
        capture_output=True, text=True, timeout=10).stdout.strip()


def source_snapshot(executable, pool_limits):
    """Read actual owners; never provision a runtime or change provider settings."""
    root = source_checkout_root()
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source checkout has uncommitted changes")
    binary = Path(executable).resolve(strict=True)
    profile = build_codex_exec_profile(binary, source_root=root, pool_limits=pool_limits)
    checked = inspect_checked_python_environment(root)
    readiness = check_codex_exec_readiness(binary, source_root=root)
    if not readiness.ready:
        raise ValueError("native CLI file-store login is not ready")
    exchange = CreativeHandoffExchange(root / ".local" / "alpha-pin-observation")
    return {
        "commit": validate_commit_sha(_git(root, "rev-parse", "HEAD^{commit}")),
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "submodules": _git(root, "submodule", "status", "--recursive"),
        "sourceRoot": str(root), "cliPath": str(binary),
        "cliSha256": sha256(binary.read_bytes()).hexdigest(),
        "profile": profile.model_dump(mode="json", by_alias=True),
        "profileHash": profile.profile_hash,
        "pythonEnvironmentHash": checked.identity_hash,
        "pythonInterpreter": str(checked.interpreter),
        "platform": platform.platform(),
        "executionPins": {stage: exchange.current_execution_pin(stage) for stage in NATIVE_OPERATIONS},
        "imagePin": image_execution_pin(_git(root, "rev-parse", "HEAD"), executor_backend="codex_exec"),
    }


def native_contract_hash(snapshot):
    return sha256_text(canonical_json({
        "version": ALPHA_ACCEPTANCE_VERSION,
        "workloads": [{"story": item.alias, "version": item.version,
            "brief": item.brief.model_dump(mode="json", by_alias=True)} for item in ALPHA_STORIES],
        "repeats": 3, "operations": NATIVE_OPERATIONS, "requiredInstallations": 9,
        "firstPassRequired": 60, "firstPassTotal": 72,
        "reviewRepeats": [1], "correctionLimit": 1,
        "correctionStages": ["outline", "characters", "art"],
        "profileHash": snapshot["profileHash"], "executionPins": snapshot["executionPins"],
    }))


# The required current native envelope, including both supported style routes.
PREFLIGHT_CASES = {
    "outline": ("outline", "upstream"),
    "branches": ("branches", "plotloom_native"),
    "cast-preset": ("characters", "preset_style"),
    "art-preset": ("art", "preset_style"),
    "script": ("script", "plotloom_native"),
    "storyboard-upstream": ("storyboard", "upstream"),
    "characters-saved": ("characters", "saved_brief"),
    "art-saved": ("art", "saved_brief"),
    "storyboard-saved": ("storyboard", "saved_brief"),
    "intent": ("bridge-intent", "plotloom_native"),
    "presentation": ("bridge-presentation", "plotloom_native"),
}


def preflight_plan_identity(package_path):
    """Rebuild the exact source-owned plan from its retained frozen package."""
    from .codex_exec_files import read_confined_regular_file
    from .codex_exec_validation import validation_plan_from_package
    package = Path(package_path)
    if not package.is_absolute() or package.is_symlink() or package.resolve(strict=True) != package:
        raise ValueError("preflight package must be a physical absolute directory")
    payload = json.loads(read_confined_regular_file(package, "request.json", max_bytes=1_000_000))
    plan = validation_plan_from_package(payload)
    return plan.stage, plan.route, plan.plan_hash, plan.source_revision


def require_preflight(proof_path, snapshot):
    """Require the exact current case/route/plan union and all denial controls."""
    try:
        proof = json.loads(Path(proof_path).read_text())
        _assert_preflight(proof, snapshot)
    except (KeyError, TypeError, OSError, ValueError) as error:
        raise ValueError("native preflight proof is incomplete, invalid or differently bound") from error
    return sha256_text(canonical_json(proof))


def _assert_preflight(proof, snapshot):
    required = {"cliSha256", "profileHash", "pythonEnvironmentHash", "validatorCommands", "negativeControls"}
    if set(proof) != required or any(proof[key] != snapshot[key]
            for key in ("cliSha256", "profileHash", "pythonEnvironmentHash")):
        raise ValueError("native preflight executable/profile/runtime identity differs")
    commands = proof["validatorCommands"]
    expected = {(case, step) for case in PREFLIGHT_CASES for step in ("validate", "render")}
    if (not isinstance(commands, list) or len(commands) != len(expected)
            or {(row["case"], row["step"]) for row in commands} != expected
            or any(type(row["exitCode"]) is not int or row["exitCode"] != 0 for row in commands)):
        raise ValueError("native preflight requires the exact eleven validator/render pairs")
    packages = {}
    for row in commands:
        stage, route = PREFLIGHT_CASES[row["case"]]
        identity = preflight_plan_identity(row["packagePath"])
        if (row["stage"], row["route"], row["planHash"], snapshot["commit"]) != identity:
            raise ValueError("preflight evidence differs from its exact frozen plan")
        if identity[:2] != (stage, route):
            raise ValueError("preflight plan substitutes a different stage or route")
        if row["case"] in packages and packages[row["case"]] != row["packagePath"]:
            raise ValueError("validator and renderer must bind the same frozen package")
        packages[row["case"]] = row["packagePath"]
    if len(set(packages.values())) != len(PREFLIGHT_CASES):
        raise ValueError("preflight cases must retain distinct source-owned packages")
    controls = proof["negativeControls"]
    expected_controls = {"imports", "python-sibling", "node-sibling", "python-auth", "node-auth", "original-venv-metadata", "uv-alias"}
    if (not isinstance(controls, list) or len(controls) != 7 or {row["name"] for row in controls} != expected_controls
            or any(type(row["exitCode"]) is not int or (row["exitCode"] == 0) != (row["name"] == "imports") for row in controls)):
        raise ValueError("native preflight requires checked imports and all six denial controls")
