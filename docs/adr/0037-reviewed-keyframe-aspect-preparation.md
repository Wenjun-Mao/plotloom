# ADR 0037: reviewed keyframe aspect preparation

## Context

The first H3 portrait catalog probe used a horizontal reviewed keyframe with
the gateway's `contain_pad` input policy. The gateway deterministically put
that image on a black portrait canvas; H3 then treated the empty areas as
generative context. One profile preserved the bars while another generated an
unstable vertical recomposition. The output geometry was correct, but the
input composition was not a reviewable portrait keyframe.

Letting a gateway choose between padding and cropping implicitly hides a
creative decision inside a video job. It also makes a video candidate
impossible to compare honestly with its reviewed still. That does not mean
black canvas is always wrong: an author may deliberately want a horizontal
composition held inside a vertical frame.

## Decision

New H3 video jobs default to `reject_mismatch`. A selected keyframe must match
the frozen profile aspect ratio before a video job is admitted; historical
snapshots retain their original policy and remain readable/retrievable.

An author may instead explicitly enable `allowLetterbox`. That narrow,
profile-owned input-frame mode freezes `contain_pad` with the job and permits a
mismatched reviewed keyframe. It means black bands are intentional input
composition—not an implicit crop, a model correction request, or a bypass of
the selected-keyframe, provenance, profile, output-geometry, or review rules.

For the Step 4 pilot, the user has also approved an explicit,
mutually-exclusive `allowCenterCrop` choice. It freezes
`cover_center_crop` with the selected H3 profile. The gateway alone performs
that deterministic centered crop from the original reviewed source bytes;
Plotloom neither creates a local derivative nor starts an ImageGen sizing
attempt. The frozen job still records the original asset ID/hash, reviewed
binding, source provenance, profile and explicit choice. The choice is made in
media preparation before the video job is frozen; it is not a Storyboard Gate
decision, and small aspect differences never imply consent.

For a mismatch, Plotloom offers these explicit preparation paths:

1. select or import an already matching source;
2. freeze `allowCenterCrop` and let the gateway apply its reviewed centered
   crop to the original source; or
3. freeze `allowLetterbox` and let the gateway apply intentional black canvas.

None of these paths silently replaces the reviewed keyframe. Existing managed
derivative and ImageGen-adaptation history stays readable, but is not created
by the Step 4 crop choice.

## Consequences

- `cover_center_crop` is available to new H3 work only through the explicit
  frozen `allowCenterCrop` mode; `contain_pad` remains available only through
  the explicit frozen `allowLetterbox` mode. `reject_mismatch` remains the
  default.
- The input-frame flags are mutually exclusive and are bound to the policy in
  the immutable request. Gateway responses that report a different policy are
  rejected before their known ID can advance the job.
- Currentness checks both request and snapshot hashes before dispatch, so a
  tampered crop choice cannot borrow a current reviewed selection.
- The UI may describe a target profile and mismatch but the server owns all
  dimensions and rechecks currentness before it freezes the gateway request.

## Follow-up guardrails

Tests must prove that default H3 admission rejects mismatches before a
reservation or provider call; an explicit letterbox request is accepted only
with `contain_pad`; an explicit crop request is accepted only with
`cover_center_crop`; both retain all other checks; the original reviewed bytes
and source binding survive restart; and a tampered frozen choice becomes
non-current rather than dispatchable.
