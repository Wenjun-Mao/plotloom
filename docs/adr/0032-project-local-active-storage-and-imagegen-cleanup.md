# ADR 0032: Project-local active storage and ImageGen staging cleanup

## Status

Accepted, 2026-09-13. This is an operational storage contract for active local
Plotloom work; historical receipts and frozen package records remain unchanged.

## Context

The retained P2 pilot placed its live SQLite database, artifacts, review pack,
and manual image exchange in sibling directories. Built-in ImageGen also stages
returned files below Codex-owned storage. Those locations made the active
working set hard to discover and invited broad user-level cleanup.

## Decision

For source checkouts, active local state belongs below ignored `data/`:

- `data/plotloom.sqlite3` and `data/artifacts/` are the runtime database and
  managed media roots;
- `data/review-packs/` holds local review aids and linked media copies;
- `data/image-exchange/` is the explicit same-host P1/P1.5 exchange root.

One-time relocation copies first and verifies hashes and SQLite integrity before
old roots are removed. Immutable requests, manifests, selections, seals,
ledgers, and historical receipts are not rewritten to disguise their original
paths. When immutable `file://` artifact records use an old root,
`PLOTLOOM_LEGACY_ARTIFACT_ROOTS` names that exact root as a read-only relocation
allowlist; the store maps only its relative path into the configured current
artifact root. A receipt names remaining compatibility references and the
disposition of each old root.

The repository-scoped image-specialist skill records only exact tool-returned
paths for its own Codex task. Its helper accepts direct, non-symlink children of
the declared task staging root, copies them to the package delivery, validates
the complete manifest identity, exact output set, and byte hashes, then unlinks
only those same paths. Missing sources are idempotent only if the durable output
already validates. Foreign paths, symlinks, incomplete manifests, extra outputs,
or incompatible existing files refuse cleanup.

New P1.5 packages name `plotloom-image-specialist.v3`; v2 frozen packages stay
historical and validate under their frozen request contract.

## Consequences

The user-level Codex staging parent is never a cleanup target. Failed or
ambiguous deliveries retain their staged files for manual disposition. Active
data stays untracked, while the committed specialist/helper/tests and
secret-free migration receipt make the workflow reproducible.
