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
assertions remain in the same journey. A subsequent correction restored the
pre-`ace33616` autosave block verbatim: its deliberate 800 ms wait lets the
second idle timer fire while the first PUT remains held, and its direct poll
then proves the coalesced title is durable. Replacing that schedule with a
response waiter had weakened this unique in-flight regression coverage; the
wait is intentional test setup, not a save-completion workaround.

## Verification

- E2E TypeScript check passed. Log:
  `.local/relay/d7adcc97-1915-413d-8b73-a43a0926c628/e2e-typecheck.log`.
- E2E TypeScript check also passed after the restoration. Log:
  `.local/relay/4be201f3-434c-4704-82b1-90d3a7f1a9c9/e2e-typecheck.log`.
- The affected journey, including the held-PATCH proof, passed serially three
  times (6.6s, 7.6s, and 7.6s) before the restoration. Log:
  `.local/relay/d7adcc97-1915-413d-8b73-a43a0926c628/project-folder-authoring-drafts-final-repeat3.log`.
- After restoring the unique in-flight autosave schedule, the affected journey
  passed serially three times (8.5s, 8.6s, and 8.5s). Log:
  `.local/relay/4be201f3-434c-4704-82b1-90d3a7f1a9c9/project-folder-authoring-drafts-restored-repeat3.log`.
- An independent attended Terra read-only delta review found no code issues. It
  confirmed exact request matching, acknowledgement-before-read ordering, held
  old/new canonical observations, and preserved CAS/autosave/restart coverage.

## Preserved adjustment evidence

The first deterministic repeat exposed a test-helper contract mistake: the
autosave PUT names its title under `payload.title`, while canonical PATCH names
it under `brief.title`. Three serial attempts timed out waiting for the wrong
request shape; their log is retained at
`.local/relay/d7adcc97-1915-413d-8b73-a43a0926c628/project-folder-authoring-drafts-repeat3.log`.
The helper was subsequently removed when the pre-`ace33616` schedule and
durability poll were restored, while the canonical PATCH helper remains for the
held-PATCH proof.
