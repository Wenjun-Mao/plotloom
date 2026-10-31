# Whole takes for branching-game playback

## Current status

The whole-take implementation and independent source review are complete. Root owns final local qualification from the clean `a4d8c917` baseline on local main. The approved scope is H3 production, normal and batch selection, retained playback, standalone export, and a small read-only restriction scan.

| Claim | Evidence | Fresh media | Status |
|---|---|---|---|
| A shorter or longer original remains eligible | Real API selection, source-bound reopen/restore and byte comparisons on both sides of the target. Within 15% is quiet, outside is advisory. | No | Passed with offline H3-shaped media and frontend threshold tests |
| The player uses the full clip and follows its natural end | Export retained eight-second originals for three-second targets. Resume past the target and follow the opening, choice and ending in Chromium. | No | Passed. All 18 clips ended at eight seconds on the exercised route. |
| Frozen identity and media integrity remain verifiable | Request catalog and prompt checks, native A/V, selected bytes, source currentness and tamper refusal. Preserve explicit trims. | No | Passed focused checks. All 15 original Last Projection takes passed unchanged. The previously selected project restored and re-exported the original 13,053,452-byte ZIP with the same digest. |
| Local qualification | Stable candidate, complete local suite and exact packaged assets | No | In progress |

## Decisions and evidence

[ADR 0082](../adr/0082-proposed-production-playback-timing.md#whole-take-playback-amendment-2026-10-31)
owns playback policy. [ADR 0100](../adr/0100-reviewed-production-presentation.md)
owns the workbench presentation, and [ADR 0227](../adr/0227-standalone-player-export.md)
owns standalone packaging. New automatic batches and ordinary requests with no
specified duration use the nearest qualified H3 output frame count. Explicit
request parameters and earlier confirmations remain bound to their own source.
An explicit existing edit operation is still available. The normal choice plays
the original encoded bytes and native audio to the end.

The evidence directory is `.local/whole-take/`. The locked local environment is
macOS arm64, Python 3.12.13 and Node 24.18.0. In Chromium the eight-second clip
resumed at 3.45 seconds after reload, past its three-second storyboard target.
The retained `n00-s3-c3` original measured 11.542 seconds and 277 frames.
No live provider integration or new creative assessment was needed.

The first frontend quick run failed three obsolete expectations. The first
browser selection used an invalid runner-relative path. The first native
nine-journey run passed five and failed four on stale generated assets and old
fixture wording/controls. After the build and fixture repairs, one old
assertion still expected a full-window selection to re-encode the original.
Its corrected regression requires the original digest for a whole take and a
different digest for an explicit partial window. Failed runs remain separate
from subsequent evidence. Independent review identified a direct-API default
duration and whole-original duration integrity issue. Both were repaired. The consumer check then exposed an existing prepared job that the new batch default would refuse to adopt. The fix preserves its original request during the fresh authority comparison. The adoption and frozen-authority selection passed all 15 focused cases. The high-deviation browser journey displayed +33.3%, selected and restored the full original. The explicit edit and full-window browser paths both passed after correction.

## Cheap restriction check

Start with a real action the creator could not complete. Read the condition
that stopped it and trace it to its owning layer. Ask what fails if that
condition becomes a warning or runs only at final export. Keep provenance,
media integrity, dispatch authority and unknown-outcome guards in place.
Only propose a change when the run or a small reproduction shows the cost.

- **Interactive branch preview.** Eight selected shots covered the complete
  short route, but seven missing shots on other routes hid its interactive
  playback and choices. The workbench computes missing media across every node
  before it enables a branch. This is a candidate for route-scoped preview.
  The existing linear route player can already use its own path, and final
  game export still needs all routes. [Production observation](2026-10-30-last-projection-h5-mvp.md#plan-review-and-production-learning) · [Preview condition](../../frontend/src/branching-video-preview.tsx#L168)
- **Storyboard cut limits.** The F5 review has a two-second minimum and a
  configurable maximum up to fifteen seconds. The original project used fifteen
  and passed this stage. This sample found no creator rework caused by the
  limits. [Review contract](../../src/plotloom/storyboard_review_contracts.py)

Root owns disposable fixture/server cleanup. The retained original project,
historical exports, and the installed runtime are outside the mutation scope.
