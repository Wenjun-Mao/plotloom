# Whole-pack material review qualification

Status: focused qualification complete; final full gate, publication and activation
pending. This record does not claim creative acceptance.

Scope: [approved plan](../roadmap/2026-10-17-bulk-material-review.md) and
[ADR 0191](../adr/0191-whole-pack-human-material-confirmation.md). Baseline
`f2858efa1b93854fe299cd97e2c839f5c763c6ed`; one serial source writer, then manager
handoff. Requested worker and independent-review settings were GPT-6.1 Sol / High;
native effective settings were not exposed. No media generation was performed.

## Contract and review

The original bottleneck was the shared authored-observation contract, not just
required-field markers. V3 records exact scoped structured human confirmation,
without invented prose/name. All frame/reference targets and resulting native
approval/intent/binding/review facts are receipt-linked. Fail/hold blocks the
atomic handoff; authorized uncertainty remains explicitly unassessable. The
ordinary detailed manual contract stays strict. Confirmation creates no video.

Independent review found one production issue: unconstrained canonical shot text
was concatenated into the 2,000-character authored-intent type. The correction
uses a separate exact source-endorsed intent, with native saved revision/hash/shot
validation and HANDOFF-only creation; authored edits retain their existing bound.
The reviewer closed that finding and found no further production defect after
checking impacted receipt/admission/snapshot readers. Source-binding revision
checks and missing retained-original pixel blocking were included in the recheck.

Frozen production-file manifest SHA-256:
`000beddc17afa36524320e19b24679c228c2749e11a468f7f0f70afd74383b97`.
It was independently checked against all listed files. Evidence is under ignored
`.local/verification/2026-10-18-bulk-material/`, including the file manifest,
selected-run logs, deterministic asset check and `whole-pack-42-gallery.png`.
The manager inspected that desktop capture: readable three-column cards and no
required per-frame form exposed by default. Fixture pixels are not creative QA.

## Executed focused checks

All commands use the checked lock and repository verification owner.

| Selection / tier | Result |
| --- | --- |
| `focused --pytest tests/test_bulk_material_handoff.py` | 20 passed; explicit API request, hostile scope/links/source text/revision, long-source handoff/reopen/repeat, manual source-authority refusal |
| `focused --pytest tests/test_bulk_material_handoff.py --pytest tests/test_cross_shot_handoff.py` | 22 passed on corrected source; latest review and cross-shot/shared intent boundaries |
| `focused --pytest tests/test_bulk_material_realistic_pack.py` | One passed, 108.17s: 42 frames/five reference sets, genuine native validator/geometry lineage, mixed human/provisional frames, multiple/no characters, separately authorized uncertainty, zero video jobs |
| Three exact retained/detailed selectors in `test_autopilot_creator_confirmation.py` and `test_autopilot_handoff.py` | Four passed; original v1 bytes/hash/recovery and current unnamed detailed/API behavior |
| `focused --vitest tests/bulk-material-review.test.ts --playwright e2e/autopilot-review.spec.ts` | Six frontend and 18 browser cases passed, including 42-frame zero-typing action, cancellation, stale/read-only/read failures, lost acknowledgment, current/original pixel failure and retry |
| `quick` | Passed in 13.135s; lock, API unused-import check, all 1,407 frontend cases and both type checks |

The realistic fixture initially copied the newly code-owned source endorsement
into a manual fixture binding; the HANDOFF-only guard correctly refused it. The
fixture now authors that one manual intent explicitly. No production guard was
relaxed. A reviewed three-module `contract` union was started before the source
correction, then its exact owned process group was interrupted and confirmed
settled (exit 130). Its log is retained; it is **not** a module pass. Focused
corrected-source checks above replace affected old-input evidence; no second
broad module run was started. Existing non-fatal Starlette deprecation warnings
remain separate from passing results.

## Real-data read-only preflight before full qualification

The manager ran the existing Docker image with `--pull=never --network none
--read-only`, mounting both retained source and the installation read-only and
setting `PYTHONPATH` to retained `src`. `ProjectStore.open(exact_home,
read_only=True)` and `review_material(store)` passed (session 25168, exit 0).
No application-store initialization, migration, bridge, provider or write path ran.

Project `a99d5422-61fd-4768-89f4-118e82bbed75` remains revision 461. The new review
envelope is v2, five reference sets / 42 frames / 42 saved intent contexts, hash
`a2fa6d670e3f0030e6377b17185ce3d4d5867b3009e51e37c9842aeeb0d3a202`.
This additive displayed context changes the review hash; an old open form must
not be reinterpreted as new bulk consent. The original generated run bundle hash
remains `d456e177cddef11fdf301268547b20c2e07dd6294da975b76505574b108cd6c1`.

The owner's later disposal policy permits removal without backup/recovery of
identified incompatible development projects; no compatibility machinery was
added for retention. This project is compatible and needs no reset. Pre-work
read-only evidence contains 82 tables / 1,729 rows and 436 substantive payloads
(excluding database sidecars and lease locks); host state was 78 completed
attempts plus one retained outcome-unknown, no queues/validators, and no live
process for that UNKNOWN attempt's recorded PID. Recheck current activity before
any restart; these observations alone are not permission to erase or settle it.

## Final-gate fixture correction

The full attempt at `200a1c78ec004b573de8699f937323909528aa05` ended with exit 1:
3,231 Python cases passed and six failed. Original failure evidence remains in
`.local/verification/2026-10-18-bulk-material/full-200a1c78.log`.
All six failures came from the minimal profile-provenance fixture missing
`v2_visual_intents`. The real validator now always reads `(id, project_id, intent)`
to reject orphaned source endorsements; the fixture explicitly models only the
columns read by real validators and omitted that empty collection. Its existing
empty approval/review collections establish the same fixture convention.

The correction adds only `v2_visual_intents: id,project_id,intent` to
`tests/autopilot_profile_fixtures.py`. Production checks, missing-table behavior
and assertions remain unchanged. The schema-seeding consumers are bindings,
receipts and transactions; the construction tests import only the unchanged
construction observer.

Executed the affected selection, including all six original failures:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_autopilot_profile_bindings.py \
  --pytest tests/test_autopilot_profile_receipts.py \
  --pytest tests/test_autopilot_profile_transactions.py
```

Result: 35 passed in 8.45 seconds; verification exit 0, 11.996 seconds total.
Log: `.local/verification/2026-10-18-bulk-material/profile-fixture-correction-200a1c78.log`.
`git diff --exit-code HEAD -- src frontend/src` confirmed production bytes stayed
unchanged. This test-fixture-only correction does not establish a new full pass:
the manager reuses unchanged passed evidence and owns the remaining unfiltered
downstream gates. No second full run, publication or live operation was performed
for this correction.

## Final release and activation

Pending: one stable `uv run --locked --no-sync python scripts/verify.py full`,
normal push after divergence checks, positive idle proof, same-installation
activation and post-start readback. No live creative approval, generation,
deletion, reset or UNKNOWN settlement has occurred. Hosted CI remains separate.
