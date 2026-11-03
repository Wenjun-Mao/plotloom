# ADR 0235 — Align historical H3 frame-binding roles with the declared schema

Status: accepted. Source checkpoint `b5afce01` is local-only; the separately authorized Spark schema activation and original-service restoration were verified on November 3, 2026 at 04:32:11 Toronto.

## Context

The gateway's fresh `job_frame_bindings` table accepts `start`, `end`, and `source`. The existing Spark table had the historical `start`/`end` CHECK. The prior startup migration left that CHECK unchanged, so fresh and existing databases admitted different role values. The observed failure was an isolated auxiliary candidate's admission; no normal H3 or Qwen failure is established.

## Decision

On gateway initialization, recognize the exact historical table definition and rebuild only that child table inside a savepoint with the current `start`/`end`/`source` CHECK. Preserve the four columns, composite primary key, foreign keys, asset index, and every row. Require foreign-key validity and the expected dependent-object shape before changing it; refuse unknown forms. Fresh/current tables are no-ops. Retired profile-state refusal remains in force.

The public API, role mapping, rendering, provider request, and shared-lane behavior do not change. No role alias or automatic retry is added. A live upgrade requires a separately coordinated idle window, verified backup, exact target pins, preservation checks, and an operator decision; installing this source alone is not evidence of live migration.

## Verification and activation

Local qualification is composite: the original `full` invocation failed because Git inventory did not yet include the new module. Its exact failed test passed after intent-to-add, and all downstream gates passed without source changes. The original invocation remains failed; no single green `full` run is claimed.

The first live operation ran as host UID 1000 and failed to write the root-owned database. The transaction rolled back; exact legacy data/schema preservation was verified before separately restarting the original service. A distinct, reviewed operation then used the exact installed image's isolated root process, after reproducing the ownership/mode mismatch and proving migration/recovery on matching private copies. It committed only the intended CHECK change and restored the original gateway. Live permissions, ownership, image and configuration were unchanged.

Readback against the fresh activation backup preserved all table data, primary/foreign keys and indexes; FK and integrity checks passed, historical readbacks matched, and the original service was healthy and idle. The independent activation receipt is retained on Spark at `/home/wjmao/services/plotloom-h3-frame-binding-root-context-20261103/live-operation/director-activation-verification.json`, SHA-256 `8f8cef5f9d6a9c9e89c22e73967a66262e7390b70d2fc92d9200680278b97e28`. This storage activation establishes no generated-media quality result. No push or CI occurred.
