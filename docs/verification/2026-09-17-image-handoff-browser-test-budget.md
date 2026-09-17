# Image handoff browser test budget receipt

## Scope

This receipt records the test-only correction to the P1 self-contained copied
image-brief browser journey. The journey now owns a 75-second timeout; the
suite-wide 45-second default, polling, assertions, retries, fixtures, and CI
serialization are unchanged.

## Retained CI evidence

GitHub Actions run `35267485044`, retained under
`.local/relay/ci-35267485044/playwright-test-results`, exhausted the 45-second
test deadline while the multi-phase image journey was still running. Its first
attempt reached the original-delivery refresh/acceptance check at about 43.4
seconds. The retry accepted the original and refinement deliveries and reached
the final tampered-manifest flow before exhausting the same deadline.

That evidence identifies a combined-journey budget mismatch, not an accepted
delivery-state defect or an H3 startup defect. The recorded `SIGTERM`/`143` is
the timeout teardown outcome and is not independently causal evidence.

## Required regression proof

All checks ran against this test-only delta:

- `npm --prefix frontend run typecheck:e2e` — passed.
- Exact journey, serial with `--repeat-each=3` — 3 passed in 1.1 minutes
  (19.7s, 19.4s, and 19.8s).
- Direct full browser suite with `--workers=1` — 47 passed in 8.4 minutes;
  the corrected journey passed in 33.2 seconds.

The retained focused and full-suite logs are under
`.local/relay/e5337d49-b8a9-4fdb-87ba-a051a55915b8/`. An independent attended
Terra read-only delta review found no scope or evidence issue.
