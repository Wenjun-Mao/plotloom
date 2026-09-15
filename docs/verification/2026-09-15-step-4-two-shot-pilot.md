# Step 4 two-shot creative pilot — production readiness block

Captured 2026-09-15 at `6b3f7f5` from the current project-folder runtime.
This is a secret-free operational preflight receipt, not a creative-pilot,
media-quality, or Alpha-qualification claim.

## Intended bounded journey

The authorized journey remains one new, project-owned cinematic-realism project
with a Chinese two-shot station scene: a single protagonist retrieves a lost
keepsake, checks it, and puts it safely away. It would use the saved active
local text profile for the normal four-stage generation, then the public
approval, identity-reference, ImageGen prepare/copy/refresh/select, and direct
H3 I2V contracts. The planned two adjoining five-second clips would remain
unselected until genuine normal-speed audiovisual review establishes an
explicit Codex engineering decision.

No part of that journey was started here.

## Readiness observation

One owned local Plotloom runtime was started against the fresh Step 3
application store. No profile was created, updated, activated, disabled, or
otherwise rewritten.

| Checked contract | Observation | Disposition |
| --- | --- | --- |
| Active saved text profile | `default`; its single profile probe returned `available` with `readiness.models_verified` | Text authoring could be admitted without changing profile state. |
| Production video backend | `enabled: false`, reason `h3_video_not_configured` | Blocked before any gateway health or generation request. |

The H3 result is the causal blocker: the approved pilot permits only the
configured self-deployed H3 I2V backend and explicitly excludes Atlas/Wan,
T2V, fallback backends, gateway/deployment edits, and blind resubmission. A
disabled runtime has no admissible route to create either required clip.

## Preserved boundary

- No project was created under `outputs/`; the retained Step 3 proof project,
  raw legacy archive, application profiles, and accounting state were left in
  place.
- No stage generation, storyboard approval, image-job package, ImageGen call,
  managed asset, character-reference decision, video job, provider request,
  accounting reservation, snapshot, restore, or browser playback was created.
- No secret, endpoint value, request identifier, or provider response is
  recorded in this receipt.
- The owned local proof server was stopped after the observation. No gateway
  call was attempted, so there is no unknown provider outcome to reconcile.

## Required next action

An operator must configure and restart the already-approved self-deployed H3
runtime so `GET /api/v2/video-backend` reports the trusted MiniMax H3 adapter
as enabled. This assignment does not authorize that configuration or deployment
change. Once the gate is available, begin again with one fresh labelled project
and execute the full bounded pilot; do not reuse an archival or Step 3 proof
project as its canonical source.

### Configuration correction recorded after this receipt

The later gateway-owner handoff established that the deployed direct gateway is
the V4 contract with the same six reviewed profiles. Plotloom's client catalog
marker must therefore be `VIDEO_MODEL=minimax_h3_gateway_catalog_v4`; a stale
V3 marker was a separate configuration/admission mismatch, not evidence that
the gateway or this untouched pilot state changed. The environment, deployment,
and pilot remain out of scope for this receipt and must still be configured by
an operator before retrying Step 4.
