# ADR 0130 Media selection reads after acknowledged writes

Accepted 2026-10-07.

## Problem

The media workbench permits changing shots while a reviewed-keyframe save is
pending. A successful write advanced the project-wide selection revision, but
a read started for the new shot before that write could finish later and replace
the token with an older revision. The next selection then correctly failed
backend CAS. Context/sequence ownership alone did not express read-after-write
authority.

## Decision

The media-read owner owns the minimum observed selection revision for its current
project visit. A selection acknowledgement advances that floor and starts a
complete read for the currently active shot/approval context, superseding reads
started before the acknowledgement. Callers do not patch the read projection
or combine a fresh token with stale bindings.

Only a complete, owned projection at or above that floor can enable media
controls. A lower-revision result is an explicit failed read, with existing
retry controls; it neither rolls back the token nor triggers repeated automatic
retries. Project changes reset ownership, including A-B-A visits. Late writes
from a different visit or unmounted owner cannot refresh the new workspace.

The backend revision/CAS contract is unchanged. Shot navigation remains usable;
mutations remain locked while media authority is loading or failed. No
compatibility setter or adapter remains.

## Rejected alternatives

Serializing only the failing browser test would hide a permitted product
interaction. Disabling shot navigation during every save would change that
interaction. Taking only the maximum token while publishing an older projection
would incorrectly make incomplete bindings actionable.

## Guardrails

Deferred hook tests hold a new-shot read across the previous-shot write ACK,
reject a lower-revision snapshot and recover explicitly, and contain old ACKs
across project changes, A-B-A and unmount. The real imported-still browser
journey continues to select successive shots without a new test-only ACK wait.
