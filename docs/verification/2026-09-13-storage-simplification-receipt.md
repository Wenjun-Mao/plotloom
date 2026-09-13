# Storage simplification receipt

- **Baseline:** `c260133995e953e350a7a50eecca0f30ee8f2f79`
- **Outcome:** behavior-preserving clarity work on the approved storage/draft
  subset; no milestone, provider, runtime cutover, or data mutation work.

## Changes retained

- The brief and stage save paths now share one local, typed check for whether a
  server draft is the exact canonical-save receipt. Their route calls, state
  updates, stale propagation, and CAS behavior remain separate.
- Visual-intent and image-direction session maps share only the defensive JSON
  map reader. Each keeps its own entry validator and server-draft lifecycle.
- Original, refinement, and keyframe-adaptation target names use explicit
  branches instead of nested ternaries. Request validation still rejects a
  simultaneous refinement parent and adaptation profile, so no precedence is
  admitted for that invalid combination.
- The project-storage error response now assigns its status/code explicitly;
  its response contract is unchanged.

The preview applicability/state refactor was reviewed and deliberately deferred:
its state-precedence contract is not worth expanding in this bounded change.

## Evidence

- Focused Python storage/media contracts: `11 passed`.
- Locked Python suite: `664 passed, 9 skipped` (278 existing/dependency
  warnings).
- Frontend unit suite: `14 files, 132 tests passed`; TypeScript and E2E
  TypeScript checks passed.
- Browser suite: `30 passed`.
- Production frontend build passed twice with identical hashes for
  `index.html`, `workbench.css`, and refreshed `workbench.js`.
- Fresh wheel build and isolated installed-wheel smoke passed
  (`ac39cba67938bba64930bfae96da8876132d263b57f27ebb0a60688ba3c586a9`).

No unresolved behavior concern was found in the selected subset. The standard
Vite bundle-size warning and existing Python warnings remain.
