# ADR 0101: Accessible creator confirmations

Status: accepted for the owner-authorized Stage 4 correction, 2026-10-02.

## Problem

Browser-native `window.confirm` paused media-review clicks in the current Codex
in-app browser. During the 14:58 B2 and 15:04 B3 rejection attempts, the ordinary
application prompt remained open until the owner dismissed it. The supported
`getJsDialog()` returned no dialog for B3; starting the click without awaiting it
did not resolve this. Native Codex control was denied and CDP initialization
stalled. These observations establish a current automation exposure failure,
not a new approval requirement. The separate 12:33 locked-host incident and
unavailable genuine sound review do not establish the same cause.

All four creator-native confirmations (original rejection, single and bulk
candidate deletion, and ShotBeatLink removal) share this failure boundary.

## Decision

Use a shared DOM `<dialog>` confirmation, portalled outside workflow details,
with native HTML modal focus containment, inert background, Escape/cancel,
default focus on cancellation, labelled consequences/targets, and focus return.
Humans and agents use the same explicit confirm button. There is no autoaccept,
API automation bypass, provider retry, or alternative security permission.

Domain owners freeze the intended action, exact project/job or coverage target,
reviewer/note and selection revision when opening. Changing domain identity,
currentness or write availability invalidates pending consent. A synchronous
in-flight guard prevents duplicate confirmations. Reload/unmount never persists
or replays consent. Server CAS and delete authority remain unchanged; original
rejection still retains evidence, while irreversible deletion still warns that
it cannot be undone. Declining a prompt performs no write.

The restore regression also exposed an older presentation mismatch with ADR
0082: an unselected original with retained segment proposals was offered for
deletion, which correctly returned server 409. Both single and bulk controls
must exclude these protected originals and explain why. New proposal identities
invalidate pending deletion consent even when selection revision is unchanged.
This aligns the UI with existing retention authority; no deletion restriction
or persistence contract is relaxed.

## Alternatives and guardrails

Automating the browser-native prompt retains the demonstrated exposure gap;
removing confirmation weakens the safeguard. A caller-specific API write bypass
would diverge from creator behavior. HTML dialog follows the existing asset zoom
convention while retaining domain-specific warnings and action ownership.

Component tests cover cancel/Escape/focus return, one dispatch, busy state,
stale identity/read-only invalidation, reload and failure recovery. Domain tests
verify exact review/deletion payloads; a source guard prevents new native confirm
calls. Actual in-app browser confirmation/cancel/reload must be checked on a
labelled disposable fixture after promotion, never by deleting retained assets.
Overnight preflight checks real UI mutation/confirmation access and actual audio
review capability separately; technical audio presence is not sound acceptance.
