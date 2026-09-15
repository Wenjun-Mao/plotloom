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
        "tests/backend_core/test_pipeline.py::test_pipeline_generates_traces_then_commits_all_stages_atomically",
        "tests/backend_core/test_pipeline.py::test_dispatch_marker_is_committed_before_the_provider_call",
        "tests/backend_core/test_pipeline.py::test_post_dispatch_provider_failure_is_outcome_unknown_and_is_not_replayed",
        "tests/backend_core/test_pipeline.py::test_received_provider_failure_is_known_and_not_replayed",
        "tests/backend_core/test_pipeline.py::test_response_persistence_failure_is_storage_failure_not_unknown",
        "tests/backend_core/test_pipeline.py::test_startup_recovery_recommits_complete_seals_without_a_provider_replay",
        "tests/backend_core/test_pipeline.py::test_startup_recovery_resumes_same_predispatch_attempt_identity",
        "tests/backend_core/test_pipeline.py::test_startup_recovery_reuses_durable_response_without_provider_replay",
        "tests/backend_core/test_pipeline.py::test_startup_recovery_reuses_durable_correction_response_without_replay",
        "tests/backend_core/test_pipeline.py::test_invalid_json_persists_response_before_local_parsing_quarantines",
        "tests/backend_core/test_pipeline.py::test_central_redaction_removes_third_party_adapter_echo_without_spending_another_lease",
        "tests/backend_core/test_pipeline.py::test_central_redaction_removes_third_party_provider_error_from_attempt_trace",
        "tests/backend_core/test_pipeline.py::test_exact_work_unit_repair_reexecutes_only_the_failed_shard_and_commits_atomically",
        "tests/backend_core/test_m15_attempt_lineage.py::test_two_visible_corrections_form_a_bounded_durable_lineage_then_quarantine",
        "tests/backend_core/test_m15_attempt_lineage.py::test_outcome_unknown_is_never_a_correction_source_or_blind_replay_target",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_exact_repair_rejects_nonreplayable_target_outcomes",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_exact_repair_rejects_nonreplayable_target_outcomes[0:0]",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_exact_repair_rejects_nonreplayable_target_outcomes[0:1]",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_exact_repair_rejects_stale_snapshot_and_cross_run_unit",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_exact_repair_idempotency_replay_does_not_resubmit_child",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_cancelled_exact_repair_keeps_its_scope_and_never_installs_partial_output",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_restart_requeues_the_existing_exact_repair_scope_without_partial_installation",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_exact_repair_scope_tampering_fails_closed",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_archived_source_is_not_advertised_as_exact_repair_eligible",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_tampered_child_reuse_binding_fails_closed_before_materialization",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_downstream_repair_failure_never_installs_partial_child_seals",
        "tests/backend_core/test_exact_work_unit_repair_integration.py::test_permanent_delete_removes_exact_repair_scope_after_leaf_first_lineage_cleanup",
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
    required_verified_entries.extend(
        [
            "tests/test_alpha_acceptance.py::test_alpha_cli_hides_publication_setup_failure",
            "tests/test_alpha_acceptance.py::test_alpha_cli_rejects_non_commit_sha",
            "tests/test_alpha_acceptance.py::test_alpha_cli_returns_one_for_qualification_failure",
            "tests/test_alpha_acceptance.py::test_alpha_late_qualification_failure_never_publishes_partial_review_pack",
            "tests/test_alpha_acceptance.py::test_alpha_publication_enforces_provenance_before_creating_review_output",
            "tests/test_alpha_acceptance.py::test_alpha_publication_provenance_binds_explicit_or_implicit_commit_to_clean_checkout",
            "tests/test_alpha_acceptance.py::test_alpha_publication_provenance_rejects_dirty_checkout_or_mismatched_commit",
            "tests/test_alpha_acceptance.py::test_alpha_qualification_enforces_first_pass_and_unknown_outcome_invariants",
            "tests/test_alpha_acceptance.py::test_alpha_refuses_to_overwrite_review_directory",
            "tests/test_alpha_acceptance.py::test_alpha_rejects_relative_or_checkout_review_directories",
            "tests/test_alpha_acceptance.py::test_alpha_runs_full_18_cell_fixture_matrix_writes_blinded_reviews_and_cleans_up",
            "tests/test_alpha_acceptance.py::test_alpha_source_checkout_is_bound_to_the_running_module",
            "tests/test_alpha_acceptance.py::test_codex_external_review_gate_cannot_vacuously_pass_a_smaller_manifest",
            "tests/test_alpha_acceptance.py::test_codex_external_review_gate_rejects_shape_and_each_quality_threshold",
            "tests/test_alpha_acceptance.py::test_codex_external_review_gate_uses_only_closed_secret_free_score_sheets",
            "tests/test_alpha_acceptance.py::test_codex_external_review_identity_is_derived_from_the_frozen_review_pack",
            "tests/test_alpha_acceptance.py::test_codex_external_review_rejects_non_integer_scores_and_identity_mismatch",
            "tests/test_alpha_acceptance.py::test_private_review_manifest_requires_all_six_samples",
            "tests/test_alpha_acceptance.py::test_source_profile_loader_does_not_deadlock_a_reserved_rollback_writer",
            "tests/test_alpha_acceptance.py::test_source_profile_loader_is_read_only_and_keeps_live_wal_visible",
            "tests/test_alpha_acceptance.py::test_source_profile_loader_refuses_disabled_profile_without_rewriting_source",
            "tests/test_alpha_acceptance.py::test_source_profile_loader_uses_consistent_snapshot_during_writer_checkpoint_pressure",
            "tests/test_alpha_acceptance.py::test_source_profile_snapshot_rejects_a_recreated_shm_inode",
            "tests/test_conformance.py::test_conformance_closes_prepared_repositories_when_later_initialization_fails",
            "tests/test_conformance.py::test_conformance_loader_refuses_disabled_saved_profile",
            "tests/test_conformance.py::test_conformance_runs_the_production_four_stage_loop_and_deletes_evidence",
            "tests/test_conformance.py::test_fixed_workload_preserves_storyboard_capacity_for_multi_beat_scenes",
            "tests/test_conformance.py::test_m15_cli_emits_six_receipts_on_a_passing_strict_batch",
            "tests/test_conformance.py::test_m15_cli_rejects_partial_shape_before_loading_runtime_config",
            "tests/test_conformance.py::test_m15_conformance_runs_two_profiles_three_times_through_the_real_fixture_path",
            "tests/test_conformance.py::test_m15_qualification_accepts_two_profiles_with_three_complete_samples",
            "tests/test_conformance.py::test_m15_qualification_requires_two_distinct_profiles",
            "tests/test_conformance.py::test_qualification_allows_audited_corrections_within_first_pass_budget",
            "tests/test_conformance.py::test_qualification_rejects_mixed_workloads_and_duplicate_sample_identity",
            "tests/test_conformance.py::test_qualification_rejects_true_conformance_invariant_codes",
            "tests/test_conformance.py::test_qualification_requires_stage_level_first_pass_rate_and_attempt_limit",
        ]
    )
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
