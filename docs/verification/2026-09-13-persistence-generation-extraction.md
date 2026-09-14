# Persistence generation extraction receipt

> **Correction:** this initial receipt overstated the completed ownership move.
> Public methods had moved, but central repair, recovery, evidence, and install
> policy still lived in the retained facade. See
> `2026-09-13-persistence-generation-ownership-correction.md` for the
> corrective extraction and final verification record.

## Checkpoint

- **Baseline:** `5827cad452a0582143357c4675b3ee3393ed9ae1`, clean before work.
- **Outcome:** moved public generation persistence bodies out of the retained
  `SQLiteRepository` facade while preserving every public signature, schema,
  row mapping, hash/JSON representation, frozen provider profile policy, and
  project/run binding.
- **Scope:** generation persistence collaborators, the modularization
  regression contract, this receipt, and the approved roadmap only.

## Ownership result

`project/generation_snapshots.py` owns immutable canonical snapshots, run
bootstrap, frozen GenerationPlan, and Story Graph topology; `generation_plans.py`
owns StagePlan/work-unit creation. Attempts, raw response/unknown outcome,
reuse bindings, aggregate seals, progress, exact repair scope, startup recovery,
atomic output installation, and legacy-compatible artifacts/traces each have a
separate named collaborator. All are 202--397 lines. The facade delegates
explicitly and retains only private session/query/codec helpers shared by the
transitional composition; no collaborator uses dynamic forwarding.

The old facade combined public compatibility calls with lifecycle bodies, making
generation transaction ownership hard to inspect. The durable fix belongs at
the persistence capability layer: named read/write/lifecycle/claim leases stay
unchanged, and callers, API, schemas, metadata, migration history, runtime
composition, and frontend behavior are untouched. The regression contract now
proves all ten generation collaborators are explicitly composed and selected
facade methods delegate to their named owner.

## Characterization and verification

- Baseline SHA-256: `legacy_repository.py`
  `f0ad85d371e57a58bfd65a52c006070fec6aca29fa52879269e656d07c2672a7`; generation
  mapping `ff7854683d05fcb82ab6e292d4c48cd47bc3f4e901ae522ff20852d542eb042b`.
- Before edits: focused work-unit, repair, recovery and pipeline characterization
  suite: **164 passed**.
- During extraction: focused work-unit, planning/aggregate, exact-repair,
  continuity-repair, pipeline and recovery suites remained green; final focused
  regression set: **123 passed**.
- Independent attended read-only Terra review: no P1--P3 findings; it confirmed
  264 repository method names/signatures match the baseline, explicit
  collaborator composition, retained project-bound checks, and unchanged lease
  and lifecycle semantics.
- `uv run --locked pytest -q`: **670 passed, 9 skipped**.
- Frontend `typecheck`, unit test, and build: passed (**132** unit tests);
  `git diff --exit-code -- src/plotloom/static`: passed unchanged.
- `npm run test:e2e`: **30 passed**.
- Fresh `uv build --wheel` and `scripts/smoke_installed_wheel.py`: passed,
  including Alembic/package inspection; wheel SHA-256
  `433939882cd3d9fa6440514887ce3106265567f8e265f03a04042a07ba1f56c7`.

No provider call, migration, configuration, frontend source or generated static
asset changed. Remaining persistence work is deliberately limited to project
media and application control; this is not persistence completion or a
project-folder runtime cutover.
