# Native Codex image-specialist loop — bounded trial receipt

**Scope.** One disposable, lawful abstract-control-room original-image job on
the production Plotloom runtime with H3 disabled. The dedicated persistent
specialist task is host-local; its identifier is intentionally not recorded
here. No retained project, selection, or Qwen/H3 backend was used.

## Transport evidence

The supported local `codex queue --thread … --message …` command first received
a no-op acknowledgement from the dedicated specialist. The production browser
then clicked **发送给 specialist** once for frozen job
`ij_74551ac59e3a47829c8091b0086cc1ef`. The specialist preflight passed and
reported one built-in ImageGen output. Queue acknowledgement was never treated
as a completion signal.

## Result and bounded failure

The specialist preserved one PNG, executor pin, and completion receipt under
the disposable project's ignored `outputs/` tree. It neither selected nor
approved the candidate. Auto-observation first saw the normal output-before-
manifest window and recorded `delivery_partial` rejections. Once the manifest
appeared it recorded `delivery_manifest_invalid`: the reference-free package
template told the specialist to emit an empty `referenceUse`, while its optional
model required a non-empty list. The durable fix permits an empty attestation
only when the frozen job supplies no identity references; identity-bound jobs
still require the exact frozen hashes.

That correction changes the package template. Rechecking the already-exported
package then correctly fails with `package_conflict`: the existing exchange
verifier compares it to its frozen original package, rather than silently
rewriting evidence to match the new contract. The observer keeps checking
transient partial delivery, but stops after this precise package conflict.

**Outcome.** This is a real one-submit transport/ImageGen result, not a
successful click-to-gallery proof. The requested result cannot be admitted
without either mutating retained evidence or spending a second ImageGen
submission, both outside this trial's authority. The staging cleanup helper
also refused a mismatched root and the staging PNG remains preserved. No
creative acceptance or candidate selection is claimed.

**Workflow fit.** This trial entered through the storyboard production
`ImageJobPanel`: its frozen v3 request is an `original` shot job with no target
or character references. It did not exercise the intended Characters
accepted-cast reference-proposal flow, which has a separate proposal target and
cast/character contract. A future bounded trial must choose that entrypoint if
the accepted-cast workflow itself is the acceptance criterion.

## Verification

- `uv run --locked pytest -q tests/test_codex_image_dispatch.py tests/test_project_storage_image_delivery_contracts.py` — 12 passed.
- `uv run --locked pytest -q tests/test_codex_image_dispatch.py tests/test_project_storage_image_delivery_contracts.py tests/test_project_storage_image_workflow.py` — 14 passed.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` — passed after the final observer reload correction; tracked static assets are current.

The observer reload after a rejected poll is independently reviewed, but does
not yet have a dedicated browser regression for rejection → reloaded state →
no further `package_conflict` polling.

## Corrected Characters evidence — deterministic only

No second ImageGen submission or native specialist command was issued for the
accepted-cast path. The actual browser command was:

```text
npm --prefix frontend run test:e2e -- --grep 'uses a cast-only production fixture through original, refinement, and restart'
```

That production-composition fixture created an accepted cast, prepared a
`character_reference_proposal`, clicked **发送给 specialist**, and observed the
actual `POST …/character-reference-proposals/{id}/send` route. Its test-only
dispatcher invokes `/usr/bin/true`, then the fixture writes one hash-valid
completion package. The gallery admitted that delivery automatically and left
it unselected until the explicit creator selection. This proves the Characters
route, explicit-send label, package/currentness admission, and automatic
accepted-delivery observation; it is not transport or ImageGen evidence.

The scoped browser command additionally runs three deterministic Characters
cases:

```text
npm --prefix frontend run test:e2e -- --grep 'Characters delivery observation'
```

Partial files are observed as `delivery_partial` and later admitted from the
same delivery path; a final-invalid completion records
`delivery_manifest_invalid` without a candidate; and a tampered frozen package
returns `package_conflict`, refreshes the gallery's durable rejected state, and
makes no further automatic refresh request over the next polling interval.
Each case asserts the actual `POST …/refresh` response and persisted result;
none uses ImageGen.

The safety regression suite verifies that cancellation and `package_conflict`
retain the local lease and nonzero queue exits become `outcome_unknown`. It no
longer uses App Server `thread/read` for release: that API reports runtime
status but cannot bind `idle` to this package's accepted queue message, so an
idle task may still have this dispatch pending. The visible desktop App Server
in this environment uses stdio and no `app-server-control` Unix socket is
exposed to Plotloom's process. The only configured identity path is the
server-owned `PLOTLOOM_CODEX_IMAGE_SPECIALIST_TASK_ID`; no running live
Plotloom instance with that value was available for a read-only task-status
probe. Starting another App Server would not establish authority over the
existing desktop task. The safe current alternative is to retain the lease
until accepted/inapplicable delivery; a future release mechanism needs a queue
receipt correlated to this job.

## Accepted-cast live trial — 2026-09-21

One newly prepared Characters refinement was sent once through the actual
browser UI against the retained technical walkthrough. It froze Mira's accepted
cast r1 (`40a97cb5877b49989e9811008624beb1965eef13fad5336c132ee1e297dbb37a`),
the parent raster (`42ec6a9e52e84a7df0e5ffe11bbd18f478f2774db16d08d105f602108d4af8e5`),
and request `ij_5de029b5a8084889af72967ae6393bc9`
(`f13ad8eb2a25b1fe771246dc7e81d75a933bfe1917716e9f9fafd260d1d27dfa`). H3
was disabled in the isolated runtime. The prior native job was verified from
its retained terminal task/result evidence, not from an idle status; its old
lease and artifacts were not changed.

The UI Send action atomically created the v4 package and schema-v2 completion
template, then recorded one queued native receipt. The specialist's package
preflight and parent-hash check passed. Its completed native turn reported a
built-in ImageGen result; the retained completion manifest records delivery
`4090f686-5e57-4478-9067-61d6f40605dc`, output
`exec-b1602196-61dc-480c-a93b-9724bb6a548e.png`, hash
`9909481b8aa670947e078428b4837c901db66d8919a840d306b0971027bb2d96`, and the
configured specialist task identity. Automatic gallery observation admitted
asset `f29892e0-48f4-467d-b8a6-9a9423a7e713` as a 1672×941 **unselected**
refinement candidate. The existing accepted cast and reference decision remain
at r1; no selection or creative approval occurred. Terminal accepted delivery
released the isolated one-worker lease.

**Observed defect, preserved rather than repaired in this bounded trial.** The
three-second automatic observer records a persistent `delivery_partial`
rejection each time it sees the specialist's normal pre-completion file set.
This run retained 25 such rejections before the valid final manifest was
admitted. The gallery consequently renders the valid candidate alongside those
historical error cards at both desktop and 390px widths. No retry, manual
refresh, deletion, or cleanup was performed. This is evidence for a separate
root-cause fix: transient delivery publication must not be persisted as a new
rejection on every poll while the same package remains in progress.

## Publication-boundary correction — 2026-09-21

The live evidence above remains unchanged. The correction makes
`completion.json`, rather than the first staged delivery byte, the durable
publication boundary. Repeated observations of an executor pin, output
directory, or output bytes without that marker now return `awaiting_delivery`
and create no delivery rows. Once the marker exists, malformed final manifests,
executor-pin/provenance mismatches, output-set/hash/raster failures, package
conflicts, and stale/currentness failures keep their existing meaningful
rejection handling.

Focused backend coverage performs three pre-final refreshes, asserts zero
stored deliveries, publishes one valid completion, and asserts exactly one
accepted delivery/candidate. The Characters browser regression performs at
least three automatic pre-final polls before final publication and asserts the
same no-growth result. The existing final-invalid and package-conflict browser
cases remain passing. The static gallery groups the retained 25 phase-unknown
historical `delivery_partial` rows into one closed audit disclosure; it does
not delete or rewrite them or claim that every old partial was transient. New
post-marker rejections persist explicit `publicationPhase: final`, and actual
rejected final deliveries remain individual cards.

The admitted ImageGen asset is independently project-managed: its served
`original` variant hashes to
`9909481b8aa670947e078428b4837c901db66d8919a840d306b0971027bb2d96`, matching
the retained completion manifest, rather than relying on the specialist staging
file. Frontend static assets were rebuilt after this gallery change.
