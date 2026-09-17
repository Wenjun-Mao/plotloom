# CI browser serialization receipt

## Scope

This receipt covers only `.github/workflows/ci.yml`. It is a prerequisite
stabilization before F0, not a product or browser-contract change.

## Diagnosis and decision

GitHub Actions run `35257793614` ran 47 Playwright tests with two workers and
failed in three distinct journeys. The retained log records browser session
closure and timeout symptoms in the exact-repair, image-jobs, and video-pilot
journeys; it does not establish one shared application defect. Because each
worker runs a full fixture stack, CI now invokes the existing E2E command with
`--workers=1` to bound concurrent resource demand. Contention is a hypothesis;
the next remote CI run is the acceptance evidence.

On a failure, CI uploads only the generated Playwright `frontend/test-results`
and `frontend/playwright-report` directories for seven days. The workflow does
not upload credentials, settings, source data, or project-storage paths.

## Local verification

| Command | Result |
| --- | --- |
| `npm --prefix frontend run typecheck:e2e` | passed |
| `npm --prefix frontend run test:e2e -- e2e/image-jobs.spec.ts --workers=1` | 2 passed (26.9s) |
| `npm --prefix frontend run test:e2e -- --workers=1` | 47 passed (8.7m) |

Command transcripts are retained in ignored
`.local/relay/fd93cc15-233c-4e82-a1b5-675e2874f174/`. No providers were used.

## Remaining acceptance

The director must inspect the next GitHub Actions run. A local serial pass
supports the bounded-resource hypothesis but does not prove the cause of the
prior remote failures.
