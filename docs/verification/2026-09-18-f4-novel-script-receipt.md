# F4 novel-script receipt

Date: 2026-09-18. Baseline: `6b73e60426323d75f62862f35997cd8a9bc52c16`.

## Historical candidate and correction status

The prior F4 candidate remains preserved historical specialist evidence and
retains its original receipt attribution. It did **not** satisfy the corrected
F4 admission contract: prepared publication was not proven to block recovery
snapshots, format-9 folders were still admitted through generic schema paths,
the target could be interpreted as an equal three-episode duration, mapping
was only bijective rather than exact, and the review UI did not make current
JSON/report ownership fully explicit. It must not be represented as having
passed the later format-10, exact-binding, route-cap, or deferred-response
contract.

The correction preserves one upstream `script.json` as creative authority and
adds only trusted admission facts: exact ordered `sectionBindings`, frozen
graph-derived section/route caps, currentness, lifecycle blocking, and scoped
episode replacement. The author target is a hard maximum per complete route,
not a runtime requirement. Reports remain original pinned upstream derived
artifacts and visibly distinguish an edited current script from their original
candidate revision. No F5/media/TTS work, fresh creative generation, retained
pilot mutation, or human creative approval occurred.

## Attended proof and review

The disposable production-browser project `884cd1ca-11d7-4223-8f0f-05078e3173e7`
was created through the normal project API. Its final frozen package and raw
delivery remain locally under `.local/relay/3498b951-455c-4082-aeee-d7939c4fef9b/f4-live-proof/`.
The attended Terra/high specialist delivered all three sections, bound
`opening → 1`, `beacon → 2`, and `dock → 3`, with 180 seconds total / 60
seconds per section. The project technically accepted that historical delivery
as script revision 1 under the earlier contract only.

Two earlier candidate attempts were cancelled, not accepted: one invented
episodic hook/cliff claims and wrapped the derived report; the next exposed that
the frozen duration was not represented and fell back to upstream's three-minute
default. The earlier work correctly retained terminal/entry status, byte-pure
reports, and `lang: en`, but its review cannot certify a contract introduced
later. Fresh current-contract specialist proof is pending the director's next
bounded action. This remains technical/structural evidence only, not human
creative approval.

The correction itself received a separate [read-only admission-boundary
review](2026-09-18-f4-admission-correction-review.md). That review covers the
new offline contract and does not reclassify the historical candidate.

## Historical verification

- `uv run --locked pytest -q tests/test_project_storage_art.py` — historical
  pass under the earlier contract. It is not proof of this correction.
- `npm run typecheck` in `frontend/` — passed.
- `npm exec -- playwright test --config playwright.config.ts e2e/art-review.spec.ts --grep 'F4 accepts'` in `frontend/` — passed: 1 production-browser journey. It prepares, refreshes, accepts, reopens, saves one stable section, restarts, and confirms the other bound episode remains present.
- `npm run build` in `frontend/` — passed; checked-in `src/plotloom/static/` is fresh. Vite retains its existing >500 kB chunk warning.
- Final attended package: pinned `validate` passed 3 episodes / 3 scenes / 12 dialogue lines at 180s; pinned HTML re-render was byte-identical to the delivered report. This validates the original specialist package, not its later admission semantics.

`uv run --locked ruff check …` was attempted but the environment has no `ruff`
executable (`Failed to spawn: ruff`). `compileall` was used for the edited
Python modules instead; it passed.
