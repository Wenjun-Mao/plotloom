# ADR 0230: Truthful Codex production-authorization operator

## Status

Accepted for the authorized Last Projection E2E delivery on 2026-10-31.

## Context and ownership

Normal H3 batch Start currently records an unnamed creator. Its request can
represent only a creator or a bounded QA actor, so an owner-authorized Codex
operator cannot start a real story without creating a false human attribution.
The ready first-shot batch has not been started or submitted to H3.

The caller owns the explicit operator identity and generation decision. Trusted
code validates, freezes and propagates that identity with the exact production
authorization. Models own no operator, grant or authorization field: their
existing derived directions and distinct fidelity checks remain unchanged.
Story sources, briefs, prompts, settings, budgets and retry authority are not
changed by this attribution repair.

## Decision

Add optional `operator: CodexTaskAttribution` to batch Start and the trusted
`IntentAuthorization` projection. It identifies the actual Codex task operating
an already authorized command; the UUID is attribution, not a capability or
permission to generate. Keep QA `attribution`, `reviewAttribution` and
`reviewBasis.attribution` separate and QA-only. Refuse operator plus QA
attribution, and refuse this normal-project path on known QA projects.

Store the complete authorizer in `intentReviewActor`; authenticate exact Start
replays before returning the existing result and again under the source/command
transaction. Propagate the Codex operator into the prepared job authorization.
Preparation, dispatch and portable reopening must match it to the retained batch;
missing, changed, malformed or conflicting operators cannot silently become
human authorization. Manual single-shot readback preserves and compares it.

Omit absent optional fields when serializing. Existing creator and QA request,
snapshot and receipt bytes remain unchanged. Preserve historical evidence;
do not rewrite it as Codex-operated. No new QA scope, source approval, dispatch
grant, inspection fact, quality pass, budget or retry permission is created.

## Verification

Use provider-free real API/persistence tests for normal Codex Start, exact replay,
changed/missing operator refusal, QA bypass refusal, prepared-job propagation,
dispatch validation, tampered stored/readback attribution, close/reopen and
snapshot/restore. Retain existing human/QA serialization and safety regressions.
Qualify the stable cross-layer authorization candidate locally before activation.
Fresh media is unnecessary to prove this repair; the original production resumes
through the unchanged ready source-bound job after focused contract qualification
and safe restart; the final local release gate continues separately.
