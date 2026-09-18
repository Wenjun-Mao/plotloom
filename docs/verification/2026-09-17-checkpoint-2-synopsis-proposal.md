# Checkpoint 2 synopsis-to-proposal receipt

Captured 2026-09-17 against the local checkpoint-2 candidate. This records
implementation and automated verification; director product acceptance and any
push remain separate.

Director accepted `6e3ad75` for the bounded checkpoint-2 outcome after reviewing
the preservation fix, browser regression evidence and live trial record. Relay's
final locked gate records 557 Python tests and 158 frontend tests passing. This is
engineering acceptance; no new human creative approval or M2 completion is claimed.

## Delivered boundary

- The existing Brief is the required synopsis input. An omitted working title
  saves as the visible `未命名故事` default; explicit input is retained.
- A proposal requests `story_bible` plus `story_graph` when its Bible is
  missing or stale, or only `story_graph` when its Bible is current and its
  Graph is missing or stale; when both are current it starts no implicit run.
  It composes those canonical revisions into characters, setting,
  premise/direction, choices/endings, derived counts, and bounded production
  scope.
- Scene beats, storyboard, media, and storyboard Gate/Approval are not created
  or reused as proposal acceptance. Continue is explicit navigation only and
  stays disabled after a Brief/Bible/Graph stale transition until proposal
  stages are regenerated.
- The proposed UI maps are in
  [checkpoint-2-synopsis-proposal-map.md](../roadmap/archive/historical/2026-09-16-checkpoint-2-synopsis-proposal-map.md);
  the durable ownership decision is ADR 0053.

## Automated evidence

| Command | Result |
| --- | --- |
| `npm --prefix frontend test` | 16 files, 158 tests passed |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run typecheck:e2e` | passed |
| `npm --prefix frontend run test:e2e -- --workers=1` | 45 browser tests passed on production FastAPI/file-SQLite fixtures; serial ownership is required because profile-availability scenarios share the fixture catalog |
| `npm --prefix frontend run build:deterministic` | passed; refreshed `src/plotloom/static/` |
| `uv run --locked pytest -q` | passed |
| `uv build --wheel` and `uv run --locked python scripts/smoke_installed_wheel.py dist` | passed |

The full Python gate initially found only the Playwright `test-results/`
directory created by a prior failed test attempt; the extraction-boundary test
correctly rejects undeclared repository roots. The evidence was retained under
the assignment's ignored `.local/relay/` scratch path, the repository root was
restored, and the final complete run above passed.

The attended independent Terra delta review found and the final candidate fixed
three code issues (post-navigation draft-state mutation, omission of valid
choice edges from non-decision sources, and shallow Bible-preservation
coverage), plus two receipt inconsistencies. No findings remained after the
focused reruns and final gates.

## Correction and live trial

The former correction overreached: it projected every stage stale after every
client Brief save, even when the normalized canonical Brief was unchanged. A
subsequent proposal request then regenerated Bible plus Graph and could replace
an authored Bible refinement. The durable fix compares the canonical Brief at
the save boundary, discards an unchanged exact authoring-draft receipt without a
canonical write, and resolves stage heads fresh after the save. A missing/stale
Bible requests Bible plus Graph; a current Bible with a missing/stale Graph
requests Graph only; both current stages create no implicit run. Browser
regressions cover unchanged revision/no run, graph-only preservation at Bible
revision 2, changed-Brief Bible-plus-Graph selection, and rejected graph-only
regeneration without overwrite.

The director's production-repository probe at
`2026-09-17T03:22:35.143373Z` returned `available`,
`readiness.models_verified`, default profile revision 6. During this delivery
the runtime was started with `uv run --locked plotloom`; the same probe was
revalidated at `2026-09-17T03:31:26.530307Z`, with no profile or environment
setting changed. These results correct the earlier unavailable-profile claim.

One fresh project (`潮汐译信`) then completed the sanctioned default-profile
trial: synopsis to Bible/Graph proposal, Bible Logline refinement saved at
revision 2, Graph-only regeneration, browser reload, and explicit Continue to
the empty scene-planning editor. The initial run completed Bible after one
semantic correction and Graph on its first attempt; the refined Graph-only run
completed on its first attempt. The persisted final heads were Bible ready r2,
Graph ready r2 with `inputRevisions.story_bible: 2`, Scene Beats missing r0,
and Storyboard missing r0. No scenes, storyboard, images, or media were
generated. Engineering readability/fidelity review found the proposal clear
enough to identify its central dilemma, two choices, and two distinguished
ending targets; it is not human/product approval. The owned runtime stopped
normally after the trial.
