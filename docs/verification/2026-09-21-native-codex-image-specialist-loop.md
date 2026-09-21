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

The browser case intentionally does **not** yet cover partial delivery,
invalid manifest, or `package_conflict` stop-after-reload behavior for
Characters. Those remain open scoped browser regressions, not claimed proof.

The safety regression suite additionally verifies that cancellation and
`package_conflict` retain the local lease, nonzero queue exits become
`outcome_unknown`, and only an exact-task App Server `thread/read` result of
`idle` can reconcile that retained lease for a later dispatch. It does not
query the persistent specialist during this receipt update.

A read-only control-socket probe during this correction found no local Codex
App Server socket, so it produced no status and released no lease. That is the
intended fail-closed result; reconciliation is available only when the
supported status service returns the exact task as `idle`.
