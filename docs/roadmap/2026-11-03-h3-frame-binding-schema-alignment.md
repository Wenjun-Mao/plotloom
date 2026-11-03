# H3 frame-binding schema alignment

## Current status

Updated: 2026-11-03. Owner: delegated worker `01a1a003-f0b1-7111-8bc8-725b26d0eb35` for source and local qualification; director owns the later live decision. Baseline: clean retained `main` at `481066f5`. Result: exact historical CHECK and private online backup proved; copied-data migration, focused regressions, independent review, and reused local full-gate evidence passed. One `full` invocation failed only because the new service module was untracked; that exact test passed after intent-to-add, and all downstream gates passed. Blocker: root checkpoint and separate live activation decision; no idle window is reserved. Next action: manager reviews this stable diff and records the local checkpoint. Stop when: local proof and review are handed off without live database changes.

## Acceptance

| Claim | Required evidence | Fresh media | Status / evidence |
|---|---|---|---|
| Functional storage parity | Populated legacy migration, current/fresh no-op, `source` admission, invalid/duplicate role and FK refusal, idempotence and rollback | No | Focused fixture, reviewed real-copy trial and local gate evidence passed |
| Data and provenance preservation | Exact historical DDL, online backup identity, all table row counts/digests, FK/index/integrity checks | No | Private copy trial passed; live source remains untouched |
| Provider request fidelity | Existing H3/Qwen and image-input regression behavior | No | No request/schema/prompt edits; affected focused regressions and Python suite passed |
| Generated-media quality | Separate source and audiovisual review | Separately scoped | Out of scope; no generation in this repair |
| Live activation | Coordinated idle window, backup/recovery, one migration, exact readback and normal service health | No | Not authorized or performed in this slice |

## Scope and method

Journey: initialize a populated historical gateway SQLite store, admit a `source` frame binding, reject invalid roles, and reopen the same store. Fixture: small local populated legacy schema plus a transactionally consistent private copy of the actual Spark database. Runtime: local locked `uv` tests and private Spark Python/SQLite copy proof; no provider, GPU, network submission or service restart. Resource use: one read-only diagnostic backup and two private migration trials (the second after a review fix), no fresh media. Cleanup owner: director retains the private backup and trials for the later live decision.

Owned source: gateway `store.py`, cohesive `frame_binding_schema.py`, focused gateway tests, this plan and ADR 0235. The isolated experimental adapter's preflight/error classification proposal remains outside main. The spent candidate identity is not retried. The source-to-final-request and media-quality claims remain separate from this storage repair.

## Historical decisions and evidence

The November 3 candidate POST returned a misleading 409 because the isolated adapter masks any SQLite integrity error as a duplicate admission. The exact job remained absent and normal service was restored. The old one-use grant is spent; that incident is evidence of an experimental admission gap, not a normal H3/Qwen failure or media-quality result. The director's retained canary packet owns detailed chronology.
