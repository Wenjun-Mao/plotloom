from pathlib import Path

from plotloom.codex_exec_profile import VALIDATOR_FILES


def test_codex_exec_validator_pin_covers_runtime_authority_and_current_sources() -> None:
    required = {
        "src/plotloom/codex_exec_contracts.py",
        "src/plotloom/codex_exec_delivery.py",
        "src/plotloom/codex_exec_files.py",
        "src/plotloom/codex_exec_profile.py",
        "src/plotloom/codex_exec_prompts.py",
        "src/plotloom/codex_exec_runtime.py",
        "src/plotloom/codex_exec_telemetry.py",
        "src/plotloom/autopilot_exec.py",
        "src/plotloom/autopilot_image_controller.py",
        "src/plotloom/autopilot_text_controller.py",
        "src/plotloom/persistence/project/autopilot.py",
        "src/plotloom/persistence/project/autopilot_bindings.py",
        "src/plotloom/persistence/project/image_source_lineage.py",
        "src/plotloom/project_storage/autopilot_validation.py",
        "src/plotloom/project_storage/creative_evidence_inventory.py",
        "services/creator_workbench/codex_exec_supervisor.py",
        "services/creator_workbench/codex_exec_supervisor_process.py",
        "services/creator_workbench/isolated.py",
        "services/creator_workbench/manage.py",
    }
    source_root = Path(__file__).resolve().parents[1]

    assert required <= set(VALIDATOR_FILES)
    assert all((source_root / relative).is_file() for relative in VALIDATOR_FILES)
