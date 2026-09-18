# F4 novel-script receipt

Date: 2026-09-18. Baseline: `6b73e60426323d75f62862f35997cd8a9bc52c16`.

## Delivered contract

F4 stores one upstream `script.json` as creative authority with only a
top-level `sectionBindings` extension. It binds the three F1B IDs one-to-one
to upstream episode slots and permits a reopened author to replace one bound
episode without overwriting the other accepted sections. The script binding
freezes source, accepted outline, map, installed graph, cast, art, and the
author-owned total playthrough target. A transient upstream outline projection
supplies only those stable section summaries, cast IDs/names, and target timing
needed by the pinned upstream script tools; the original accepted outline stays
frozen separately and no Bible/Shot/legacy Scene Beats translation is added.

Prepared script publication blocks close/archive/delete/snapshot through the
shared lifecycle blocker and cancellation refuses later admission. Reports are
byte-pure pinned upstream renders. Plotloom, rather than the upstream report,
labels hook/cliff and duration output as structural-only and product-inapplicable
for this non-episode pilot. F5's seam is the accepted upstream JSON plus
`sectionBindings`; no F5/media/TTS work or retirement was performed.

## Attended proof and review

The disposable production-browser project `884cd1ca-11d7-4223-8f0f-05078e3173e7`
was created through the normal project API. Its final frozen package and raw
delivery remain locally under `.local/relay/3498b951-455c-4082-aeee-d7939c4fef9b/f4-live-proof/`.
The attended Terra/high specialist delivered all three sections, bound
`opening → 1`, `beacon → 2`, and `dock → 3`, with 180 seconds total / 60
seconds per section. The project admitted and explicitly technically accepted
the delivery as script revision 1.

Two earlier candidate attempts were cancelled, not accepted: one invented
episodic hook/cliff claims and wrapped the derived report; the next exposed that
the frozen duration was not represented and fell back to upstream's three-minute
default. The durable correction records terminal/entry status in the required
upstream fields, preserves byte-pure reports, freezes `lang: en`, and carries
the project target through the execution projection. The final independent
Terra/high read-only review found no P0–P2 issues in source/consequence/context,
IDs, exact bindings, timing, inapplicability wording, hashes, or renderer
reproducibility. This is technical/structural evidence only, not human creative
approval.

## Executed verification

- `uv run --locked pytest -q tests/test_project_storage_art.py` — passed: 6.
  Includes F4 whole-pilot candidate/accept, scoped opening edit preserving the
  other ending, cancellation/late-delivery rejection, restart, and lifecycle
  blocker coverage.
- `npm run typecheck` in `frontend/` — passed.
- `npm exec -- playwright test --config playwright.config.ts e2e/art-review.spec.ts --grep 'F4 accepts'` in `frontend/` — passed: 1 production-browser journey. It prepares, refreshes, accepts, reopens, saves one stable section, restarts, and confirms the other bound episode remains present.
- `npm run build` in `frontend/` — passed; checked-in `src/plotloom/static/` is fresh. Vite retains its existing >500 kB chunk warning.
- Final attended package: pinned `validate` passed 3 episodes / 3 scenes / 12 dialogue lines at 180s; pinned HTML re-render was byte-identical to the delivered report.

`uv run --locked ruff check …` was attempted but the environment has no `ruff`
executable (`Failed to spawn: ruff`). `compileall` was used for the edited
Python modules instead; it passed.
