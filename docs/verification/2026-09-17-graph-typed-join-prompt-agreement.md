# Graph typed-join prompt agreement receipt

Captured 2026-09-17 from the retained baseline
`6c68bf6b37393cc34e71988b084ce541106483f1`. This is a prospective, bounded
prompt-contract correction. It is not a historical rewrite, creative approval,
or checkpoint-3B quality acceptance.

## Diagnosis and ownership

Graph admission already compiled the typed direct-edge entry contract and
rejected partial or conflicting entity-state assignments. The two Graph prompts
only described generic `stateEffects` join variance and typed edge syntax, so the
model did not see the same cross-edge contract that trusted validation enforced.

The graph author/model owns causal content and explicit direct-edge assignments.
Trusted code owns vocabulary, topology, and fail-closed validation. Generic
`stateEffects` variance remains governed by `joinContract`; it neither represents
nor relaxes typed `entityStateEffects`. JSON Schema cannot express the relation
across all direct incoming edges, so no schema or executable state framework was
added.

## Delivered correction

- `story_graph` is version `3.2.0`; `story_graph_content_fill` is version
  `2.7.0`.
- Both rendered prompts require, for each entity at any target, either omission
  from every direct incoming edge or the identical state on every such edge.
- Both direct incompatible narratives to an explicit upstream causal content
  revision. They prohibit fabricating state, erasing a meaningful assignment
  merely to satisfy validation, and topology changes.
- ADR 0056 records the author/model versus trusted-code boundary. Existing
  snapshots, version recovery behavior, schemas, validators, production code,
  and retained 3B runtime data were not changed.

## Verification

| Check | Result |
| --- | --- |
| focused rendered-prompt and Graph-admission tests | `uv run --locked pytest -q tests/generation/test_prompts.py tests/generation/test_join_state_values.py` — 17 passed |
| locked Python suite | `uv run --locked pytest -q` — 565 passed; one existing FastAPI/TestClient deprecation warning |
| direct full production browser suite (default worker count, not single-worker) | `npm --prefix frontend run test:e2e` — 47 passed in 1.4m |
| fresh package check | `uv build --wheel` plus `uv run --locked python scripts/smoke_installed_wheel.py dist` — passed |
| diff hygiene | `git diff --check` — passed |

The direct browser and installed-wheel console logs are retained under ignored
`.local/relay/a23ecf73-9409-4246-8b83-e8a51c3f7bd2/`; mutable `test-results`
artifacts are not used as a substitute for those transcripts.

## Independent review

An attended independent read-only Terra review of the final source delta found
no P1/P2 findings. It confirmed that only the two templates, two focused test
files, and ADR 0056 changed; both templates render the same all-omit-or-all-equal
direct-edge rule, the tests exercise `validate_story_graph` for omitted, equal,
incomplete, and conflicting examples, and ADR 0056 accurately preserves the
schema boundary. Tracker and receipt closure remain coordinator-owned.

## Disposition

This closes the explicit Graph prompt-agreement correction only. It does not
resolve the retained checkpoint-3B causal/creative findings and does not assert
human or product acceptance. Director acceptance, merge, and push remain
separate.

Director engineering acceptance: `c738e63` closes the typed-entry enforcement,
source-binding, modularity, and explicit prompt-agreement correction. Retained
logs were inspected; the browser run's earlier “serial” label was incorrect and
is corrected above. Its full default-worker pass is the fresh browser evidence
for this template-only delta; no single-worker rerun is claimed. Checkpoint 3B
still requires a bounded live requalification and concrete causal review.
