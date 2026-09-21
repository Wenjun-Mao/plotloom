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

## Verification

- `uv run --locked pytest -q tests/test_codex_image_dispatch.py tests/test_project_storage_image_delivery_contracts.py` — 12 passed.
- `npm --prefix frontend run typecheck` — passed before the observer stop fix;
  the follow-up is a one-line type-safe predicate and requires the normal final
  static rebuild/check before a future trial.
