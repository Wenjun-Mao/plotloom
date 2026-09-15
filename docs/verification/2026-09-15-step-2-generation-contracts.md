# Step 2 generation-contract receipt

## Scope and result

This receipt records the generation group of the approved Step 2 verification
work at `926aaf7` plus this candidate. It verifies current project-folder
generation behavior with offline fixtures. It neither restores the retired
shared runtime nor claims media/H3, live-provider, product, or human creative
acceptance.

The current ownership contract is unchanged:

- The author owns the project brief and reviewed canonical inputs; the model
  owns only the schema-bounded candidate content for a planned work unit.
- Trusted code owns provider-profile snapshots, prompt/schema rendering and
  hashing, deterministic topology and plans, validation/binding, correction
  limits, repair eligibility, sealed manifests, and canonical installation.
- Server and session credentials stay outside project state. Prompt, response,
  validation, and canonical trace evidence are public/redacted only.

The primary prompt schemas remain aligned with their current validators:
`story_bible.v3`, `story_graph.v3`, `scene_beats.fragment.v12`, and
`storyboard.fragment.v6`. `compile_work_unit_request` binds each rendered
prompt to its validator schema, immutable stage plan, unit inputs, and
dependencies; `DurableWorkUnitRunner` persists that contract before dispatch
and validates the returned final content. Corrections use the closed
`work_unit_correction.v19` schema and the same frozen base contract. No field
ownership or public/prompt-schema contract changed, so no ADR amendment is
required.

| Contract trigger | Required / forbidden outcome | Current exact assertion owner |
| --- | --- | --- |
| A complete four-stage direct run | The frozen profile, generation plan, deterministic topology, rendered prompt trace, validator/provider schema, every prompt/unit contract, and each seal manifest bind together before the four canonical heads install | `test_direct_generation_binds_frozen_profile_prompt_plan_topology_and_seal_provenance`; `test_direct_project_pipeline_seals_four_stages_then_installs_the_complete_prefix_atomically` |
| Invalid final content or exhausted corrections | The raw response is retained before local rejection; primary → correction lineage is durable and limited; no candidate installs after quarantine | `test_direct_generation_persists_invalid_raw_response_before_quarantining_without_install`; `test_project_generation_caps_corrections_and_keeps_durable_lineage` |
| Dispatch loss, known provider error, response persistence loss, or restart | Post-dispatch uncertainty is `outcome_unknown` and never replays; known/storage errors are terminal; pre-dispatch and durable-response recovery retain the original attempt; complete seals recommit without a provider call | `test_direct_generation_marks_ambiguous_provider_loss_unknown_without_replay_and_redacts_error`; `test_direct_generation_restarts_a_predispatch_attempt_with_its_original_identity`; `test_direct_generation_reuses_a_durable_primary_or_correction_response_without_provider_replay`; `test_direct_generation_recommits_complete_seals_after_restart_without_provider_replay` |
| Provider echo or session/profile secret | The project trace and project SQLite never retain the secret; correction prompts never reuse hidden reasoning | `test_project_generation_redacts_provider_secret_echoes_before_project_persistence`; `test_project_generation_dispatches_before_call_and_never_reuses_reasoning` |
| Exact-unit repair after one quarantined unit | Only a quarantined, current source unit can repair; HTTP idempotency submits only its newly created child; the child retains one scope over dispatched cancellation and restart, reuses immutable upstream/sibling evidence, and rejects stale or tampered bindings before materialization | `test_exact_repair_http_replay_submits_only_the_created_child`; `test_exact_repair_refuses_nonreplayable_direct_project_targets`; `test_exact_repair_rejects_stale_or_foreign_direct_project_evidence`; `test_exact_repair_keeps_one_scope_across_idempotency_cancellation_and_restart`; `test_tampered_frozen_upstream_binding_never_materializes_a_child_candidate`; `test_exact_repair_preserves_frozen_upstream_and_sibling_bindings_until_atomic_install` |
| Repair re-execution or downstream failure | Recovery reruns only the failed scene shard; valid reused evidence remains immutable; a later child failure preserves seals/evidence but installs no canonical heads | `test_exact_repair_reexecutes_only_the_failed_scene_shard_after_preseal_process_loss`; `test_exact_repair_downstream_failure_keeps_child_seals_but_never_partially_installs` |
| Admission before a text run exists | An unreachable selected backend returns `422` and creates no placeholder run | `test_unreachable_text_provider_returns_422_before_creating_a_project_run` |

## Root-cause repair

The group was pending because successful direct generation proved that plans and
seals existed, but not their cross-boundary provenance, and it lacked an
explicit post-seal/pre-commit recovery assertion. Independent review then
found three test-boundary gaps: idempotency stopped before the public submit
gate, cancellation occurred before dispatch, and prompt provenance did not
compare the rendered trace and provider schema to the validator-bound
contract. The runtime already owns and checks these values; the durable fix is
focused regressions at those production boundaries, rather than correction
machinery, a compatibility facade, or a change to generation semantics.

## Inventory and verification

The inventory now requires 30 reviewed generation entries: the three
line-by-line `01874da` scenarios plus 27 reviewed pipeline, M1.5 attempt-lineage,
and exact-repair entries. The exact-repair and M1.5 lineage source groups are
fully verified. The pipeline and work-unit source groups remain mixed because
their unrelated historical policy and compatibility cases remain explicit
`pending`; this receipt does not infer equivalence from a shared test file.

The inventory has 82 verified and 244 pending entries. The pending media,
legacy-compatibility, and other unreviewed entries retain their existing
dispositions.

Focused verification completed without a live provider:

| Command | Result |
| --- | --- |
| `uv run --locked pytest -q tests/test_project_storage_direct_generation_regressions.py tests/test_project_storage_generation_contracts.py tests/test_project_storage_work_unit_contracts.py tests/test_project_storage_exact_generation_scenarios.py tests/test_project_storage_exact_repair_regressions.py tests/test_project_storage_exact_repair_recovery.py tests/test_project_storage_generation_admission_contracts.py tests/test_project_storage.py` | 54 passed; one existing TestClient deprecation warning |
| `uv run --locked python scripts/retained_runtime_coverage_inventory.py --check` | passed |
| `uv run --locked pytest -q tests/test_retained_runtime_coverage_inventory.py` | 1 passed |

Before the review corrections, the stable candidate completed `uv run --locked pytest -q` (504 passed; one existing TestClient deprecation warning), `npm test` (149 tests in 16 files), `npm run typecheck`, and 39 offline end-to-end tests. An out-of-tree frontend production build left `src/plotloom/static/` unchanged (Vite emitted its existing over-500 kB chunk warning). `uv build --wheel` followed by an installed-wheel smoke check also passed. After the review corrections, the direct-generation and exact-repair regression files passed together (21 tests), and the inventory check and inventory test passed again.

An independent Terra semantic review found the three boundary gaps above; its
targeted re-review confirmed all three corrections and found no remaining
concrete blocker.

## Remaining Step 2 work

This is not Step 2 completion. Media/H3 V4 queueing, restart,
dispatch-uncertainty, and retention contracts remain pending, as do all
unreviewed inventory rows. The generation group is executable verification
evidence only; release and product acceptance remain separate authorities.
