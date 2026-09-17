# Durable draft canonical-save synchronization receipt

Date: 2026-09-17. Scope: `project-folder-authoring-drafts.spec.ts` only.

## Root cause and correction

The durable-draft journey read `GET /api/v2/projects/{id}` immediately after
clicking **保存简报**. The click begins an asynchronous canonical `PATCH`, so
the direct GET could observe the prior canonical Brief even when the write later
succeeded. This was a test-observation race, not a persistence defect.

Each immediate-read canonical-save boundary now registers its response waiter
before the click, matches the exact project pathname, PATCH method, and intended
Brief title, then requires an OK response carrying that title. A held-PATCH
proof reads the old canon before release and the new canon after the acknowledged
response. The existing draft CAS, autosave, conflict, consumption, and restart
assertions remain in the same journey; the prior sleep and polling were removed.

## Verification

- E2E TypeScript check passed. Log:
  `.local/relay/d7adcc97-1915-413d-8b73-a43a0926c628/e2e-typecheck.log`.
- The affected journey, including the held-PATCH proof, passed serially three
  times (6.6s, 7.6s, and 7.6s). Log:
  `.local/relay/d7adcc97-1915-413d-8b73-a43a0926c628/project-folder-authoring-drafts-final-repeat3.log`.
- An independent attended Terra read-only delta review found no code issues. It
  confirmed exact request matching, acknowledgement-before-read ordering, held
  old/new canonical observations, and preserved CAS/autosave/restart coverage.

## Preserved adjustment evidence

The first deterministic repeat exposed a test-helper contract mistake: the
autosave PUT names its title under `payload.title`, while canonical PATCH names
it under `brief.title`. Three serial attempts timed out waiting for the wrong
request shape; their log is retained at
`.local/relay/d7adcc97-1915-413d-8b73-a43a0926c628/project-folder-authoring-drafts-repeat3.log`.
The corrected helper now matches the autosave payload contract separately.
