# ADR 0131 Routine specialist continuation authority

Accepted 2026-10-08 UTC; owner clarification during the creator E2E run.

## Problem

The coordinator treated a continuation of an already assigned Image job as a
new task-messaging authorization boundary, despite the owner's authorization
to coordinate specialists for the run. The known blocker was uncommitted
execution source, subsequently repaired and committed; package, model and
settings were unchanged. Repeated consent requests interrupted approved work.

## Decision

Explicit owner authorization to coordinate specialists for an approved run
includes routine follow-ups and safe continuation of the same frozen job in
the existing specialist task. Before continuing, verify known job/dispatch
state, execution pin and completion evidence; retain package, model, settings
and job identity. A repaired preflight refusal is not itself a new consent gate.
This does not authorize duplicate preparation, dispatch or generation.

Ask when specialist coordination has not been authorized or when the action
materially changes scope, spending/provider, protected data or acceptance.
A user-directed stop, safety pause or permission refusal is not an ordinary
preflight blocker and must not be bypassed. Unknown dispatch is investigated,
not blindly retried. Tool/sandbox security requirements remain in force.

## Consequences and guardrails

Reject both per-message reapproval within established authority and blanket
permission to resume any stopped task. The run profile records the authority
and exact job state; routine continuation is reported as progress, not a new
approval question. Delivery and creative acceptance remain distinct.
The permanent playbook and AGENTS.md carry this rule. Historical receipts retain
the earlier pause; their wording does not create a current consent requirement.
