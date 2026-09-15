# ADR 0049: MiniMax-H3 catalog V3 clean cutover

**Status:** Accepted

## Context

The first private H3 gateway had one 864 × 480 profile. The later profile
catalog added six reviewed horizontal and vertical geometries, but retained the
original profile as a non-selectable compatibility entry. That decision left
the original profile in more than historical evidence: it was the gateway HTTP
default, the workflow-template identity, and the adapter fallback when a
frozen request or response omitted a profile ID.

That is unsafe for a clean, internal MVP. An incomplete request could silently
produce the wrong geometry, and maintaining an interpreter for a retired
profile would make every future profile change more costly. The gateway state
is disposable test/development state; completed MP4 retention does not justify
a permanent execution compatibility layer.

## Decision

Adopt the H3 profile contract version 3 as a clean cutover.

- The allowlist contains exactly six current profiles: three landscape and
  three portrait geometries. The 864 × 480 profile is absent.
- `profileId` is mandatory for every new one-step and two-step job. There is
  no default profile at the HTTP boundary.
- Plotloom may use the portrait fast profile as an authoring default, but it
  freezes and sends that explicit ID; the adapter never infers one for a
  frozen request, response, or observed output.
- The ComfyUI graph is stored as a profile-neutral H3 Turbo template. Width
  and height are bound only from the selected allowlisted profile during
  rendering; the template has no retired profile identity or dimensions.
- The health/catalog handshake, adapter version, and Plotloom configuration
  anchor move together to V3. A V2 gateway and V3 Plotloom runtime refuse to
  preflight each other rather than silently drifting.
- An old profile ID or a profile-less request is rejected before job creation
  or source-URL fetching. It is not migrated to a nearest geometry and is
  never replayed.

Deploy the gateway V3 before restarting a Plotloom runtime configured with
`VIDEO_MODEL=minimax_h3_gateway_catalog_v3`. Before deployment, confirm that
no old-profile job is queued, submitting, running, or transfer-pending.

## Consequences

Existing successful clips may remain downloadable until their normal 72-hour
MP4 expiry, and their SQLite rows may remain until their normal 30-day cleanup.
They are retained data, not an executable compatibility contract: V3 does not
list, validate, dispatch, or reconstruct their retired profile.

Callers must select a profile deliberately. This makes image preparation,
aspect-policy choice, and output geometry reviewable at the boundary. It also
makes a future profile addition a deliberate V4-style contract change with a
new bounded probe, rather than an extension of a hidden fallback chain.

## Alternatives rejected

- **Keep the old profile non-selectable.** It still makes it a runtime API
  contract and preserves fallback code.
- **Map old or missing IDs to a current profile.** A geometry change changes
  framing and violates the frozen request/output contract.
- **Keep a one-profile template and patch dimensions conditionally.** This
  makes retired geometry a hidden baseline instead of binding every dimension
  from the selected profile.
