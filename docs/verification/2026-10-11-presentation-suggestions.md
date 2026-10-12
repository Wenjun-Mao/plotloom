# Presentation suggestions and review readability

Approved scope: [plan](../roadmap/2026-10-11-presentation-suggestions.md) and
[ADR 0161](../adr/0161-specialist-presentation-candidates.md). Baseline:
`029933f75c15a48fd82d075408960da420b59476`.

## Diagnosis and delivered contract

Intent output describes dramatic purposes; it has no presentation span contract.
Dropdown defaults cannot be inferred from action/composition kind: one source
can mix physical limits, literal words, player choice and review directions.
The new separate frozen `bridge-presentation` stage binds every exact source,
contiguous Unicode-codepoint spans and required renderings/reasons. Candidate
and immutable report stay on the durable job; delivery does not advance the
proposal, change saved intent, approve presentation or install canonical data.

The editor prefills exactly current advice marked `助手建议`, preserving authored
buffers and requiring explicit replacement when advice arrives after editing.
Saved authored presentation is not overwritten automatically. Scene grouping,
human source labels and collapsed raw/splitting tools remove duplicate default
prose. Completed intent is folded, but dirty/conflicted review stays open.
The checkbox is removed; `确认并保存呈现方式` is the existing complete CAS save
boundary. Production confirmation remains separate.

SQL layout is unchanged; no project migration/reset or frozen intent rewrite.
Author, model and trusted-code ownership are recorded explicitly in ADR 0161.

## Focused evidence

- Existing native intent plus presentation/projection tests: 55 passed (28.77s).
- New native presentation lifecycle/binder tests: 20 passed (25.94s), plus one
  mixed-role/Unicode/literal-text test in the subsequent contract selection.
- Mixed-role, creative exchange and API intent contracts: 22 passed (11.58s).
- Five focused UI files: 56 passed; additional API/panel/workflow selection:
  52 passed. Final conflict-recovery basis selection: 27 passed.
- Quick: 151 frontend files / 1,283 tests, lock/import checks and both TS checks
  passed in 11.976s before the final conflict assertion/type declaration; final
  full qualification remains authoritative for the stable candidate.
- Final focused browser run: three presentation cases and one same-project
  rebuild case passed, 24.8s Playwright / 27.863s runner. Exact save ACK/readback,
  unchanged advice, preserved intent/evidence, separate installation, native
  Shift-click splitting and reload were exercised on disposable fake data.
- Inspected real browser captures at 1280×460, 1280×768 and 1700×900: scene labels,
  readable controls, complete raw-source access and visible sticky confirmation
  bar; no horizontal overflow. These are software-fixture pixels, not real
  specialist output or creator acceptance.
- Specialist skill validator passed; `git diff --check` passed.

## Diagnosed failures and review

Initial browser advice assertion incorrectly assumed the old flat display order;
the grouped view preserves order within each scene and save order at the owner.
The corrected test asserts exact per-source text and exact ordered scene IDs,
not weaker aggregate counts. The rebuild test initially enumerated collapsed
scenes before the fresh project read completed; it now waits for the exact
source count, then operates each disclosure. First failure evidence is retained
under `output/playwright/presentation-suggestions-failure-20261011/`.

The saved-intent folding refinement required the browser test to explicitly
reopen saved intent before inspecting its save group. Independent review also
found conflict recovery could be hidden with presentation-only edits; conflict
now automatically opens it. A regression proves buffer retention, disabled save,
visible recovery and explicit adoption. GPT-6.1 Sol / Medium confirmed the fix;
no remaining actionable findings were reported.

## Stable-candidate local qualification

Qualification used the isolated checkout at
`/tmp/plotloom-presentation-qualification.yjjySh/plotloom`, keeping the live
checkout and its served frontend unchanged until activation. Implementation:
`6279b2a9`; generated assets: `d6618d21c88194d771a603b652d646344ace5903`;
final test-only API snapshot correction: `9039f850`.

The first full attempt stopped at the archived prompt reader's missing `jsdom`
dependency in the fresh checkout. Its established prerequisite,
`npm --prefix docs/prompt-pipeline-lab ci`, resolved that setup failure.
The subsequent full command passed the lock, FFmpeg/ffprobe, API-F401 lint,
archived reader, 151 frontend files / 1,284 tests and TypeScript checks. The
Python workers reported 782 passed and 780 passed / one failed; that command
correctly exited 1 after 236.385s and is not claimed as an uninterrupted pass.

The sole failure was an exact API snapshot in
`test_f5a_uses_a_distinct_source_review_api_not_the_canonical_storyboard_review`:
its expected intent-only response omitted the four new presentation fields.
The correction adds their exact values, without relaxing assertions or changing
product code. Independent review confirmed that scope. The complete failed
file then passed 7/7 in 4.59s pytest / 6.293s runner. Per the repository evidence
reuse policy, the unchanged passed suites were retained and every downstream
full gate ran without filtering:

- Deterministic production build and checked-in static parity passed.
- Browser shard coverage: 90 specs / 298 cases, shards 84/72/71/71; no gaps or
  overlap. The unfiltered browser suite passed all 298 cases in 7.5 minutes.
- Wheel build and installed-wheel smoke passed.
- Native ownership collection independently covered 1,563 pytest, 1,284 Vitest
  and 298 Playwright cases. Collection is not test execution.
- Two serialized deterministic builds matched across all seven static files.
  Compiled `workbench.js` SHA-256:
  `218bc138887f388e3060cb77b51235a2727c4faa63ddbab4563b6c8dc57f7954`.
- Compiled fixture pixels were inspected at 1280×460, 1280×768 and 1700×900;
  the owned browser reported zero console errors and warnings. Captures are
  retained in `output/playwright/presentation-compiled-*-20261012.png`.

This combined evidence completes the local software gates for unchanged
product/dependency inputs; it does not claim a fresh uninterrupted full command
at `9039f850`, hosted exact-SHA qualification or creator acceptance.
The unchanged pinned frontend development dependency tree reports one high
`source-map-js` advisory (GHSA-68fv-2mgg-jv7q, via PostCSS/Vite). No dependency
autofix was applied; separate dependency maintenance and exposure assessment
remain outside this feature. The existing bundle-size warning also remains.

## Activation checkpoint

The owner explicitly approved a brief backend activation after checks pass.
Before activation, the live specialist registry was idle and retained media
jobs in the two open projects were terminal. The valued project
`160554c7-f021-40b0-b218-b9d53412b75c` (给今天的自己) was closed; all 70 files
were hashed before the restart. Preserve that closed state and compare the
exact files after activation. Activation readback is pending.

Hosted CI is manual and will not be dispatched. No browser reload, story save,
creative approval, specialist task preparation/send or media generation is
authorized by this implementation. Product acceptance remains owner-led.
