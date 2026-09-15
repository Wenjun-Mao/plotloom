"""Keep the retirement coverage inventory tied to its historical baseline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_retained_runtime_coverage_inventory_is_complete_and_current() -> None:
    root = Path(__file__).resolve().parents[1]
    required_verified_entries = [
        "tests/backend_core/test_pipeline.py::test_storyboard_audio_timing_uses_exact_frozen_repair_fact",
        "tests/backend_core/test_pipeline.py::test_cue_order_fact_rejects_rebound_membership_before_dispatch",
        "tests/backend_core/test_work_unit_persistence.py::test_duplicate_producer_artifacts_are_rejected_before_they_can_be_sealed",
        "tests/backend_core/test_api.py::test_camel_case_and_revision_conflict",
        "tests/backend_core/test_m15_profile_repository.py::test_profile_control_plane_crud_selection_revision_and_run_snapshot_isolation",
        "tests/backend_core/test_m15_profile_repository.py::test_profile_configuration_never_accepts_secret_shaped_values",
        "tests/backend_core/test_m15_profile_repository.py::test_profile_api_is_secret_free_and_pipeline_honors_requested_profile",
        "tests/backend_core/test_m15_profile_repository.py::test_profile_availability_is_revisioned_without_rewriting_snapshots_and_guards_admission",
        "tests/backend_core/test_m15_profile_repository.py::test_disabled_selected_profile_stays_selected_but_cannot_activate_or_admit_via_api",
        "tests/backend_core/test_project_lifecycle.py::test_archive_restore_and_archived_write_guards",
        "tests/backend_core/test_project_lifecycle.py::test_duplicate_copies_only_ready_prefix_and_replays_idempotently",
        "tests/backend_core/test_project_lifecycle.py::test_duplicate_stops_at_a_nonready_gap_even_if_later_stages_are_ready",
        "tests/backend_core/test_project_lifecycle.py::test_permanent_delete_requires_archived_terminal_project",
        "tests/backend_core/test_repository.py::test_project_and_stage_revision_conflicts",
        "tests/backend_core/test_repository.py::test_stage_change_marks_existing_downstream_stale",
        "tests/backend_core/test_storyboard_review.py::test_storyboard_install_records_gates_and_approval_is_append_only",
        "tests/backend_core/test_storyboard_review.py::test_upstream_edit_makes_approval_stale_and_exact_preconditions_are_enforced",
        "tests/backend_core/test_storyboard_review.py::test_gate_result_id_is_revision_scoped_across_identical_projects",
        "tests/backend_core/test_storyboard_review.py::test_forged_gate_receipt_cannot_authorize_approval",
    ]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/retained_runtime_coverage_inventory.py",
            "--check",
            *[
                value
                for entry in required_verified_entries
                for value in ("--require-verified-entry", entry)
            ],
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
