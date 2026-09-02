# ADR 0008: Capability-based source adoption tracking

## Context

Plotloom preserves the strongest product ideas from Narrative Forge and
shuohao-skills without inheriting either repository's runtime architecture. A
file-by-file porting checklist would confuse copied implementation with retained
behavior and reward directory movement. A single completion percentage would
also hide the difference
between a tested domain contract, a usable browser workflow, a live provider
integration, and a releasable standalone product.

## Decision

- Track adoption by user or system capability, not by source file. The
  authoritative living tracker is `docs/roadmap/capability-matrix.md`.
- Pin every source assessment to an exact audited revision. The tracker records
  provenance and license boundaries separately from Plotloom implementation status.
- Give every capability one source disposition: **Adopt**, **Adapt**,
  **Rebuild**, **Defer**, or **Reject**. These labels describe the decision about
  behavior or design; they do not imply that third-party code was copied.
- Measure maturity with evidence levels from a recorded decision through
  contract, implementation, fake-provider verification, browser verification,
  live-provider verification, and extraction-ready release. Each row declares
  its own required exit level, so a provider-neutral domain rule is not required
  to perform a live network call.
- A capability may be called complete only at its declared exit level. Every
  non-terminal row must name the next missing proof or product outcome. Deferred
  and rejected rows are closed decisions only while their stated scope remains
  unchanged.
- Keep subjective planning percentages as a secondary forecast. They must never
  replace the capability rows or test evidence.

## Rejected alternatives

- Tracking source files or commits as percent incorporated would overcount
  copied structure and undercount redesigned contracts.
- Maintaining separate source-comparison and Plotloom-progress tables would allow the
  two views to drift and would obscure why a feature exists.
- Treating passing unit tests as product completion would conceal browser, live
  provider, packaging, recovery, and creative-quality gaps.

## Consequences and guardrails

The matrix must be updated whenever a capability decision, maturity level,
required exit level, or blocking gap changes. Evidence links should point to a
contract, implementation, test, runtime receipt, or decision record rather than
an unsupported status assertion. The shuohao-skills private shot-recipes library
is never counted as audited or incorporated. Direct reuse of copyrightable
third-party material requires a separate provenance and Apache-2.0/NOTICE review.

The matrix and historical ADRs remain design evidence in Plotloom's clean
repository. No V1 runtime source is required by this tracking workflow.
