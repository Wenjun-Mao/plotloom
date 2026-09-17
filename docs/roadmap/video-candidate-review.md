# Video candidates: generate, compare, select, discard

Status: Delivered correction, implementation `2925fddc84cea4c6da88db97ac74b4280c2d8f9b`; director acceptance/push pending.
Baseline: `24fee13`; reuse existing project-owned video jobs and reviews.

## Outcome

A reviewer can generate another video for any shot, retain alternatives together,
compare them, choose exactly one for playback, and explicitly discard unwanted
candidates. No arbitrary lifetime candidate count. Backend capacity still applies.

## Contract and boundaries

- One explicit generation action creates a fresh job/candidate with frozen current
  shot, approved keyframe, profile and generation settings. Show settings before
  dispatch. Same idempotency key returns the same job; another intentional
  generation uses a new key. No automatic replay of unknown outcomes.
- Group by project and stable shot ID; distinguish stale candidates and changed
  inputs. Preserve each candidate's immutable settings, output and review history.
  A new candidate must never overwrite or deselect the current selection.
- Selecting a current, ingested candidate atomically replaces that shot's selected
  candidate. Reject stale concurrent selection intent rather than silently choosing
  whichever response arrives last. Both route and branch players use one candidate
  per shot and reset safely on selection changes.
- Present thumbnails/native playback, status, settings and review notes; allow two
  candidates to be compared without mixing audio. Keep selection explicit. No
  synchronized editor, ranking model, timeline or new production snapshot system.
- Support individual discard and confirmed "delete all except selected" for the
  current shot. The server rechecks the exact target set and selection revision.
  Never delete the selected candidate, active/unknown-outcome job, unrelated shot,
  external path, or bytes referenced by another retained asset/job.
- Discard removes availability and eligible project-managed media bytes, while
  retaining minimal job/accounting/review tombstones. No automatic backup or Trash
  framework. Deletion cannot revive a prior selection or reset dispatch accounting.
  Use the smallest crash-safe deletion workflow; interrupted cleanup must be
  recoverable without orphaning the selected asset. Existing independent snapshots
  are not rewritten. Explicitly tell users deletion is irreversible.
- Reuse current boundaries; remove obsolete code only where replaced. Split cohesive
  modules when needed, not by arbitrary line-count slicing. Add a concise ADR.

## Delivery checkpoints and evidence

1. Map existing prepare/review/selection/storage owners briefly and implement the
   smallest backend candidate operations. Test idempotency, stale selection, closed
   projects, cross-project IDs, active/unknown jobs and referenced-blob protection.
2. Add shot-scoped candidate review UI and explicit generate-another action; ensure
   late responses cannot cross project/shot navigation. Rebuild tracked static assets.
3. Real production FastAPI/file-SQLite browser journey in disposable test data:
   generate two alternatives using offline fixtures, compare/select/switch, reopen,
   discard unused candidates, and prove selected route/branch media survives. Test
   bulk deletion selection races and interrupted cleanup at the relevant layer.
4. Attended independent Terra review once stable. Run focused checks during work;
   full locked pytest, frontend tests/typecheck/build/static freshness, E2E and
   fresh installed-wheel smoke on the final candidate. Record actual results.

Codex ImageGen and the owner's H3 gateway are now authorized for useful development
verification without per-call confirmation; the old pilot caps remain historical,
not an ongoing restriction. Prefer offline regression tests and a small live check
only if needed. Do not generate merely to exercise cleanup. No Atlas/paid fallback,
gateway source changes or deployment changes. Existing valued pilot media must not
be deleted/replaced for testing; test deletion only in named disposable fixtures.

One Relay Terra-high coordinator owns serial implementation. Director handles
acceptance/push; stop for material scope changes or after two failed attempts at
the same criterion. No broad storage redesign, image-candidate redesign, staging
cleanup project, old-pilot requalification or unbounded regeneration loop.

## Correction closeout

The preserved `9348c70` candidate omitted the folder-runtime transition:
Alembic 0019 was not invoked by `ProjectStore.open(create_schema=False)`, so a
pre-change project folder could lack selection authority. The delivered bounded
transition admits only the exact format-8 pre-selection schema, runs once under
an exclusive project lease, backfills the retired latest-review projection, and
never mutates read-only inspection, a normal closed admission, restore
validation, or unsupported schemas. It adds committed production-path coverage
for transition/reopen/idempotence, explicit bulk targets and stale selection,
native audio peer pause, and crash-safe deletion retry. Exact final verification
is recorded in `docs/verification/2026-09-16-video-candidate-review.md`.
