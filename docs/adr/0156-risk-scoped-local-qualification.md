# ADR 0156 — Risk-scoped local qualification

Status: accepted, 2026-10-10.

## Context

Requiring the full local release suite for every bounded frontend presentation
change repeats unaffected integration work. The October 10 workflow-guide
candidate passed the frontend suite and all 1,492 Python tests. Its deterministic
asset build correctly updated the checked-in static bundle, then the full
runner's `git diff --exit-code -- src/plotloom/static` step stopped because
those intended, uncommitted generated files differed from the trusted Git
baseline. Repeating the full suite would not make that baseline comparison
valid and would rerun source-based evidence whose inputs had not changed.

## Decision

Allow a local frontend qualification for a bounded frontend presentation or
navigation change that consumes unchanged APIs. Classification requires review
of the actual diff and dependencies against a trusted revision. The record must
show that backend/API schemas and request payloads, persistence, admission,
authentication, provider/prompt behavior, dependencies, package contracts and
build tooling are unchanged. File paths alone do not establish the boundary.

The qualification runs the unfiltered frontend unit suite, both TypeScript
checks, deterministic static-asset generation with a second-build SHA-256 tree
comparison, and explicitly selected affected browser regressions plus desktop
pixel inspection where layout changes. Run shared-contract and package checks
when the actual diff reaches those owners. Preserve generated files in the
candidate. This is a documented evidence path using existing commands, not a
new `verify.py` tier.

Use the complete, unfiltered local `full` gate for changes to the named
contracts or dependencies, build tooling, broad refactors, cross-layer runtime
behavior, or when impact is uncertain. Reuse valid evidence for unchanged
inputs; after a diagnosed failure, rerun the failed and affected downstream
checks and invalidate earlier evidence only when its inputs changed. Required
unfiltered hosted CI remains separate and is never waived or filtered. Local
frontend qualification is not full local release qualification, hosted CI
success, or product acceptance.

## Alternatives and consequences

Running `full` after every frontend edit was rejected because it repeats
unaffected suites and its Git-baseline asset check can reject a correct
uncommitted candidate. Classifying by file path alone was rejected because a
frontend change can still alter shared contracts. A new runner tier or parallel
verification infrastructure was rejected; the existing commands and explicit
evidence records are sufficient. This policy reduces unnecessary local reruns
while preserving unfiltered coverage on hosted CI and retaining `full` for
cross-layer, contract, dependency and uncertain changes.

The roadmap/receipt must state the trusted revision, reviewed contract surface,
exact commands and results, generated asset hashes, independent review, hosted
CI status, remaining gaps and product acceptance separately.
