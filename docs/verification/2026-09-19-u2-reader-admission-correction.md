# U2 reader admission correction receipt

Date: 2026-09-19. Scope: the read-only `story-prototype` frontend surface only.

## Root cause and correction

The earlier reader made storyboard-review retrieval and exact currentness a
global page prerequisite, even though the canonical graph and accepted screenplay
already provide a complete screenplay-reading contract. It also rendered the
full storyboard after the full screenplay. This mixed independent admission
contracts and let an unavailable storyboard hide a valid screenplay.

The corrected reader admits screenplay from only the accepted screenplay and
current graph binding. Storyboard review is checked asynchronously and locally;
it appears only in the focused storyboard view when it has the exact current
script, graph, and section binding. Missing or stale review shows a local honest
state. Route and shared-opening focus persist across the view switch.

## Focused evidence

- `npm test` in `frontend/`: 18 files, 165 tests passed.
- `npm run test:e2e -- story-prototype.spec.ts` in `frontend/`: 3 passed. It
  covers an F4-only two-scene episode with distinct scene context and lines, a
  valid storyboard route with collapsed prompt disclosure and no appended
  screenplay, and stale storyboard local refusal while the edited screenplay
  remains readable. The browser observer recorded no API writes after loading.
- `npm run build:deterministic` in `frontend/`: passed and refreshed
  `src/plotloom/static/`.

## Visual inspection

Reviewed Playwright captures at 1440 px and 768 px for the focused storyboard,
and 1440 px and 720 px for the F4-only screenplay. At 720 px, cards collapse
to one column without horizontal clipping; at desktop width, the selected
reader is presented without the other reader appended below it. These captures
are technical layout evidence, not creative or media acceptance.

## Independent review

An attended independent Terra read-only review of committed implementation
`e2f9b390c1adf421be2cedff702a7c8e0ccb42ad` approved the exact delta with no
findings. It inspected the retained F4-only preview and confirmed independent
screenplay admission, local storyboard refusal, mutually exclusive views,
route/opening preservation, creator-facing terminology, sandboxed report, and
absence of page mutation paths. It did not rerun checks or alter source.

## Exclusions

No backend, schema, prompt, provider, generation, production-media, report
sandbox, or persistence behavior changed. No valued project was modified; E2E
used disposable technical projects only.
