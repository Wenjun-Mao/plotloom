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
