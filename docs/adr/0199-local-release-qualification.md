# 0199: Local release qualification without mandatory hosted CI

Status: accepted owner-directed workflow decision, 2026-10-19

## Problem

Older verification guidance made hosted CI a release prerequisite while the
owner's standing rule prohibited GitHub Actions without a new explicit request.
This left an unrequested external run appearing to block a stable release even
after local qualification and actual product evidence were available. The owner
explicitly removed the hosted-CI requirement.

## Decision

GitHub Actions and other hosted CI are optional evidence, not prerequisites for
a stable/general-availability Plotloom release. Qualification uses the existing
applicable local verification policy, checks of the exact distributed package,
real supported-workflow evidence and applicable acceptance. This does not make
the current candidate release-qualified or waive any of those remaining checks.

The explicit-request-only CI rule remains unchanged. Do not dispatch, retry,
prepare or publish workflow changes, or knowingly trigger CI through publication
without the owner's new explicit request. No workflow, runner, test selection,
assertion or deadline changes follow from this decision.

Record an unrequested hosted run as not requested/not run, not as a pending
release blocker. Preserve historical failed results as failed. Concrete defects
found in a hosted run remain actionable; removing the execution requirement is
not a reason to ignore an unresolved product, packaging or verification defect.
If complete hosted qualification is requested, filtered diagnostics or failed,
skipped or cancelled checks cannot be represented as a complete pass.

This decision supersedes mandatory-hosted-release wording in ADRs 0109, 0160,
older roadmaps and verification plans. Their historical execution records and
technical runner/evidence contracts remain intact. AGENTS.md, README.md and the
development guide carry the current operational policy.

## Alternatives and guardrails

Keeping a mandatory hosted gate would recreate the unwanted external blocker.
Deleting or weakening the workflow would be an unrelated change and could evade
the owner's CI boundary. Treating all qualification as optional would weaken
release confidence. Instead, retain local release and real product checks, reuse
unchanged evidence, and report software qualification separately from acceptance.

Documentation-only verification checks policy consistency, links and whitespace;
it does not rerun software suites or claim new qualification.
