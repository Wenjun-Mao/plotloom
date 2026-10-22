# ADR 0154 — Process-local style-contract derivation reuse

Status: accepted for bounded implementation probe, 2026-10-10.

## Context

P0 profiled the approved rebuild/bridge pair at the current `main` source. It
called the Cast Node wrapper 1,026 times and the Art wrapper 513 times. Those
calls derive deterministic contracts while project readers repeatedly check
whether persisted bindings match current author direction and rules. The
profile establishes repeated process startup at the shared derivation boundary;
it does not justify caching any project or candidate decision.

Render ownership remains as defined by [ADR 0141](0141-character-render-direction.md)
and [ADR 0094](0094-author-selected-art-render-style.md): the author owns style
and direction, the Node rule owners derive frozen presets/contracts, and trusted
project code checks currentness and candidate validity.

## Decision

Probe a bounded, process-local LRU for successful pure Cast/Art contract
derivation. Keep the existing Node entrypoints as the sole rule owners. A cache
key includes owner and resolved script identity, exact style and direction
arguments (`null` remains distinct from an empty string), a SHA-256 fingerprint
of every file in the local ESM rule dependency closure, the resolved Node
executable identity and the exact `PATH`. Re-read dependency bytes for every
lookup so same-size or timestamp-preserving edits invalidate a hit. Verify the
same inputs after a miss derivation; if they changed, return the ordinary Node
result without caching it.

Store only the successful JSON text and parse it for each return, yielding an
independent object each time. Bound the LRU to 64 entries and serialize cache
misses under a lock. Never cache currentness booleans, accepted revisions,
requests, receipts, candidates or validator results. The existing style
validators, transaction/CAS, rollback, stale-target/direction and dispatch
checks continue to execute on their normal paths.

Do not use a hit when Node is unavailable or an input cannot be fingerprinted;
fall through to the existing invocation so its normal failure remains visible.
When `NODE_OPTIONS` is non-empty, bypass reuse because injected loaders and
startup options can add unbounded execution inputs. No environment values are
logged. Preserve Node stdout, frozen JSON shapes and hashes, and existing
nonzero-exit/JSON parse failures.

## Alternatives and consequences

Request-scoped derivation would require threading cache context through nested
readers and still leave repeated requests costly. A persistent Node worker adds
IPC, lifetime and failure-recovery behavior before the measured startup cost
requires it. Duplicating presets or rules in Python is rejected because it
creates a second authority. This change adds content hashing to each lookup;
the probe must show that this small cost is materially below avoided Node
startup while retaining freshness.

Tests must cover cache hits and independent values, all key dimensions,
dependency-content replacement (including same-size/same-timestamp changes),
mid-derivation edits, Node availability/identity/PATH changes, option failures,
JSON/Node failures, bounded eviction/concurrency, and real project currentness
and validator refusal. If the safety or material-speedup target fails, remove
this reuse and retain the evidence; no product persistence or runtime cutover
is part of this decision.
