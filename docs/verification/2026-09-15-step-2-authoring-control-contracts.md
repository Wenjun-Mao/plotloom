# Step 2 authoring/control contract receipt

## Scope and result

This receipt records the authoring/control group of the approved Step 2
verification work at `2cf70f7` plus this candidate. It does not claim that the
generation, media, or qualification groups are complete.

The reviewed current contract uses project-folder stores and production routes:

| Contract trigger | Required / forbidden outcome | Current exact assertion owner |
| --- | --- | --- |
| A stale project or stage revision, then an upstream story-bible edit | The stale write is `409` and preserves content; the accepted edit makes every downstream head stale | `test_canonical_conflicts_stale_downstream_and_consume_only_the_exact_draft` |
| A canonical Save names a valid draft revision but a different payload | The Save is `409`, leaves the durable draft untouched, and only matching content consumes its receipt atomically | `test_canonical_conflicts_stale_downstream_and_consume_only_the_exact_draft` |
| Draft CAS conflict, second project, Close/Open and browser restart | A stale draft cannot overwrite; drafts are project-local and Close drains the active browser writers before explicit reopen | `test_project_folder_authoring_api_persists_isolated_cas_drafts_and_exact_save_receipts`; `frontend/e2e/project-folder-close.spec.ts` |
| Profile update/selection/availability/deletion and a frozen run | Revision conflicts preserve the selected record; disabled/default profiles cannot be activated, admitted, or deleted; run snapshots and session keys remain out of project state | `test_application_profiles_freeze_run_snapshots_and_keep_session_keys_out_of_project_state`; `test_disabled_profile_remains_selected_but_cannot_be_reactivated`; `test_profile_delete_is_guarded_across_run_reservation_and_completion` |
| Archive/restore/duplicate/delete | Lifecycle CAS rejects a stale restore; duplicate replays one key, rejects a changed request, stops at the READY prefix, and wrong-title or non-quiescent deletion preserves the archived project | `test_production_runtime_owns_archive_duplicate_and_media_free_deletion`; `test_production_runtime_rejects_lifecycle_transitions_with_manual_publications`; `test_canonical_conflicts_stale_downstream_and_consume_only_the_exact_draft` |
| Approval, revoke, upstream edit, and a forged gate-set request | Approval is append-only and exact-head/gate-set bound; revoke and upstream change make it inactive; forged gate-set approval is `409`; required skipped gates do not pass | `test_storyboard_approval_is_gate_bound_append_only_and_stales_with_its_inputs`; `test_gate_result_identity_is_scoped_to_the_project_revision`; `test_required_dialogue_timing_skip_and_audio_overrun_fail_the_gate` |

The retired direct forged-receipt call is individually recorded in the
inventory as obsolete: project-folder authoring never accepts caller-supplied
gate receipts, and the current public approval boundary rejects unbound
gate-set versions instead.

## Root-cause repair

The profile availability test exposed an actual runtime defect. Disabling a
profile updated application metadata, but selection activation did not consult
that metadata and could create a new selection revision for an unavailable
profile. `ApplicationProfileRepository.activate_text_provider_profile` now
checks availability inside the same application-control transaction as its
selection CAS. ADR 0025 records that transactional contract.

## Inventory and checks

The retained-runtime inventory marks only the reviewed authoring/control
entries verified (and the individually retired forged-receipt entry). Its
pytest guard requires those entries alongside the earlier three generation
entries:

```sh
uv run --locked python scripts/retained_runtime_coverage_inventory.py --check
uv run --locked pytest -q tests/test_retained_runtime_coverage_inventory.py \
  tests/test_project_storage_authoring_control_contracts.py \
  tests/test_project_storage.py \
  tests/test_project_storage_generation_contracts.py \
  tests/test_production_project_folder_runtime.py \
  tests/test_production_project_folder_runtime_boundaries.py \
  tests/test_v2_authoring_domain.py
```

Stable-candidate checks completed without a live provider:

| Command | Result |
| --- | --- |
| `uv run --locked pytest -q` | 483 passed; one existing TestClient deprecation warning |
| `npm --prefix frontend test` | 149 passed in 16 files |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run build && git diff --exit-code -- src/plotloom/static` | passed; checked static bundle remains fresh (existing >500 kB chunk warning) |
| `npm --prefix frontend run test:e2e -- --grep 'project-folder Close'` | 7 passed |
| `npm --prefix frontend run test:e2e` | 39 passed against real FastAPI/file-SQLite offline fixtures |
| `uv build --wheel && uv run --locked python scripts/smoke_installed_wheel.py dist` | passed in an isolated installation |

The required independent Terra review was clear: it found no concrete
authoring/control issue, confirmed availability and selection CAS share one
write transaction, and confirmed that the `.local` exception only ignores
untracked Relay metadata. The reviewer also confirmed 19 verified inventory
entries (the three prior generation entries plus 16 authoring/control
dispositions) and 307 pending entries; no pending media or qualification row
was reclassified by this group.

## Remaining Step 2 work

Generation beyond its previously accepted three scenarios, media (including H3
V4 queue/restart/dispatch-uncertainty/retention), and qualification remain
pending. Unreviewed historical rows—including legacy compatibility and probe
paths outside this group—remain `pending`; this receipt does not reinterpret
them as equivalent.
