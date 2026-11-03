# ADR 0235 — Align historical H3 frame-binding roles with the declared schema

Status: local implementation under the November 3, 2026 serial source lease; live migration and activation are separate decisions.

## Context

The gateway's fresh `job_frame_bindings` table accepts `start`, `end`, and `source`. An existing Spark table has the historical `start`/`end` CHECK. The prior startup migration left that CHECK unchanged, so a fresh database and the existing database admit different role values. The observed failure was an isolated auxiliary candidate's admission; no normal H3 or Qwen failure is established.

## Decision

On gateway initialization, recognize the exact historical table definition and rebuild only that child table inside a savepoint with the current `start`/`end`/`source` CHECK. Preserve the four columns, composite primary key, foreign keys, asset index, and every row. Require foreign-key validity and the expected dependent-object shape before changing it; refuse unknown forms. Fresh/current tables are no-ops. Retired profile-state refusal remains in force.

The public API, role mapping, rendering, provider request, and shared-lane behavior do not change. No role alias or automatic retry is added. A live upgrade requires a separately coordinated idle window, verified backup, exact target pins, preservation checks, and an operator decision; installing this source alone is not evidence of live migration.
