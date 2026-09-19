# ADR 0069: H3 explicit sampling recipes and profile cutover

**Status:** Accepted

## Context

The original H3 geometry profile IDs represented a four-step Turbo LoRA but
did not render its required sigma shifts. ComfyUI therefore applied the base
H3 video/audio defaults of `12 / 3`, while LightX2V's published FL2VA 4-step
v1.0 recipe specifies `4 / 6 / 3`. A visually plausible output did not prove
the intended recipe had run.

Changing values behind the original IDs would make old job records appear to
have used a different sampling trajectory than they actually did.

## Decision

H3 profile contract version 5 makes the full sampling recipe a typed,
profile-owned value: LoRA file and strength, steps, video/audio sigma shifts,
sampler, scheduler, and denoise. The renderer inserts a
`MiniMaxH3SigmaShift` node after the LoRA and passes its model to both the
scheduler and guider.

New jobs use six corrected `v2` geometry profile IDs with the published
LightX2V 4-step v1.0 `6 / 3` shifts. The original `v1` IDs stay in an internal
retired catalog with their observed `12 / 3` recipe so stored jobs can be read
or safely completed, but the public health catalog and creation endpoints no
longer admit them.

The active health descriptor includes the non-secret sampling recipe. The
Plotloom adapter mirrors and verifies that descriptor, while retaining retired
IDs only for frozen-job validation. This is a new capability contract, not a
browser-selectable model-path interface.

## Consequences

- New rendering cannot silently inherit base H3 sigma defaults.
- Historical evidence remains correctly interpretable rather than relabeled.
- A later LoRA or quality setting change needs a new profile/recipe version.
- The corrected recipe is a candidate until retained real-model evidence and
  review promote it; this ADR does not make an automatic quality claim.
