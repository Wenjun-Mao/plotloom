# ADR 0066: H3 qualified per-job duration contract

**Status:** Accepted

## Context

The reviewed H3 gateway V4 accepts whole requested durations from five through
fifteen seconds and freezes the resulting 24-fps `17k + 5` frame grid per job.
Plotloom's catalog profiles instead exposed five seconds and 124 frames as
profile-owned constants.  The adapter consequently rejected an otherwise
supported eight-second I2V request and checked every delivered MP4 against the
five-second default.  That made the production contract narrower than the
gateway for the wrong reason: mutable display defaults were being used as the
durable job contract.

The F6 readiness receipt establishes an eight-second qualification target, not
general product adoption of the gateway's five-to-fifteen-second range.  A
browser, gateway response, restarted runtime, or physical output must not be
able to substitute current profile defaults for the values frozen when the job
was prepared.

## Decision

H3 profile `durationSeconds` and `frameCount` remain public defaults: five
requested seconds, 124 frames at 24 fps (about 5.167 seconds).  Plotloom
currently admits exactly two requested durations for a new H3 I2V job: five
and eight seconds.  Eight seconds freezes 192 frames at 24 fps (exactly eight
seconds).  All other values are rejected by the adapter before a row,
reservation, preflight, or transport request; the UI exposes only those two
choices and keeps five selected by default.

The immutable production contract, persisted in the request snapshot, owns the
actual requested seconds, expected frame count, fps, profile geometry, native
audio requirement, aspect policy/input mode, seed, adapter version, and exact
configured backend binding.  The compiler reads only that snapshot.  Submit
and poll envelopes must bind their requested duration, frame count, fps,
geometry/profile, audio, aspect policy, and seed to that frozen contract.
Observed MP4 ingestion applies the same contract to duration, frame count,
frame rate, geometry, H.264 video, and AAC audio.  Requested duration and
delivered duration stay distinct: the existing one-frame physical-duration
tolerance remains only for the observed probe.

Gateway health retains its exact trusted profile-catalog validation; it does
not become a Plotloom authorization for every duration the gateway can parse.
No gateway, deployment, upstream service, compatibility layer, replay path,
or post-processing path is introduced.

## Consequences

- A restart cannot infer a job's output expectation from the current profile
  default or current UI selection.
- Tampered snapshots, mismatched submit/poll envelopes, and wrong physical
  output fail closed before publication; known-ID failures remain retrievable
  and unknown dispatches remain non-replayable.
- Local H3 capacity dispatch continues to reserve the job's requested seconds
  through the established direct-composition identity path; it does not touch
  Wan accounting.
- Adding another H3 duration is a new explicit product-contract decision and
  qualification, not a gateway-range expansion.

## Rejected alternatives

- **Expose the gateway's full five-to-fifteen range.** Gateway capability is
  not Plotloom product qualification.
- **Derive the output contract from the current profile on reconcile.** It
  makes retained job evidence mutable and permits restart drift.
- **Pad, trim, stitch, or tolerate plausible output.** Those hide a contract
  violation rather than preserve the requested media unit.
