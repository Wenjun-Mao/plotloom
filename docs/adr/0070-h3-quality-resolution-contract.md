# ADR 0070: H3 quality and resolution contract

**Status:** Accepted

## Context

The original H3 gateway used a `profileId` that combined two independent
decisions: an output geometry and a sampling recipe. That made it difficult to
offer the reviewed Turbo and Base-20 paths without multiplying opaque IDs.
It also allowed queued work to be rendered by looking up mutable catalog state
at dispatch time.

The reviewed local evidence establishes four named quality paths across the
six supported horizontal and portrait resolutions. Plotloom itself needs only
the default image-to-video path, while colleagues need a simple direct API.

## Decision

Gateway creation requests use a required exact `resolution` and an optional
integer `quality`, defaulting to `1`. The only admitted qualities are:

- `1`: V1.2 Turbo-4 / Euler / explicit 6:3 shifts;
- `2`: V1.0 Turbo-4 / res_multistep / explicit 6:3 shifts;
- `3`: V1.0 Turbo-8 / Euler / explicit 6:3 shifts;
- `8`: Base-20 / res_multistep / native H3 12:3 shifts.

Every accepted job persists a canonical execution snapshot containing the
quality, geometry, recipe/version, renderer version, and frame settings. The
worker renders exclusively from that snapshot. Base-20 removes the Turbo LoRA
and sigma-shift nodes; it is not represented as a zero-strength Turbo graph.

`profileId` is removed from gateway requests and responses. Retired gateway
SQLite state is not migrated or replayed: operators archive the identified
state and deploy a clean data directory. Plotloom continues to use a narrow
internal quality-1 geometry catalog for its generic production-snapshot
framework, but its HTTP transport sends only `quality=1` and `resolution`.

## Consequences

- Colleagues can choose quality and portrait/landscape geometry independently.
- Queue semantics remain deterministic even after a source/catalog edit.
- No prior profile meaning is silently reinterpreted under the new contract.
- Adding a quality path requires a new evidence-backed catalog revision, API
  tests, renderer tests, and an explicit decision record update.

## Plotloom pacing-first admission amendment (2026-09-25)

Plotloom's new-job catalog v7 and adapter v6 admit quality 1 for development
iteration and quality 8 for production-review candidates, independently of the
six exact resolutions. The quality-8 descriptor is the gateway's Base-20
`res_multistep` recipe with native shifts and no Turbo LoRA; it is not a
strength-zero Turbo variant. Existing quality-1 profile IDs remain bound to
their original recipe and version. New profiles have version 2 IDs, and the
job request freezes quality, profile ID/version, geometry, seed and expected
frames. Gateway responses must match the frozen quality and resolution.
The preferred new-work choice is quality 8, while the gateway's own omitted
quality default remains 1. There is no quality fallback or automatic creative
acceptance; the director's reduced-shaking observation is not a guarantee.

The gateway's existing 5–15 integer-second API maps each request upward to
the first `17k+5` frame count at 24 fps. Plotloom now admits that same request
range and checks the exact frozen count at response and ingestion. Requested
seconds are capacity/input intent, not exact measured or authored playback
time. The reviewed segment path still admits only its existing 6/8-second
source timing and 8-second source take. End-frame conditioning and broader
playback timing are separate decisions under ADR 0082.

Rejected alternatives: relabel quality-1 IDs as quality 8, synthesize a Base-20
recipe from Turbo fields, or treat the 5–15 request range as automatic playback
eligibility. Regression checks cover the gateway frame formula, frozen quality,
wrong-quality responses and old quality-1 profile interpretation.
