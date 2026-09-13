# ADR 0034: Provider-neutral video adapters and local H3 execution

## Context

P2's first implementation is intentionally narrow: it freezes an AtlasCloud
Wan 3.0 request, reserves a shared paid 100-second allowance, uploads a hosted
image, and recovers only a known prediction ID.  Its persistence schema and
`VideoJobService` therefore assume Atlas request and response envelopes.

Spark's MiniMax-H3 gateway has a materially different, already tested
contract.  It accepts an authenticated local asset upload, requires an
explicit image-aspect policy, submits one fixed ComfyUI profile, and exposes a
gateway-owned job ID and output proxy.  H3 is local execution, not a priced
Atlas request.  Treating its asset ID as an HTTPS URL, parsing its job as an
Atlas prediction, or charging it to the Wan ledger would be a false contract.

## Decision

Introduce a versioned video-adapter boundary.  An adapter owns only the
translation between a frozen Plotloom production snapshot and one trusted
provider contract:

- its stable `adapterId` and `adapterVersion`;
- immutable capability values (profile/model, duration, output dimensions,
  native-audio support, and input requirements);
- upload, submit, known-job polling, and output retrieval parsing;
- stable, secret-free failure codes.

The production snapshot freezes the adapter identity, capability version,
normalised request, and any provider-specific public parameters before a
dispatch claim.  A caller cannot pass arbitrary provider JSON, model names,
workflow paths, endpoints, or secrets.

`atlas_wan.v1` preserves the existing P2 request shape, HTTPS-output
validation, known-prediction recovery semantics, and the existing
`wan-3.0-pilot-100-requested-seconds` ledger.  Historical V1 snapshots are
read without reinterpretation.

`minimax_h3_gateway.v1` targets only the deployed
`minimax_h3_fp8_turbo4_480p` profile: 864x480, 124 frames at 24 fps, about
5.167 seconds, and native audio.  It requires one of the gateway's explicit
aspect policies; its initial workbench default is visible as
`cover_center_crop`, never a silent stretch.  Its gateway job ID is a known
remote identity.  A submit with an uncertain outcome remains
`outcome_unknown` and is never replayed.

H3 is enabled only by explicit server configuration and a server-held bearer
key.  The browser never receives the key, cannot alter its endpoint, and does
not select a backend per request.  Existing provider-settings fields remain a
public display/control-plane projection; runtime admission selects only an
enabled, trusted adapter matching its server configuration.

Because H3 runs locally, it does not decrement, reset, or otherwise affect
the priced Wan pilot ledger.  Admission is bounded by the gateway's own
durable queue capacity.  This is a capacity safeguard, not a hidden cost
budget.

## Consequences

The next implementation creates a typed H3 transport and adapter, preserves
all Wan tests and snapshots, adds explicit H3 request/provenance fields, and
makes the workbench explain the active profile's duration, resolution, audio,
and aspect policy.  The UI must not label a low-level audio stream as accepted
dialogue: a reviewer evaluates intelligibility, lip sync, performance, and
cross-shot voice continuity from the actual candidate.

Future remote or local backends can add a new adapter version with a distinct
capability record; they must not add model-name branches to the H3 or Atlas
adapters.  Video generation remains candidate production: it never changes
canonical story data or bypasses keyframe, identity, approval, or explicit
candidate-selection gates.
