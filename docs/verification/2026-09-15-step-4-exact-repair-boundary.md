# Step 4 exact-repair parent-evidence boundary

Captured 2026-09-15. This is a local engineering verification record, not a
repeat of the retained pilot and not evidence that Step 4's creative or media
acceptance has completed.

## Root cause and ownership

Read-only inspection of retained project `ae4595cf-2bcc-480a-839b-af3a8901240c`,
run `2326517e-9e51-4771-aa15-eeeecb3382bd`, found Scene Beats #1–#6 succeeded,
#7 quarantined, and #8 queued with no candidate. The old exact-repair admission
attempted to freeze every non-target sibling as reusable. Its one-candidate
requirement therefore failed on queued #8; it did not prove that #7's rejected
attempt/response/validation lineage was invalid.

The durable ownership boundary is now:

- the server freezes only successful sibling candidates with accepted,
  hash-consistent producer evidence;
- a queued parent sibling is a scope-hashed pending child unit and must execute
  before the repaired aggregate seals;
- failed, cancelled, running, and outcome-unknown siblings reject admission;
- upstream candidates are selected from the sealed aggregate manifest after
  its stored hash is verified, never by timestamp; and
- the target remains bound to its original rejected evidence and receives only
  the normal bounded child correction contract.

ADR 0015 records this contract. Prompt/continuity content was inspected only
to confirm the original model-output rejection; no prompt-contract change is
included here.

## Executed local evidence

`uv run --locked pytest tests/test_project_storage_exact_repair_regressions.py tests/test_project_storage_exact_repair_recovery.py -q`
passed: 17 tests. The new deterministic production-owner regression proves
accepted siblings are reused, a quarantined target plus an undispatched sibling
execute in the child, all stages seal, and canonical installation remains
atomic. It also covers sealed-manifest hash tampering and non-replayable sibling
states.

`uv run --locked python -m compileall -q src/plotloom tests` passed.

Frontend unit tests (149), TypeScript typecheck, production build, generated
static freshness, `uv build --wheel`, and the fresh installed-wheel smoke all
passed. The frontend build emitted its existing >500 kB chunk-size warning.

The full Python suite reached the pre-existing extraction-environment failure
`tests/test_extraction_contract.py::test_clean_repository_has_only_declared_product_roots`:
undeclared local root `.playwright-cli`. It is outside this scoped delta and
was preserved; this record does not claim the full-suite gate passed.

## Acceptance disposition

The source repair boundary is locally verified. The retained live project and
its frozen profile/evidence were not mutated, no provider request was made, and
no pilot was replayed. Step 4 remains blocked pending an explicitly attended,
sanctioned live continuation and its separate creative and audiovisual review.
