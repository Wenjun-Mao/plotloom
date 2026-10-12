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

## Remaining qualification / activation

Full local qualification and deterministic generated assets are pending on the
stable isolated candidate. Hosted CI is manual and will not be dispatched.
The owner explicitly approved a brief backend activation after checks pass.
Activation requires idle specialist/task readback and unchanged valued-project
content; no browser reload, story save, creative approval or real generation is
authorized by this implementation. Product acceptance remains owner-led.
