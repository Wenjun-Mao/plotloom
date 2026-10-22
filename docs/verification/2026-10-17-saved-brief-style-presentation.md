# Saved-Brief style presentation — October 17, 2026

## Failure and correction boundary

Trusted base: `1c59ce753618234978152e0c459a6ec828bd1898`.
Opening Art on a saved-Brief automatic project reproduced a blank root and
`TypeError: Cannot read properties of undefined (reading 'label')`.
The accepted Art contract legitimately contained `authority: saved_brief`,
`direction` and `emptyDirectionRule`, not `preset`. Art dereferenced
`preset.label`; Cast's candidate display had the same assumption.

[ADR 0163](../adr/0163-autopilot-brief-style-authority.md#frontend-review-presentation)
now explicitly covers frontend review presentation. A shared frontend union
models the existing saved-Brief and stage-specific manual-preset shapes. Both
pages display the candidate's frozen authority, or the accepted authority only
when no candidate exists. Empty directions use the frozen discretion rule;
missing direction is disclosed, not converted to a photographic preset.
Manual preset labels and Cast direction presentation remain unchanged.

The actual diff is limited to frontend types, presentation, tests, one regenerated
JavaScript asset and documentation. Backend/API schemas and request payloads,
persistence, admission, authentication, provider/prompt behavior, package/build
dependencies and build tooling are unchanged. Independent review confirmed that
boundary and found no implementation defect. Its non-blocking candidate-versus-
retained-authority coverage gap was closed with four additional unit cases.
Initial correction `1acfd0a5` removed the live blank screen. Live inspection
also caught an accepted Cast style caption hardcoded as confirmed; the follow-up
uses the existing revision/hash-bound adoption label. Its browser fixture now
checks AI-adopted provenance on a cancelled run. Independent targeted review
found no defect in that follow-up.

## Risk-scoped local frontend qualification

This uses AGENTS' bounded frontend policy, not a full backend/release rerun:

- Focused Art/Cast presentation unit tests: 42/42 passed before the additional
  four precedence cases; the final unfiltered suite includes all 46 cases.
- Final unfiltered `npm --prefix frontend test`: **1,401/1,401**, 159 files,
  final native session `38193`, completion `468024`, exit 0.
- `npm --prefix frontend run typecheck` and `typecheck:e2e`: passed. Browser
  TypeScript also passed again with the final pixel/navigation invocation.
- Two `npm --prefix frontend run build:deterministic` builds produced identical
  sorted SHA-256 trees, final session `27761`, completion `80e993`, exit 0.
  Workbench JavaScript SHA-256:
  `3c4435c428604c7c23365a1b3c2e69674fa3b9a06948f014a44d204d524dc9dd`.
- Final selected browser regressions: **17/17**, session `52823`, completion `176ca3`:
  `autopilot-guidance`, `art-review`, `cast-render-choice`,
  `recommended-art-workflow`, and `recommended-cast-workflow` specs.
- The final saved-Brief navigation/pixel case is included in those 17. An earlier
  standalone 1/1 pass, session `27550`, remains retained as overlapping evidence,
  not an additional unique browser case. Browser reads through Art and
  Characters caused no writes or provider calls.
- Root inspected Art and Cast captures at 1280×768, 1280×460 and 1700×900.
  Authority and direction remain readable without the root-render crash.
- Native module ownership discovery and whitespace checks passed; discovery
  executed no test bodies. Existing Vite chunk-size and NO_COLOR warnings were
  retained, not suppressed.

Private logs, immutable original diagnosis and desktop captures are retained
under `.local/art-saved-brief-render-20261017/`. The complete Python suite and
unfiltered browser suite were not rerun for this presentation-only change.
Hosted CI remains separate and unverified; these are local software checks,
not creative acceptance or a completed story walkthrough.

## Runtime preservation

The owner requested stopping the real automatic run before this fix. The
supported cancel control stopped the run and local worker; adopted text and
delivered references were retained. One already-dispatched image has an unknown
remote outcome, with its original reservation preserved. It was not retried,
cleared or falsely classified as never started.

Activate only the same installation's checked frontend assets and verify both
live pages. Its existing revalidating static-file mount reads the checked assets
per request, so this frontend-only change does not require restarting the app or
generation host. Keep the cancelled run stopped; do not rewrite its frozen
policy, resume generation, change settings or auto-accept media as part of this
fix. The older manual project and unrelated work remain unchanged.
