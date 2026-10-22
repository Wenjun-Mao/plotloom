# ADR 0151: Local project-command admission and progress

Status: implemented; focused qualification and independent source review passed,
2026-10-09. Final broad candidate qualification is recorded separately.

## Problem

Held Archive and Restore requests left the directory's competing controls enabled
and displayed no progress. Close, Delete and Snapshot had separate busy projections;
React rendering alone could not reject same-tick overlap. Archive's draft-save
preparation happened before lifecycle admission. Its retained decision was also
unbound: after a workspace change, a later Discard could target the old project
while clearing the new workspace's draft.

## Decision

The lifecycle hook owns one synchronous, in-memory command token, acquired when a
command actually executes, before error clearing or awaiting. Its immutable target,
title and action project a target-specific status into both directory entrances.
Ownership lasts through draft preparation, the request and required directory
refresh. Exact-token cleanup runs even after a workspace epoch change or setup
failure. Close/Delete/Snapshot retain their existing read/write quiescence; Archive
and Duplicate do not pretend to close a project or weaken server admission.

An archive/close draft decision freezes its originating workspace operation and
scope. Superseded decisions are dismissed before command admission, without
saving, discarding, targeting another project or clearing an unrelated error.
Cancelled consent, unsupported capability and busy no-ops do not admit commands.
An executing confirmation remains mounted and disabled by its own confirmation
owner; command progress must not invalidate the confirmation that admitted it.

## Alternatives and consequences

Per-button flags leave preparation and same-tick gaps. A backend lock or automatic
retry cannot repair missing client progress or a misbound draft decision. A global
cross-tab queue would add an unnecessary contract: this exclusion belongs to the
requesting workspace hook only. Existing server CAS, idempotency and unknown-result
boundaries remain authoritative. No persistence, migration or compatibility code.

## Guardrails

Held Archive/Restore feedback, disabled competing commands, ACK/error retirement,
Snapshot mutual exclusion, save-before-archive single admission, cancelled and
unsupported no-ops, setup-failure cleanup, stale settlement and superseded decision
callbacks. Confirmed Delete/Duplicate remain visible and busy while held. Exercise
the supported desktop sizes and exact disposable targets; preserve owner data.
