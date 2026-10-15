"""Source-bound Codex CLI profile construction for the local host bridge."""
from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path

from .codex_exec_auth import AUTHENTICATION_STORE
from .codex_exec_contracts import CodexExecProfile
from .codex_exec_resources import validator_toolchain_hash

SUPPORTED_CLI_VERSION = "codex-cli 0.162.0-alpha.17.2"
EXECUTION_MODEL = "gpt-6.1-sol"
EXECUTION_REASONING_EFFORT = "medium"
PERMISSION_PROFILE = "plotloom_autopilot_delivery_v5"
TOOL_PROFILE = "plotloom_autopilot_tools_v4"
TEXT_VALIDATOR_RUNTIME_PROFILE = "node_openssl_private_zsh_tmp_and_checked_python_v3"
NODE_OPENSSL_CONFIG = Path("/System/Library/OpenSSL/openssl.cnf")
DISABLED_CLI_FEATURES = (
    "apps",
    "browser_annotation_api",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "in_app_browser",
    "mcp_2026_07_28",
    "multi_agent",
    "multi_agent_v2",
    "skill_mcp_dependency_install",
    "standalone_web_search",
    "tool_call_mcp_elicitation",
)
INSTRUCTION_FILES = (
    "src/plotloom/codex_exec_prompts.py",
    ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
    ".agents/skills/plotloom-intent-specialist/SKILL.md",
    ".agents/skills/plotloom-presentation-specialist/SKILL.md",
    ".agents/skills/plotloom-image-specialist/SKILL.md",
)
VALIDATOR_FILES = (
    "src/plotloom/codex_exec_contracts.py",
    "src/plotloom/codex_exec_pool_contracts.py",
    "src/plotloom/codex_exec_namespace_contracts.py",
    "src/plotloom/codex_exec_receipt_contracts.py",
    "src/plotloom/codex_exec_constants.py",
    "src/plotloom/codex_exec_attempt_contracts.py",
    "src/plotloom/codex_exec_files.py",
    "src/plotloom/codex_exec_telemetry.py",
    "src/plotloom/codex_exec_tool_source.py",
    "src/plotloom/codex_exec_delivery.py",
    "src/plotloom/codex_exec_profile.py",
    "src/plotloom/codex_exec_resources.py",
    "src/plotloom/codex_exec_python_environment.py",
    "src/plotloom/codex_exec_runtime_tree.py",
    "scripts/provision_codex_exec_python.py",
    "src/plotloom/codex_exec_auth.py",
    "src/plotloom/codex_exec_prompts.py",
    "src/plotloom/codex_exec_runtime.py",
    "src/plotloom/codex_exec_stage_routing.py",
    "src/plotloom/codex_exec_validation.py",
    "src/plotloom/autopilot_contracts.py",
    "src/plotloom/autopilot_exec.py",
    "src/plotloom/autopilot_exec_reservation.py",
    "src/plotloom/autopilot_exec_staged.py",
    "src/plotloom/autopilot_image_controller.py",
    "src/plotloom/autopilot_early_references.py",
    "src/plotloom/autopilot_image_selection.py",
    "src/plotloom/autopilot_materials.py",
    "src/plotloom/autopilot_launch.py",
    "src/plotloom/autopilot_text_controller.py",
    "src/plotloom/creative_handoff_contracts.py",
    "src/plotloom/creative_handoff_exchange.py",
    "src/plotloom/creative_handoff_package_exchange.py",
    "src/plotloom/image_commands.py",
    "src/plotloom/image_job_contracts.py",
    "src/plotloom/image_job_exchange.py",
    "src/plotloom/image_job_package.py",
    "src/plotloom/persistence/schema/project_autopilot.py",
    "src/plotloom/persistence/project/autopilot.py",
    "src/plotloom/persistence/project/autopilot_exec_attempts.py",
    "src/plotloom/persistence/project/autopilot_activity.py",
    "src/plotloom/persistence/project/autopilot_inventory_validation.py",
    "src/plotloom/persistence/project/first_install_references.py",
    "src/plotloom/persistence/project/production_rebuild_quiescence.py",
    "src/plotloom/persistence/project/media_character_references.py",
    "src/plotloom/persistence/project/autopilot_bindings.py",
    "src/plotloom/persistence/project/autopilot_checkpoints.py",
    "src/plotloom/persistence/project/image_preflight.py",
    "src/plotloom/persistence/project/image_source_lineage.py",
    "src/plotloom/persistence/project/media_image_preparation.py",
    "src/plotloom/persistence/project/media_reference_proposals.py",
    "src/plotloom/persistence/project/media_art_reference_proposals.py",
    "src/plotloom/project_storage/autopilot_validation.py",
    "src/plotloom/project_storage/creative_evidence_inventory.py",
    "src/plotloom/project_storage/material_bundle_validation.py",
    "src/plotloom/project_storage/handoff_validation.py",
    "services/creator_workbench/codex_exec_supervisor.py",
    "services/creator_workbench/codex_exec_supervisor_pool.py",
    "services/creator_workbench/codex_exec_supervisor_queue_control.py",
    "services/creator_workbench/codex_exec_supervisor_admission.py",
    "services/creator_workbench/codex_exec_supervisor_control.py",
    "services/creator_workbench/codex_exec_supervisor_worker_ownership.py",
    "services/creator_workbench/codex_exec_supervisor_errors.py",
    "services/creator_workbench/codex_exec_supervisor_job.py",
    "services/creator_workbench/codex_exec_supervisor_ledger.py",
    "services/creator_workbench/codex_exec_supervisor_namespace.py",
    "services/creator_workbench/codex_exec_supervisor_process.py",
    "services/creator_workbench/codex_exec_supervisor_environment.py",
    "services/creator_workbench/codex_exec_supervisor_validation.py",
    "services/creator_workbench/codex_exec_supervisor_validation_process.py",
    "services/creator_workbench/codex_exec_supervisor_image.py",
    "services/creator_workbench/codex_exec_supervisor_terminal.py",
    "services/creator_workbench/codex_exec_supervisor_worker.py",
    "services/creator_workbench/host_bridge.py",
    "services/creator_workbench/codex_client.py",
    "services/creator_workbench/isolated.py",
    "services/creator_workbench/manage.py",
    "src/plotloom/specialist_settings.py",
    "scripts/branch_suggestion.py",
    "scripts/cast-style.mjs",
    "scripts/brief-cast-style.mjs",
    "scripts/art-style.mjs",
    "scripts/brief-art-style.mjs",
    "scripts/brief-storyboard-style.mjs",
    "scripts/storyboard-receiving.mjs",
    "scripts/storyboard-dialogue-timing.mjs",
    "src/plotloom/production_dialogue_timing.py",
    "scripts/native_bridge_intent.py",
    "scripts/native_bridge_presentation.py",
    "pyproject.toml",
    "uv.lock",
)

def cli_feature_flags(domain: str) -> tuple[str, ...]:
    """Pin nonconflicting image-tool features for one execution domain."""
    if domain not in {"text", "image"}:
        raise ValueError("Codex CLI feature profile requires a supported delivery domain")
    if domain == "text":
        return ("--disable", "image_generation", "--disable", "view_image")
    return ("--enable", "image_generation", "--enable", "view_image")


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hash(source_root: Path, files: tuple[str, ...]) -> str:
    entries = []
    for relative in files:
        path = source_root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"source-bound Codex capability is unavailable: {relative}")
        if not path.resolve(strict=True).is_relative_to(source_root):
            raise RuntimeError(f"source-bound Codex capability escapes its checkout: {relative}")
        entries.append((relative, _hash_file(path)))
    encoded = json.dumps(entries, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(encoded).hexdigest()


def _python_source_tree_hash(source_root: Path) -> str:
    from .codex_exec_runtime_tree import python_source_identity

    _parent, identity = python_source_identity(source_root)
    return identity


def build_codex_exec_profile(executable: Path, *, source_root: Path, pool_limits=None) -> CodexExecProfile:
    """Fail closed unless this source checkout and the evaluated CLI are present."""
    executable = executable.expanduser().resolve(strict=True)
    source_root = source_root.expanduser().resolve(strict=True)
    if not executable.is_file() or source_root.joinpath(".git").is_symlink() or not source_root.joinpath(".git").exists():
        raise RuntimeError("Codex Exec requires its qualified executable and source checkout")
    if not executable.stat().st_mode & 0o111:
        raise RuntimeError("qualified Codex CLI is not executable")
    if NODE_OPENSSL_CONFIG.is_symlink() or not NODE_OPENSSL_CONFIG.is_file():
        raise RuntimeError("the pinned Node validator OpenSSL configuration is unavailable")
    version = subprocess.run(
        [str(executable), "--version"], capture_output=True, timeout=5, check=False
    )
    if version.returncode != 0 or version.stderr or version.stdout.decode("utf-8", "strict").strip() != SUPPORTED_CLI_VERSION:
        raise RuntimeError("installed Codex CLI version has no qualified execution evidence adapter")
    from .codex_exec_pool_contracts import CodexExecPoolLimits
    limits = CodexExecPoolLimits.model_validate(pool_limits or CodexExecPoolLimits())
    return CodexExecProfile(
        contractVersion="plotloom.codex-exec.v8",
        executable_sha256=_hash_file(executable),
        cli_version=SUPPORTED_CLI_VERSION,
        model=EXECUTION_MODEL,
        reasoning_effort=EXECUTION_REASONING_EFFORT,
        capabilities=(
            "exec_json_events_v1",
            "session_rollout_v1",
            "image_gen_event_v1",
            "image_reference_view_v1",
            "delivery_directory_write_v1",
        ),
        instruction_hash=_source_hash(source_root, INSTRUCTION_FILES),
        validator_hash=sha256(json.dumps({
            "files": _source_hash(source_root, VALIDATOR_FILES),
            "pythonSourceTree": _python_source_tree_hash(source_root),
            "validatorToolchain": validator_toolchain_hash(source_root),
        }, separators=(",", ":")).encode()).hexdigest(),
        authentication_store=AUTHENTICATION_STORE,
        permission_profile=PERMISSION_PROFILE,
        tool_profile=TOOL_PROFILE,
        text_validator_runtime_profile=TEXT_VALIDATOR_RUNTIME_PROFILE,
        max_runtime_seconds=1800,
        # Session JSONL may embed ImageGen result bytes in one Extension record.
        max_event_bytes=50_000_000,
        max_output_bytes=500_000_000,
        max_image_outputs=4,
        max_processes=limits.max_processes,
        max_text_processes=limits.max_text_processes,
        max_image_processes=limits.max_image_processes,
        max_queued_jobs=limits.max_queued_jobs,
    )
