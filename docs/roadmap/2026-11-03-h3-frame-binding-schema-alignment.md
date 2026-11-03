# H3 frame-binding schema alignment

## Current status

Updated: 2026-11-03. Completed under the H3 director: source/local qualification by worker `01a1a003-f0b1-7111-8bc8-725b26d0eb35`, operation preparation/evidence capture by worker `01a1a060-f735-7ab2-8381-482c6f8762ea`, and live execution/independent readback by the director. Original source baseline: `481066f5`; scoped local source checkpoint: `b5afce01`. Separate Spark schema activation and verified restoration of the original gateway completed at 04:32:11 Toronto. All data and constraints were preserved except the intended role CHECK widening. No remaining blocker or reserved window for this storage repair; no further apply is authorized by this plan.

Local qualification remains composite: the original `full` invocation failed because the new service module was untracked; its exact failed test passed after intent-to-add, and all downstream gates passed without source changes. The original invocation remains failed, not a single green full run. Source publication and generated-media quality are separate; no push or CI occurred.

## Acceptance

| Claim | Required evidence | Fresh media | Status / evidence |
|---|---|---|---|
| Functional storage parity | Populated legacy migration, current/fresh no-op, `source` admission, invalid/duplicate role and FK refusal, idempotence and rollback | No | Focused fixture, reviewed real-copy trial and local gate evidence passed |
| Data and provenance preservation | Exact historical DDL, online backup identity, all table row counts/digests, FK/index/integrity checks | No | Private trials and actual live readback against the fresh activation backup passed; only the intended CHECK changed |
| Provider request fidelity | Existing H3/Qwen and image-input regression behavior | No | No public request or prompt edits; affected regressions and composite local qualification passed, with original full failure retained |
| Generated-media quality | Separate source and audiovisual review | Separately scoped | Out of scope; no generation in this repair |
| Live activation | Coordinated idle window, backup/recovery, one migration, exact readback and normal service health | No | Distinct corrected operation committed once; original gateway restored and independently verified at 04:32:11 Toronto; earlier failed operation preserved |

## Scope and method

Initial journey: initialize a populated historical gateway SQLite store, admit a `source` frame binding, reject invalid roles, and reopen the same store. Local fixtures and locked tests were followed by transactionally consistent private Spark copies, permission-matched actual-image migration/recovery proof, and a separately coordinated schema-only live operation. After a fresh protected online backup and private preflight, the exact normal gateway was stopped; migration ran under a SQLite write fence, then the original gateway was restored. Runtime and permissions were unchanged. Role insert probes ran only on disposable copies under rollback. No provider/GPU/media submission was part of this repair. Director retains backups, fixtures and operation evidence; the three stopped one-shot activation containers were subsequently removed without images, volumes or evidence deletion.

Owned source: gateway `store.py`, cohesive `frame_binding_schema.py`, focused gateway tests, this plan and ADR 0235. The isolated experimental adapter's preflight/error classification proposal remains outside main. The spent candidate identity is not retried. The source-to-final-request and media-quality claims remain separate from this storage repair.

## Historical decisions and evidence

The November 3 candidate POST returned a misleading 409 because that isolated adapter mapped every SQLite integrity error to duplicate admission. The exact job remained absent and normal service was restored. The old one-use grant is spent; that incident is evidence of an experimental admission gap, not a normal H3/Qwen failure or media-quality result. The director's retained canary packet owns detailed chronology.

The first schema operation failed at its first DDL statement: host UID 1000 could not write the root-owned database/parent. Private copies had been writable by that user, leaving a deployment-envelope gap. The migration rolled back; all legacy data/schema matched the fresh backup before a separately authorized start restored the original service. That attempt remains failed and its grant spent. Matching root-owned private fixtures then reproduced the failure and qualified a distinct isolated root execution context before the successful activation.

The corrected operation committed at 04:32:08 Toronto and verified original-service restoration at 04:32:11. Fresh-backup counts were preserved: 366 assets, 276 jobs, 366 frame bindings, two voice bindings, 283 lane rows, four sync-pilot rows and one SQLite sequence row, including the preceding normal job. Only `job_frame_bindings` changed from the exact historical CHECK to `start`/`end`/`source`; keys, indexes, all table data, FK validity and integrity matched. Root and Plotloom independently verified restoration and released the hold.

Actual receipt: `/home/wjmao/services/plotloom-h3-frame-binding-root-context-20261103/live-operation/director-activation-verification.json` on Spark, SHA-256 `8f8cef5f9d6a9c9e89c22e73967a66262e7390b70d2fc92d9200680278b97e28`. Historical failed and successful operation packets are retained separately. This completes the storage repair; source-to-render and audiovisual qualification remain separate work.
