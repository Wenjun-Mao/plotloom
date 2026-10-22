# ADR 0202: One linked correction for typed text content rejection

Status: accepted for source implementation, 2026-10-21.

## Problem and diagnosis

The native CLI correctly writes candidate JSON only. Trusted host validation runs
after its completed process and currently reduces content rejection to a private
failure hash. The automatic controller consequently blocks without giving the
model corrective feedback. The art validator's handheld-scale rule is genuine:
model-owned `prop.scale` requires its source-owned phrase in both model-owned
`image.prompt` and `image.sheet`. Host injection would conceal the contract error.

## Decision

New launch authority freezes a limit of one automatic correction per logical text
stage. Only a typed, allowlisted source-owned content rejection from the completed
CLI's exact trusted validation can authorize it. The rejection binds candidate
bytes, validation evidence, request/package/plan/profile/source and original
attempt identity. Runtime, parser, sandbox, permission, cancellation, refusal,
UNKNOWN and authority drift failures never authorize correction. Arbitrary stderr
and nonzero exit status are evidence, never repair instructions.

Create a new immutable job and physical checkpoint `<stage>:correction:1` in the
same run. Preserve the failed original candidate, checkpoint, package and attempt.
Freeze feedback and the prior candidate in the corrective request; otherwise
preserve exact source, upstream, style and currentness authority. Resolve the
logical stage to its linked correction for dispatch and adoption. Existing CAS,
unique identities, finite/lifetime budgets and machine command fences still apply.
Failure-to-prepared transitions remain prohibited. Images/video get no retry.

The current typed adapter allowlist is Outline, Characters and Art: their source
APIs return content issues normally. The other five text owners remain terminal
on rejection until their owners expose an equally typed boundary. Thrown parser,
contract or runtime errors never acquire correction permission. Feedback contains
fixed codes/paths and source-owned facts, never validator stderr or dynamic prose.
Prior candidate JSON is bounded to 500,000 UTF-8 bytes for the existing request
envelope; larger candidates fail closed without correction.

New profiles and launches explicitly freeze `textCorrectionLimit: 1`; omission in
retained authority grants no corrections. Fresh supported requests freeze the
`contentValidationContract` discriminator, so passive Outline projection can
preserve old plan bytes without rewriting or executing old frozen evidence.
One shared lifecycle-field contract carries typed rejection through the native
ledger and project reconciliation, preventing terminal evidence projection loss.

Publication guards classify only an exact source-owned terminal content rejection
as no longer publishable. The prepared original candidate row stays immutable;
manual, foreign, unstarted, UNKNOWN and other failed handoffs retain their guards.
This permits ordinary snapshot/restore after terminal correction outcomes without
resetting source rows or weakening unresolved native ownership checks.

## Alternatives and guardrails

Rejected: retrying the original identity, interpreting stderr as authority,
loosening validators, silently inserting prompt words, and generic retry machinery.
Focused tests cover typed rejection eligibility, one-correction exhaustion,
authority tampering, inactive controls, restart/duplicate reconciliation and
retained provenance. Provider-boundary fixtures are labelled separately from real
provider E2E and human acceptance. No migration rewrites old frozen authority.
