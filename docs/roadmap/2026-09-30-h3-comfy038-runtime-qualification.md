# H3 ComfyUI 0.38 runtime qualification

Owner approved on 2026-09-30. Specialist-only; Plotloom integration, director
contact, merge and push remain on hold.

## Outcome and boundary

Qualify ComfyUI `v0.38.0` (`6b747c0428c343e1417219641db93a4fb7cb69ae`)
against the running `d43a5fa20c8547ff42d13232f589a06536c42b97` / 0.35.0 image.
The current H3 decoder internally tiles and stores raw overlap tails before
blending. Upstream PR 16436 changes this to composited neighbours. The remedy
belongs in the decoder/runtime, not prompts or the gateway's image preparation.

Keep models, gateway contracts, quality catalog, Torch/CUDA/SageAttention,
launch flags and input/output/model data unchanged; use a copied, isolated
Comfy user directory for the candidate. Do not install W6A8. Build a pinned
candidate derived from the current image, retaining its GB10 source mod and
freezing non-Comfy dependencies. Any dependency conflict is a planning stop,
not permission to silently replace the GPU stack.

## Serial steps and call cap

1. Capture current runtime and idle queues. Preserve its exact image under an
   explicit rollback tag. Build the candidate while the current service runs.
2. Freeze two genuine stills and graphs: quality 1, 1280x704 and 704x1280,
   124 frames, one fixed seed. Submit each once on the baseline (two calls).
3. With all generation queues empty, stop gateway admission, switch only
   ComfyUI to the candidate and verify readiness. Submit the same two graphs
   with output destinations changed only (two calls).
4. Run one already reviewed Ref2VA portrait first-frame/voice case, 576x1024,
   124 frames (one call). Preserve reference and prompt hashes.
5. Check graph/cache provenance, full video/audio decode, dimensions, duration,
   audio, seams, measured time and sampled memory. Retain an inspectable A/B
   page. Technical qualification does not imply human creative acceptance.
6. Restore baseline unless evidence supports a safe promotion; record the exact
   final image, health and unchanged gateway/Voice Lab state. Preserve rollback.

Maximum five generation submissions. No automatic replay after an ambiguous
submission or timeout. After a known failure, preserve evidence and diagnose
before any separately bounded replacement. Stop immediately for unrelated
queued work; do not cancel it. Use one source/runtime owner.

## Evidence and stopping condition

Retain runtime/package deltas, frozen workflow/input hashes, each accepted
Comfy prompt ID, history/cache evidence, media metadata, sampled memory and
full-stream decode results. No secrets in tracked receipts. Keep experiment
media separate from gateway-managed outputs. Update the reproduction guide
with candidate/final status; do not rewrite historical installation evidence.

Sources: [release](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.38.0),
[seam fix](https://github.com/Comfy-Org/ComfyUI/pull/16436),
[offload fix](https://github.com/Comfy-Org/ComfyUI/pull/16485).

Stop after the bounded technical checks and retained review material, or at a
demonstrated blocker with baseline restored and evidence saved.

## Original five-call implementation status · 2026-09-30

The five-call cap is exhausted. Technical media checks and an independent
CPU decoder-composition regression passed. The baseline image/container and
untouched user directory are restored; gateway, Voice Lab and Qwen Image are
healthy. **Full visual qualification and promotion remain incomplete**:

- Landscape input was a padded doorway still, not the prompt's astronaut;
  both videos blend scenes. This test-design mistake was caught in frame
  review and retained; a corrected pair needs separate bounded authority.
- Valid portrait/Ref2VA whole-video visual/audio review is pending.
- Candidate startup migrated only an isolated user-directory copy. Its
  catalog discards/rebuilds metadata; production disposition must be decided
  before adoption, not hidden inside an image update.

See the [receipt](../verification/2026-09-30-h3-comfy038-runtime-qualification.md)
and [ADR 0095](../adr/0095-h3-runtime-qualification-and-catalog-isolation.md).
No director contact, merge, push, model switch or additional call is authorized
by this status. Stop here with work and rollback preserved.

## Separately approved follow-up

The owner reports no noticeable quality difference across the displayed pairs.
After the proposal to perform only one corrected landscape pair and treat 0.38
as a maintenance upgrade, the owner replied “agreed”. This follow-up permits
**two additional calls total**, one per runtime, with a pixel-reviewed 1280×704
spacecraft still, matching prompt, quality 1, fixed seed and 124 frames.
Original cases/receipts stay immutable; use a separate experiment root.

Read-only production-catalog inspection found zero assets, references,
metadata rows and tag assignments (24 standalone tag definitions). Thus no
bound user metadata was identified as a migration blocker. Conditional
promotion keeps the original image/container/user directory intact and uses
a separate stable `data/user-v038` copy for the new runtime. Models and other
service data stay unchanged; no destructive catalog reset is needed. Stop and
restore baseline for a demonstrated failure or material regression, without
replaying or expanding the call cap. No merge, push or director contact.

### Follow-up implementation status

Both corrected landscape calls completed and fully decoded with native audio;
sampled operator review found no material regression. The exact 0.38 image is
adopted using `data/user-v038`; the original 0.35 image, stopped container and
user directory remain preserved. Restart smoke, services and voice-file checks
passed. See the [adoption receipt](../verification/2026-09-30-h3-comfy038-maintenance-adoption.md).
Both call caps are exhausted. Broader memory/creative qualification and all
Plotloom delivery authority remain outside this closure.
