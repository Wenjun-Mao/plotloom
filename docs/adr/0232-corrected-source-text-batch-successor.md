# ADR 0232 — Explicit corrected-source text-batch successor

Status: accepted for the demonstrated V2 pre-H3 cancellation blocker, 2026-11-01.

Cancelling a directions draft can retain a text-only UNKNOWN even after the
native host proves local execution stopped. Ordinary setup and execution retry
must continue refusing that record. Process absence does not settle remote
outcome, refund cost or authorize replay.

A separate explicit corrected-source command may prepare a fresh single-shot
batch after one exact cancelled pre-H3 batch. It requires predecessor revision,
job/attempt identity, native host confirmation of that same cancelled stopped
text attempt, zero image reservation, no production authorization or video jobs,
unchanged execution envelope and generation settings, a fresh request identity, and
a changed validated source. It does not dispatch text or video itself. The new
batch requires its own draft, independent check and production authorization.

Creation and predecessor CAS share one project transaction. Both sides retain
an immutable command/request identity and predecessor link containing UNKNOWN
and possible prior cost. Idempotent acknowledgement cannot create another
successor. The predecessor stays cancelled, unpublishable and non-resumable;
its attempt/status, spending reservations and host capacity are unchanged.
Active execution, image/H3 uncertainty, permission/authorization refusal and
ordinary retries retain their existing refusals.

This is a troubleshooting owner operation, not a routine production step or a
general stopped-UNKNOWN exception. It does not authorize a new provider, a
larger frozen grant, uncertain-dispatch clearing, CI or creative acceptance.

The prospective command freezes the current full execution-profile hash. A
causal source repair changes the validator fingerprint because it includes the
complete Python source tree; only that hash may differ from the predecessor.
Model, executable, instructions, permissions, tools, runtime and resource limits
must match. Both profiles remain recorded. Observation leaves an already locally
stopped cancelled text UNKNOWN intact across source upgrades; fresh native host
identity/stop proof is still mandatory before a successor can be created.
