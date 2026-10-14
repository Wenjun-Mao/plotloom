from pathlib import Path

import pytest

from plotloom.codex_exec_profile import (
    DISABLED_CLI_FEATURES,
    VALIDATOR_FILES,
    cli_feature_flags,
)


def test_codex_exec_validator_pin_covers_runtime_authority_and_current_sources() -> None:
    required = {
        "src/plotloom/codex_exec_contracts.py",
        "src/plotloom/codex_exec_receipt_contracts.py",
        "src/plotloom/codex_exec_constants.py",
        "src/plotloom/codex_exec_attempt_contracts.py",
        "src/plotloom/codex_exec_auth.py",
        "src/plotloom/codex_exec_delivery.py",
        "src/plotloom/codex_exec_files.py",
        "src/plotloom/codex_exec_profile.py",
        "src/plotloom/codex_exec_resources.py",
        "src/plotloom/codex_exec_prompts.py",
        "src/plotloom/codex_exec_runtime.py",
        "src/plotloom/codex_exec_telemetry.py",
        "src/plotloom/codex_exec_tool_source.py",
        "src/plotloom/autopilot_exec.py",
        "src/plotloom/autopilot_image_controller.py",
        "src/plotloom/autopilot_text_controller.py",
        "src/plotloom/creative_handoff_package_exchange.py",
        "src/plotloom/persistence/project/autopilot.py",
        "src/plotloom/persistence/project/autopilot_bindings.py",
        "src/plotloom/persistence/project/image_source_lineage.py",
        "src/plotloom/project_storage/autopilot_validation.py",
        "src/plotloom/project_storage/creative_evidence_inventory.py",
        "services/creator_workbench/codex_exec_supervisor.py",
        "services/creator_workbench/codex_exec_supervisor_errors.py",
        "services/creator_workbench/codex_exec_supervisor_job.py",
        "services/creator_workbench/codex_exec_supervisor_ledger.py",
        "services/creator_workbench/codex_exec_supervisor_process.py",
        "services/creator_workbench/codex_exec_supervisor_validation.py",
        "services/creator_workbench/codex_exec_supervisor_validation_process.py",
        "services/creator_workbench/codex_exec_supervisor_image.py",
        "services/creator_workbench/codex_exec_supervisor_terminal.py",
        "services/creator_workbench/codex_exec_supervisor_worker.py",
        "services/creator_workbench/host_bridge.py",
        "services/creator_workbench/codex_client.py",
        "services/creator_workbench/isolated.py",
        "services/creator_workbench/manage.py",
        "scripts/branch_suggestion.py",
        "scripts/cast-style.mjs",
        "scripts/art-style.mjs",
        "scripts/native_bridge_intent.py",
        "scripts/native_bridge_presentation.py",
        "pyproject.toml",
        "uv.lock",
    }
    source_root = Path(__file__).resolve().parents[1]

    assert required <= set(VALIDATOR_FILES)
    assert all((source_root / relative).is_file() for relative in VALIDATOR_FILES)
    assert {
        "apps",
        "browser_annotation_api",
        "browser_use",
        "browser_use_external",
        "browser_use_full_cdp_access",
        "in_app_browser",
        "multi_agent",
        "multi_agent_v2",
        "tool_call_mcp_elicitation",
    } <= set(DISABLED_CLI_FEATURES)
    assert "view_image" not in DISABLED_CLI_FEATURES
    assert not {"web_search_cached", "web_search_request"} & set(DISABLED_CLI_FEATURES)


def test_cli_image_capabilities_are_enabled_only_for_image_attempts() -> None:
    text_flags = cli_feature_flags("text")
    image_flags = cli_feature_flags("image")

    assert text_flags == ("--disable", "image_generation", "--disable", "view_image")
    assert image_flags == ("--enable", "image_generation", "--enable", "view_image")
    with pytest.raises(ValueError, match="supported delivery domain"):
        cli_feature_flags("other")
