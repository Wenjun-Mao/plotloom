# Storyboard and production guide qualification

> Only QA artifacts listed in the [2026-10-25 cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md)
> were retired. References to those artifacts describe historical
> runs, not available files or current launch/recovery instructions.
> Recorded outcomes and limits stand.

Trusted integrated baseline: `038b46850e5a4f2b31d7a251d56eff5fe6af0cf5`.

## Root cause and correction

The Storyboard guide was generic even when there was no candidate or when an
accepted candidate could not yet prepare production. Confirmation of the
Storyboard is not evidence of proposal preparation or installation readiness.
The existing Storyboard and nested production owners already know those states.
Observe both owners, scoped to project/revision/page, without additional API
reads or any change to approval, projection, generation or playback semantics.
Name the actual enabled preparation, review, intent, presentation, installation
or same-task delivery-check control; preserve failed/loading/retained states.

The actual diff and dependencies were reviewed against the trusted baseline:
no backend/API schema, request payload, persistence/admission/authentication,
provider/prompt behavior, package contract, dependency or build-tool changes.
Native ownership and shard allocation add only the new tests. ADR 0156 applies;
the baseline full gate's unchanged Python/package evidence is reused.

## Executed verification

- `uv run --locked --no-sync python scripts/verify.py quick`: exit 0, 11.214s;
  all 1,214 Vitest cases / 147 files, both type checks, lock and API F401 pass.
- Two new focused Vitest files: 13 cases pass. Owner reads remain one per owner
  in the mounted harness; project switching, A-B-A, page exit and failed retained
  refreshes cannot publish stale observations.
- Explicit browser selection: `recommended-storyboard-workflow`,
  `recommended-script-workflow`, `production-bridge-shot-handoff` and
  `production-bridge-review-refresh`: all seven cases pass, 18.2s. The new browser
  read-count assertion initially assumed the harness's mount lifecycle; corrected
  it against existing development StrictMode (Storyboard effect replay reaches
  two reads, bridge layout replay aborts before the first request reaches server).
  No production effect or coverage was weakened to accommodate the assertion.
- Native ownership discovery passes: 1,518 pytest / 157 files, 1,214 Vitest /
  147 files, 294 browser / 89 specs. No Python test bodies ran for this UI delta.
- Four-shard guard: 83/70/70/71 cases, zero gaps or overlap.
- Deterministic static build and second-build tree comparison pass; SHA-256
  `b3cf32ec48f8923d5d70ba1f4e33c07d3629764180fe9d8b9965bfee2406cf7c`.
- Desktop pixels inspected at 1280x460 and 1700x900, with additional 1280x768
  screenshot retained. Guide remains visible beside the actual confirmation
  control, and accepted state names the visible production preparation button.
- Independent read-only review found two availability mistakes (disabled queued
  controls and incomplete installed-cut coordinates). Both were fixed using
  the controls' availability and shared `bridgeCut` predicate, with negative
  regressions. Fresh review reran 13 cases and found no remaining issues.

Screenshots are under
`frontend/test-results/recommended-storyboard-wor-feed9-dent-production-preparation/`.
Owner normal8841 reload also shows the actual proposal preparation instruction;
proposal r1 was prepared through the UI. Software qualification is separate
from creative acceptance and final-media playback. Hosted latest-SHA CI is
still pending publication; no hosted success is claimed here.
