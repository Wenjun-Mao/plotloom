#!/usr/bin/env python3
"""Build and verify the shared-runtime retirement coverage inventory.

The production tree must never import the removed facade.  This verifier keeps
the historical baseline available only as Git evidence, then requires every
removed or substantially rewritten test to be classified against a current
project-folder owner (or an explicit approved breaking-storage retirement).
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASELINE = "e658057"
RETIREMENT = "f908c51"
INVENTORY = Path("docs/verification/2026-09-14-retained-runtime-coverage-inventory.json")


@dataclass(frozen=True)
class Policy:
    disposition: str
    replacements: tuple[str, ...]
    rationale: str


RETIRED = Policy(
    "truly_retired_contract",
    (),
    "Approved breaking project-folder storage cutover removed this shared-facade-only surface; no retained-project importer, route alias, or generic media worker is supported.",
)

API_RETIRED = Policy(
    "truly_retired_contract",
    (),
    "Approved breaking project-folder storage cutover removed the legacy V1 reset endpoint and the hard-stopped generic media facade; neither has a production project-folder owner.",
)

POLICIES: dict[str, Policy] = {
    # Individual retained V2 contracts in this historical module are assigned
    # below.  This fallback covers only the two intentionally removed facade
    # endpoints, never the whole former API module.
    "tests/backend_core/test_api.py": API_RETIRED,
    "tests/backend_core/test_api_modularization_contract.py": RETIRED,
    "tests/backend_core/test_frontend_contract.py": RETIRED,
    "tests/backend_core/test_m15_migration_compatibility.py": RETIRED,
    "tests/backend_core/test_persistence_modularization_contract.py": RETIRED,
    "tests/media_jobs/test_runner.py": RETIRED,
    "tests/backend_core/test_exact_work_unit_repair_integration.py": Policy(
        "migrated_current_contract",
        (
            "tests/test_project_storage.py::test_exact_repair_lineage_is_project_owned_and_reopenable",
            "tests/test_project_storage.py::test_stale_exact_repair_and_foreign_project_routes_are_rejected",
            "tests/test_project_storage_generation_contracts.py::test_project_exact_repair_refuses_tampered_response_evidence_without_creating_a_child",
        ),
        "Manifest-bound repair runs retain exact scope, sibling reuse, stale-admission, and tamper fail-closed assertions.",
    ),
    "tests/backend_core/test_image_jobs.py": Policy(
        "migrated_current_contract",
        ("tests/test_project_storage_image_workflow.py::test_project_owned_image_handoff_isolated_across_restart_and_stales_after_intent_replacement",),
        "Project-owned image route coverage asserts delivery hashes, authority, intent currentness, review, and cross-project isolation without a shared exchange database.",
    ),
    "tests/backend_core/test_m15_attempt_lineage.py": Policy(
        "migrated_current_contract",
        ("tests/test_project_storage_generation_contracts.py::test_project_generation_caps_corrections_and_keeps_durable_lineage",),
        "Current project attempts preserve a two-correction ceiling and durable primary-to-correction lineage.",
    ),
    "tests/backend_core/test_m15_profile_repository.py": Policy(
        "migrated_current_contract",
        (
            "tests/test_project_storage_generation_contracts.py::test_application_profiles_freeze_run_snapshots_and_keep_session_keys_out_of_project_state",
            "tests/test_production_project_folder_runtime.py::test_production_runtime_uses_application_profiles_and_exact_project_routes",
        ),
        "Application-owned profiles retain selection and revision checks, freeze a run snapshot, and keep session keys outside project state while production admission selects the active profile.",
    ),
    "tests/backend_core/test_m15_story_graph_lifecycle.py": Policy(
        "existing_equivalent",
        ("tests/test_project_storage.py::test_two_project_homes_run_actual_four_stage_pipeline_and_reopen_by_project_id",),
        "The production four-stage project run asserts persisted topology-derived stage seals and reopens them from the project folder.",
    ),
    "tests/backend_core/test_managed_still_media.py": Policy(
        "migrated_current_contract",
        ("tests/test_project_storage_image_workflow.py::test_project_owned_image_handoff_isolated_across_restart_and_stales_after_intent_replacement",),
        "Current managed assets, visual intent, keyframe review, stale selection, and owned-delivery checks are exercised through project routes.",
    ),
    "tests/backend_core/test_p2_video_jobs.py": Policy(
        "migrated_current_contract",
        ("tests/test_project_storage_video.py::test_direct_h3_dispatch_persists_claims_before_provider_calls_and_never_uses_wan_ledger", "tests/test_project_storage_video.py::test_direct_dispatch_faults_and_cancel_race_never_call_provider_or_replay"),
        "The direct project video owner proves atomic application claims, dispatch ordering, unknown outcomes, non-replay, and currentness.",
    ),
    "tests/backend_core/test_pipeline.py": Policy(
        "migrated_current_contract",
        (
            "tests/test_project_storage_generation_contracts.py::test_project_generation_caps_corrections_and_keeps_durable_lineage",
            "tests/test_project_storage_generation_contracts.py::test_project_generation_dispatches_before_call_and_never_reuses_reasoning",
            "tests/test_project_storage_generation_contracts.py::test_project_generation_recovers_durable_primary_and_correction_responses_without_replay",
            "tests/test_project_storage_generation_contracts.py::test_project_generation_redacts_provider_secret_echoes_before_project_persistence",
            "tests/test_project_storage_generation_contracts.py::test_project_generation_rejects_tampered_correction_audit_before_second_dispatch",
            "tests/generation/test_work_unit_contracts.py::test_storyboard_timing_plan_rejects_rehashed_invalid_coverage",
        ),
        "Direct project execution retains dispatch-before-call, bounded correction, response recovery, reasoning separation, redaction, correction-audit hash checks, and rehashed timing-fact rejection.",
    ),
    "tests/backend_core/test_project_lifecycle.py": Policy(
        "migrated_current_contract",
        ("tests/test_production_project_folder_runtime.py::test_production_runtime_owns_archive_duplicate_and_media_free_deletion", "tests/test_production_project_folder_runtime.py::test_production_runtime_rejects_lifecycle_transitions_with_manual_publications"),
        "The production runtime owns archive, duplicate, deletion, and lifecycle publication guards through project handles and the application ledger.",
    ),
    "tests/backend_core/test_repository.py": Policy(
        "migrated_current_contract",
        ("tests/test_project_storage.py::test_two_project_homes_run_actual_four_stage_pipeline_and_reopen_by_project_id", "tests/test_project_storage.py::test_terminal_evidence_is_project_owned_without_partial_canonical_heads"),
        "Manifest-bound stores retain atomic canonical installation, project isolation, terminal evidence, and no-partial-head behavior.",
    ),
    "tests/backend_core/test_storyboard_review.py": Policy(
        "migrated_current_contract",
        ("tests/test_project_storage_image_workflow.py::test_project_owned_image_handoff_isolated_across_restart_and_stales_after_intent_replacement",),
        "Project storyboard approval and reviewed-keyframe routes assert revision-bound approval and stale-currentness guards.",
    ),
    "tests/backend_core/test_work_unit_persistence.py": Policy(
        "migrated_current_contract",
        (
            "tests/test_project_storage_work_unit_contracts.py::test_project_work_unit_claim_is_atomic_across_independent_project_handles",
            "tests/test_project_storage_work_unit_contracts.py::test_project_work_unit_seal_requires_accepted_producer_and_freezes_evidence",
            "tests/test_project_storage.py::test_terminal_evidence_is_project_owned_without_partial_canonical_heads",
        ),
        "Project generation traces preserve atomic work-unit claims, producer/seal admission, immutable evidence, and atomic canonical installation.",
    ),
    "tests/backend_core/test_jobs.py": Policy(
        "existing_equivalent",
        ("tests/backend_core/test_jobs.py::test_runner_starts_installs_and_finishes_without_name_error",),
        "This file was migrated in place: its assertions now use the explicit manifest-bound project store rather than a shared test repository.",
    ),
    "tests/test_alpha_acceptance.py": Policy(
        "migrated_current_contract",
        ("tests/test_alpha_acceptance.py::test_alpha_uses_current_profiles_and_project_folders_for_all_18_samples", "tests/test_alpha_acceptance.py::test_external_review_receipt_filters_invalid_sheets_and_private_mapping_rejects_partial_pack"),
        "Alpha keeps the 18-sample project-folder matrix, secret-free review pack, strict review schema, frozen identities, quality thresholds, and private-map completeness.",
    ),
    "tests/test_conformance.py": Policy(
        "migrated_current_contract",
        ("tests/test_conformance.py::test_conformance_runs_the_production_four_stage_loop_and_deletes_evidence", "tests/test_conformance.py::test_qualification_rejects_invariant_and_sample_identity_failures"),
        "Conformance now drives application profile snapshots and project folders while preserving qualification identity and invariant checks.",
    ),
}


API_ROUTE = Policy(
    "migrated_current_contract",
    (
        "tests/test_production_project_folder_runtime.py::test_production_runtime_uses_application_profiles_and_exact_project_routes",
        "tests/test_production_project_folder_runtime.py::test_production_runtime_preserves_structured_domain_validation_issues",
        "tests/test_project_storage_route_contracts.py::test_project_folder_static_mount_serves_the_current_workbench_index",
    ),
    "Current project-folder routes retain typed responses, bounded run lookup/progress, and actionable validation without the shared factory.",
)
API_REPAIR = Policy(
    "migrated_current_contract",
    (
        "tests/test_project_storage.py::test_exact_repair_lineage_is_project_owned_and_reopenable",
        "tests/test_project_storage.py::test_stale_exact_repair_and_foreign_project_routes_are_rejected",
        "tests/test_project_storage_generation_contracts.py::test_project_exact_repair_refuses_tampered_response_evidence_without_creating_a_child",
    ),
    "Current exact repair is project-bound, snapshot-stale aware, profile-frozen, and rejects tampered evidence before child admission.",
)
API_BOOTSTRAP = Policy(
    "migrated_current_contract",
    (
        "tests/test_project_storage_route_contracts.py::test_project_folder_bootstrap_replays_a_canonical_prefix_without_duplicate_project",
        "tests/test_project_storage_route_contracts.py::test_project_folder_bootstrap_rejects_a_noncanonical_initial_prefix",
        "tests/test_project_storage_route_contracts.py::test_project_folder_bootstrap_returns_retryable_contention_then_replays",
        "tests/test_project_storage_route_contracts.py::test_project_folder_bootstrap_recovers_an_expired_crash_reservation",
    ),
    "The project-folder bootstrap atomically installs a canonical prefix and uses an application-owned idempotency lease to reject divergent reuse, return retryable contention during initialization, and recover one expired owner without duplicating the project.",
)
API_PROFILE = Policy(
    "migrated_current_contract",
    (
        "tests/test_project_storage_generation_contracts.py::test_application_profiles_freeze_run_snapshots_and_keep_session_keys_out_of_project_state",
        "tests/test_conformance.py::test_application_profile_snapshot_refuses_disabled_or_secret_corruption",
    ),
    "Application-owned profile revisions, selection, frozen run snapshots, disabled-profile rejection, and session-key non-persistence replace shared profile control-plane tests.",
)
API_PREFLIGHT = Policy(
    "existing_equivalent",
    ("tests/backend_core/test_jobs.py::test_enqueue_then_brief_edit_fails_preflight_without_provider_cost",),
    "The project generation runner asserts stale preflight fails before an engine/provider call and creates no canonical output.",
)

ENTRY_POLICIES: dict[str, Policy] = {
    "tests/backend_core/test_api.py::test_exact_v2_route_contract": API_ROUTE,
    "tests/backend_core/test_api.py::test_canonical_schema_errors_are_actionable_422_issues": API_ROUTE,
    "tests/backend_core/test_api.py::test_request_schema_errors_are_actionable_and_never_echo_rejected_secrets": API_PROFILE,
    "tests/backend_core/test_api.py::test_run_progress_is_bounded_and_excludes_prompt_response_and_validation_payloads": API_ROUTE,
    "tests/backend_core/test_api.py::test_exact_repair_api_projects_old_parent_plan_as_ineligible": API_REPAIR,
    "tests/backend_core/test_api.py::test_exact_work_unit_repair_uses_frozen_profile_and_rejects_client_overrides": API_REPAIR,
    "tests/backend_core/test_api.py::test_camel_case_and_revision_conflict": API_ROUTE,
    "tests/backend_core/test_api.py::test_project_bootstrap_installs_a_prefix_and_replays_an_idempotency_key": API_BOOTSTRAP,
    "tests/backend_core/test_api.py::test_project_bootstrap_requires_a_canonical_initial_prefix": API_BOOTSTRAP,
    "tests/backend_core/test_api.py::test_project_creation_contention_returns_retryable_response": API_BOOTSTRAP,
    "tests/backend_core/test_api.py::test_provider_and_media_request_reject_secret_fields": API_PROFILE,
    "tests/backend_core/test_api.py::test_definite_preflight_failure_creates_no_pipeline_run": API_PREFLIGHT,
    "tests/backend_core/test_api.py::test_profile_crud_round_trips_the_trusted_adapter_selection": API_PROFILE,
    "tests/backend_core/test_api.py::test_provider_settings_merge_defaults_and_freeze_on_run": API_PROFILE,
    "tests/backend_core/test_api.py::test_profile_probe_uses_its_server_key_without_a_browser_override": API_PROFILE,
    "tests/backend_core/test_api.py::test_profile_probe_exercises_a_declared_json_schema_capability": API_PROFILE,
    "tests/backend_core/test_api.py::test_text_run_submission_requires_auth_only_for_bearer_and_can_resume": API_PROFILE,
    "tests/backend_core/test_api.py::test_provider_profile_rejects_an_impossible_text_token_budget": API_PROFILE,
    "tests/backend_core/test_api.py::test_provider_profile_partial_updates_validate_after_merging_current_values": API_PROFILE,
    "tests/backend_core/test_api.py::test_legacy_provider_settings_write_obeys_active_profile_revision": API_PROFILE,
    "tests/backend_core/test_api.py::test_legacy_provider_settings_write_rejects_a_changed_active_profile": API_PROFILE,
    "tests/backend_core/test_api.py::test_profile_delete_accepts_the_public_camel_case_revision_query": API_PROFILE,
    "tests/backend_core/test_api.py::test_static_v2_mount_serves_index": API_ROUTE,
    "tests/backend_core/test_api.py::test_stage_envelopes_rehydrate_all_canonical_payloads": API_BOOTSTRAP,
}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout


def _literal_or_source(node: ast.AST) -> Any:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_literal_or_source(element) for element in node.elts]
    if isinstance(node, ast.Dict):
        return {
            str(_literal_or_source(key)): _literal_or_source(value)
            for key, value in zip(node.keys, node.values, strict=True)
            if key is not None
        }
    try:
        return ast.literal_eval(node)
    except (TypeError, ValueError):
        return {"source": ast.unparse(node)}


def _parameter_cases(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        if decorator.func.attr != "parametrize" or len(decorator.args) < 2:
            continue
        cases.append({"argnames": _literal_or_source(decorator.args[0]), "cases": _literal_or_source(decorator.args[1])})
    return cases


def _tests_at_baseline(path: str) -> list[dict[str, Any]]:
    source = _git("show", f"{BASELINE}:{path}")
    tree = ast.parse(source, filename=path)
    return [
        {"id": f"{path}::{node.name}", "line": node.lineno, "parameterized_cases": _parameter_cases(node)}
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    ]


def _changed_test_paths() -> list[str]:
    rows = _git("diff", "--name-status", BASELINE, RETIREMENT, "--", "tests").splitlines()
    return sorted(path for row in rows if row and row[0] in {"D", "M"} for path in [row.split("\t")[-1]])


def build_inventory() -> dict[str, Any]:
    entries = []
    for path in _changed_test_paths():
        for test in _tests_at_baseline(path):
            policy_key = test["id"] if test["id"] in ENTRY_POLICIES else path
            policy = ENTRY_POLICIES.get(test["id"], POLICIES.get(path))
            if policy is None:
                raise RuntimeError(f"missing retirement coverage policy for {path}")
            entries.append({**test, "policy": policy_key})
    policies = {
        path: {
            "disposition": policy.disposition,
            "current_replacements": list(policy.replacements),
            "assertion_rationale": policy.rationale,
        }
        for path, policy in sorted({**POLICIES, **ENTRY_POLICIES}.items())
    }
    # JSON is the durable format; normalize Python tuples from literal
    # parameter cases so --write and --check compare the same representation.
    return json.loads(json.dumps({"schema_version": 1, "baseline_commit": BASELINE, "retirement_commit": RETIREMENT, "policies": policies, "entries": entries}))


def _current_test_ids() -> set[str]:
    found: set[str] = set()
    for path in Path("tests").rglob("test_*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                found.add(f"{path.as_posix()}::{node.name}")
    return found


def _current_test_sources() -> dict[str, str]:
    """Return each current test body so a replacement cannot be a name-only map."""

    found: dict[str, str] = {}
    for path in Path("tests").rglob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                body = ast.get_source_segment(source, node)
                if body is not None:
                    found[f"{path.as_posix()}::{node.name}"] = body
    return found


def check_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = build_inventory()
    if inventory != expected:
        errors.append("inventory differs from the baseline-derived source and policy")
    current_ids = _current_test_ids()
    current_sources = _current_test_sources()
    for entry in inventory.get("entries", []):
        policy = inventory.get("policies", {}).get(entry["policy"])
        if policy is None:
            errors.append(f"entry references a missing policy: {entry['id']}")
            continue
        replacements = policy["current_replacements"]
        if policy["disposition"] == "truly_retired_contract":
            if replacements or "breaking project-folder storage" not in policy["assertion_rationale"]:
                errors.append(f"retired entry lacks its approved rationale: {entry['id']}")
        elif not replacements or any(item not in current_ids for item in replacements):
            errors.append(f"current replacement is absent: {entry['id']}")
        elif not any(
            "assert " in current_sources[item] or "pytest.raises" in current_sources[item]
            for item in replacements
        ):
            errors.append(f"current replacement lacks an executable assertion: {entry['id']}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the deterministic inventory")
    parser.add_argument("--check", action="store_true", help="verify the checked-in inventory")
    args = parser.parse_args()
    inventory = build_inventory()
    if args.write:
        INVENTORY.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.check:
        errors = check_inventory(json.loads(INVENTORY.read_text(encoding="utf-8")))
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
    if not args.write and not args.check:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
