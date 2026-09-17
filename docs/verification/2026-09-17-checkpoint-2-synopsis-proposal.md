# Checkpoint 2 synopsis-to-proposal receipt

Captured 2026-09-17 against the local checkpoint-2 candidate. This records
implementation and automated verification; director product acceptance and any
push remain separate.

## Delivered boundary

- The existing Brief is the required synopsis input. An omitted working title
  saves as the visible `未命名故事` default; explicit input is retained.
- A proposal requests exactly `story_bible` and `story_graph`, then composes
  their canonical revisions into characters, setting, premise/direction,
  choices/endings, derived counts, and bounded production scope.
- Scene beats, storyboard, media, and storyboard Gate/Approval are not created
  or reused as proposal acceptance. Continue is explicit navigation only and
  stays disabled after a Brief/Bible/Graph stale transition until proposal
  stages are regenerated.
- The proposed UI maps are in
  [checkpoint-2-synopsis-proposal-map.md](../roadmap/checkpoint-2-synopsis-proposal-map.md);
  the durable ownership decision is ADR 0053.

## Automated evidence

| Command | Result |
| --- | --- |
| `npm --prefix frontend test` | 16 files, 158 tests passed |
| `npm --prefix frontend run typecheck` | passed |
| `npm --prefix frontend run typecheck:e2e` | passed |
| `npm --prefix frontend run test:e2e` | 44 browser tests passed on production FastAPI/file-SQLite fixtures |
| `npm --prefix frontend run build:deterministic` | passed; refreshed `src/plotloom/static/` |
| `uv run --locked pytest -q` | 557 passed, 1 external deprecation warning |
| `uv build --wheel` and `uv run --locked python scripts/smoke_installed_wheel.py dist` | passed |

The full Python gate initially found only the Playwright `test-results/`
directory created by a prior failed test attempt; the extraction-boundary test
correctly rejects undeclared repository roots. The evidence was retained under
the assignment's ignored `.local/relay/` scratch path, the repository root was
restored, and the final complete run above passed.

## Review and live limitation

An attended independent Terra read-only review identified two P1 findings:
client-side Brief saves failed to project server-wide staleness, and the shipped
static bundle was stale. The candidate now marks all canonical stages stale on
a Brief save and includes a rebuilt static bundle; focused and full browser
coverage passed after those repairs.

The browser journey uses a test-owned no-auth text fixture. No user-owned,
ready local text profile was available without changing profile/environment
settings, so the requested bounded real-text creative trial was not performed.
Live creative fidelity and acceptance therefore remain pending; this receipt
does not claim them.
