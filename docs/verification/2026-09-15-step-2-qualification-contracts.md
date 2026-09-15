# Step 2 qualification-tools contract receipt

## Scope and result

This receipt closes the Alpha, conformance, and public external-review coverage
group in the approved Step 2 plan. It is an offline behavioral qualification of
the current project-folder runtime. It did not call a live provider, generate a
product candidate, or claim Alpha, human, or creative acceptance.

The root cause was coverage loss during shared-runtime retirement: current tests
exercised successful disposable runs but several retired failure triggers were
only mapped to broad happy-path tests. The runner contracts themselves already
own the required behavior. This change restores direct assertions at those
owners instead of restoring `SQLiteRepository`, copied source databases, or any
removed shared-runtime API.

| Contract trigger | Required / forbidden outcome | Current exact assertion owner |
| --- | --- | --- |
| Two profiles × three stories × three repetitions | Exactly 18 opaque, secret-free receipts with deterministic profile/story/repetition cells; each successful receipt has all four first-pass stages, one attempt per unit, and temporary project evidence is deleted | `test_alpha_uses_current_profiles_and_project_folders_for_all_18_samples` |
| Missing, malformed, unknown, cancelled, or quarantined Alpha samples | Incomplete matrix/score structures fail closed; unknown is an invariant breach; every non-`succeeded` terminal state fails completion | `test_alpha_qualification_fails_closed_for_missing_incomplete_and_non_success_samples` |
| Alpha corrections and canonical installation | Six corrected stages may consume the per-profile first-pass budget exactly; a seventh fails; a succeeded run missing any canonical stage is invariant-invalid | `test_alpha_qualification_counts_corrections_against_each_profile_first_pass_budget`; `test_alpha_invariant_codes_require_an_atomic_four_stage_install` |
| Review-pack publication and provenance | Dirty/mismatched source provenance, unsafe destination, late qualification failure, or invalid CLI commit never exposes a partial pack or private setup details | `test_alpha_never_publishes_a_partial_review_pack_after_late_qualification_failure`; `test_alpha_provenance_is_bound_to_the_running_checkout_and_clean_head`; `test_alpha_provenance_failure_precedes_review_output_and_cli_rejects_bad_commit` |
| Engineering score sheets | Only frozen six-sample, closed, prose-free sheets count; malformed, undersized, and identity-mismatched inputs fail; the result is an engineering receipt, never a product Approval or human acceptance | `test_external_review_gate_enforces_quality_thresholds_and_full_manifest`; `test_external_engineering_review_is_not_a_product_approval_or_human_acceptance` |
| Conformance profile/repetition matrix | Current saved application profiles produce isolated disposable project stores; receipts have the complete public shape and M1.5 samples are deterministically 1–3 for each profile | `test_conformance_runs_the_production_four_stage_loop_and_deletes_evidence`; `test_m15_conformance_uses_two_current_application_profiles` |
| Conformance failure boundaries | Duplicate/mixed identities, missing samples, true install invariants, first-pass shortfall, attempt limit, unknown/cancelled/quarantined results fail; audited corrections inside budget pass | `test_qualification_enforces_first_pass_attempt_and_identity_boundaries`; `test_qualification_rejects_true_install_invariants_and_missing_samples`; `test_qualification_allows_audited_corrections_within_the_first_pass_budget` |
| Application-profile read boundary | A direct `mode=ro` transaction sees one profile snapshot under WAL/checkpoint pressure, reads while a rollback writer is reserved, leaves database/WAL data unchanged, and rejects disabled or secret-shaped records | `test_saved_profile_snapshot_reads_a_live_wal_without_mutating_application_files`; `test_saved_profile_snapshot_uses_one_transactional_view_during_a_writer_update`; `test_saved_profile_snapshot_reads_consistently_while_a_rollback_writer_is_reserved`; `test_application_profile_snapshot_refuses_disabled_or_secret_corruption` |

## Individual retirement rationale

`test_source_profile_snapshot_rejects_a_recreated_shm_inode` is individually
`truly_retired_contract` in the inventory. The breaking project-folder storage
transition removed the copied SQLite/WAL/SHM snapshot pair; current qualification
reads one direct query-only SQLite transaction, so there is no copied SHM inode
whose replacement can be validated. The retained direct-owner tests instead
cover the live-WAL, consistent-snapshot, and reserved-writer requirements. SQLite
may update reader coordination bytes in its SHM file; application database and
WAL data remain unchanged.

## Inventory and verification

All 23 Alpha and 13 conformance baseline entries from `e658057` now have an
individual verified disposition and exact current assertion owner. The inventory
guard requires those 36 entries, leaving generation and media entries unchanged.

The attended independent Terra review was clear. It found no concrete issue in
the individual mappings, direct read-only application snapshot rationale, or
the Alpha/conformance failure-boundary assertions.

All checks ran without a live provider:

| Command | Result |
| --- | --- |
| `uv run --locked pytest -q tests/test_alpha_acceptance.py tests/test_alpha_qualification_contracts.py tests/test_alpha_review_templates.py tests/test_conformance.py tests/test_application_profile_snapshot_contracts.py tests/test_retained_runtime_coverage_inventory.py` | 35 passed |
| `uv run --locked python scripts/retained_runtime_coverage_inventory.py --check` | passed |
| `uv run --locked pytest -q` | 502 passed; one existing TestClient deprecation warning |
| `npm --prefix frontend test` | 149 passed in 16 files |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run build -- --outDir ../.local/relay/step2-qualification/static-build` plus `diff -ru src/plotloom/static .local/relay/step2-qualification/static-build` | passed; tracked bundle is fresh (existing >500 kB chunk warning) |
| `npm --prefix frontend run test:e2e` | second full run: 39 passed. The first full run had one unrelated provider-profile deletion timeout (38 passed); its serial exact retry passed before the clean full rerun. |
| `uv build --wheel --out-dir .local/relay/step2-qualification/wheel --clear` plus `uv run --locked python scripts/smoke_installed_wheel.py .local/relay/step2-qualification/wheel` | passed in a fresh isolated installation |

## Remaining Step 2 work

This is not Step 2 completion. Generation and media/H3 V4 contract groups remain
pending, as do all unrelated inventory entries. Alpha and conformance coverage
is executable evidence only; a future Alpha run and any human creative judgment
remain separate authorities.
