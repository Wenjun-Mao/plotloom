# ADR 0144: Runtime-owned workspace capabilities

Status: implemented candidate; qualification is recorded in the E22 receipt.

## Cause and decision

Native authoring composes no API text admission/dispatcher and deliberately
omits the provider-profile routes. The workspace nevertheless offered their
settings launcher and displayed an invented default profile's readiness. Its
initial profile read was also coupled to draft support or a failed draft probe.
The resulting 404 was a composition mismatch, not a missing credential.

Replace the draft-only-named capability endpoint with
`GET /api/v2/runtime-capabilities`. All five current boolean fields are required:
durable project/media drafts, explicit project close, portable snapshots and
text-provider profiles. The composition owns `textProviderProfiles`: true only
when both API text admission and dispatch are composed, exactly matching route
registration. This projection does not assert native specialist readiness.
Retire the former endpoint/getter without an alias or response fallback.

The client validates the complete response and owns loading/failed/ready states.
Failed or malformed reads remain unknown with an explicit read retry. An explicit
false hides API provider controls and explains where assistant settings live.
The workspace never reads profiles merely because draft capabilities are absent
or their read failed. A profile's status comes from the loaded active catalog,
not an initial form default or an unsaved/inactive selection. Existing frozen API
run credential reads retain their exact run/profile ownership.

## Alternatives and guardrails

Reject enabling an API backend for native mode, inferring mode from a 404, hiding
every read error as unsupported, or using default form values as service evidence.
Tests must prove both real compositions and the unknown-read retry, with zero
unsupported profile requests from the native UI. Preserve draft ownership and
the current close/snapshot behavior; inspect all supported desktop sizes.
