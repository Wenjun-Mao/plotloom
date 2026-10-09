# ADR 0144: Runtime-owned workspace capabilities

Status: implemented candidate; qualification is recorded in the E22 receipt.

## Cause and decision

Native authoring composes no API text admission/dispatcher and deliberately
omits provider-profile and generic pipeline execution/progress/trace routes.
The workspace nevertheless offered their execution and settings controls and
displayed an invented default profile's readiness. Its
initial profile read was also coupled to draft support or a failed draft probe.
The resulting 404 was a composition mismatch, not a missing credential.

Replace the draft-only-named capability endpoint with
`GET /api/v2/runtime-capabilities`. All five current boolean fields are required:
durable project/media drafts, explicit project close, portable snapshots and
the API text pipeline. The composition owns `apiTextPipeline`: true only
when both API text admission and dispatch are composed, exactly matching route
registration. This projection does not assert native specialist readiness.
This required boolean replaces the unpublished `textProviderProfiles` field,
without an alias. Both route groups share the same composition condition;
a separate profile flag would allow invalid availability combinations.
Retire the former endpoint/getter without an alias or response fallback.

The client validates the complete response and owns loading/failed/ready states.
Failed or malformed reads remain unknown with an explicit read retry. An explicit
false hides API provider controls and explains where assistant settings live.
The workspace never reads profiles merely because draft capabilities are absent
or their read failed. A profile's status comes from the loaded active catalog,
not an initial form default or an unsaved/inactive selection. Existing frozen API
run credential reads retain their exact run/profile ownership.

Every generic run command fails closed before profile/stage reads or mutations
unless the validated capability is explicitly true. The Brief proposal callback
checks the same admission before saving its Brief. Unsupported controls are
hidden or disabled with native authoring guidance. Unknown reads explain pending
availability and retain explicit retry; they never claim unsupported mode.
Project loading reads retained run summaries in either composition, but only
API mode reads progress/trace or resumes/observes a retained active run. Native
Source, Outline, Cast, Art, Script, Storyboard and bridge-intent keep their own
contracts and remain available. No default credentials, 404 mode inference or
API fallback is introduced.

## Alternatives and guardrails

Reject enabling an API backend for native mode, inferring mode from a 404, hiding
every read error as unsupported, or using default form values as service evidence.
Tests must prove both real compositions and the unknown-read retry, with zero
unsupported profile/run/progress/trace requests or Brief save on refused
generation. Preserve exact frozen profile/key ownership for supported resume
and repair, draft ownership and the current close/snapshot behavior; inspect
all supported desktop sizes.
