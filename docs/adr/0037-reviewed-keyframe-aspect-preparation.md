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
The choice is made in media preparation before the video job is frozen; it is
not a Storyboard Gate decision.

For a mismatch, Plotloom offers three explicit preparation paths:

1. select or import an already matching source;
2. create a deterministic centered-crop managed asset at one reviewed H3
   profile size; or
3. prepare a manual Codex ImageGen keyframe-adaptation job, which freezes the
   current reviewed keyframe, selected H3 profile, source binding, and exact
   required delivery geometry.

Neither path silently replaces the reviewed keyframe. A creator must inspect
the derived or generated asset, record its VisualIntent, and explicitly select
it for the shot before video admission. Adaptation deliveries whose dimensions
do not exactly match the frozen target profile are rejected.

## Consequences

- `cover_center_crop` remains a gateway capability solely to interpret
  historical frozen jobs. New H3 work may use `contain_pad` only through the
  explicit frozen `allowLetterbox` mode.
- A deterministic crop has source-hash, source-binding, target-profile and
  transform provenance, but is not mistaken for model-generated imagery.
- Image adaptation reuses the same-host P1 package/delivery boundary. The
  specialist receives the source keyframe as a named reference and an exact
  output contract; its output remains an unselected candidate pending review.
- New `keyframe_adaptation` request and output roles are additive. Existing
  P1 original/refinement packages retain their exact contracts.
- The UI may describe a target profile and mismatch but the server owns all
  dimensions and rechecks currentness before it creates either derivative.

## Follow-up guardrails

Tests must prove that default H3 admission rejects padding/cropping policies
and aspect mismatches before a reservation or provider call; an explicit
letterbox request is accepted only with `contain_pad` and retains all other
checks; deterministic crop provenance cannot be forged or applied after
selection changes; adaptation packages include their source keyframe and
reject wrong-sized deliveries; and neither derivative becomes the selected
keyframe implicitly.
