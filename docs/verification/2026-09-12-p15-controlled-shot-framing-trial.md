# P1.5 controlled shot-framing trial — 2026-09-12

This is a test-only, real built-in-ImageGen trial. It is not a production
approval, a creator keyframe selection, a still preview, or a universal visual
quality claim.

## Scope and retained runtime evidence

- Source revision: `fa3d65a3144f7d73fbfe4b96840c4b1ce995e302`.
- New isolated runtime root:
  `/Users/wjmao/projects/HU/plotloom-shot-trial-Rj57hk/`. It has a new SQLite
  database, artifact root, and image exchange; it did not clone or mutate the
  earlier rehearsal database.
- The only imported input was the previously frozen Mara reference bytes, read
  from the earlier rehearsal root. The new public-API managed-asset import and
  selected identity decision both retained original hash
  `4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1`.
- The test project was created through the public authoring API:
  `958d3b10-d709-4618-a7a3-236fcc52412b`. Its explicitly recorded storyboard
  Approval is `90070897-807b-4f7e-a786-ba27d4714ae0`, revision `r1`, attributed
  to `Codex`; its selected character-reference decision is
  `cf073ec4-a8d0-49a0-bd8c-30642c02b553`, revision `r1`.
- Each package was created and copied through the public API, pinned before
  generation, and accepted through its public Refresh endpoint. Each specialist
  made exactly one built-in ImageGen call. A first wide-job pin attempt used the
  job root rather than its inner `package/` directory and stopped before any
  ImageGen call or delivery; the corrected pin succeeded. No fourth image was
  generated.

| Shot | Job / request hash | Input reference SHA-256 | Built-in task | Output SHA-256 | Retained delivery |
| --- | --- | --- | --- | --- | --- |
| Tight close | `ij_5096811a12f94bb8831a87fea86d9190` / `798e1c19cd2548cd0d4933872b0d59c7e5b9fedd9d0d422e34b2acb3d1e53693` | `4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1` | `00aab59a-5e3d-4ce7-8f17-90f339141dc2` | `c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd` | `/Users/wjmao/projects/HU/plotloom-shot-trial-Rj57hk/image-exchange/jobs/ij_5096811a12f94bb8831a87fea86d9190/delivery/completion.json` |
| Profile medium | `ij_b8569b5958b445feb9e5acbdeacaf463` / `8fd0c9eb6d1346f76ed3c89973838c91ca90b897c34029703b00d478d3a73eef` | `4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1` | `exec-f3d2473c-5083-40f9-b418-2e0e132a9b26` | `f68e8036326a7a227e0a88e9f3e66014645b4cf080f7433dda7d3287ab64b3be` | `/Users/wjmao/projects/HU/plotloom-shot-trial-Rj57hk/image-exchange/jobs/ij_b8569b5958b445feb9e5acbdeacaf463/delivery/completion.json` |
| Environmental wide | `ij_6b17a44ad60a482390a979aba5175fee` / `e5eeead964133977d60c2e8e284fbe4cb10c701c5e289675e9e9709fc92b6196` | `4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1` | `exec-8cd5b362-da17-455c-a594-4f37d4337879` | `258f5358b1f9d47310b51bf5448d0c5b5e1f1c76faf4e0d688a938706ef59f75` | `/Users/wjmao/projects/HU/plotloom-shot-trial-Rj57hk/image-exchange/jobs/ij_6b17a44ad60a482390a979aba5175fee/delivery/completion.json` |

The table's delivery paths are absolute paths within the isolated runtime root.
Each completion records the exact prompt, reference-use attestation, executor
pin, and the following delivery limitations:

- Close: one generated candidate only; it is not storyboard Approval, reference
  selection, or a reviewed keyframe.
- Profile: unreviewed generated candidate; visual continuity, anatomy, and
  framing remain subject to creator review; it is not storyboard Approval or
  reference selection.
- Wide: identity continuity is generated from the supplied reference; it is not
  creator Approval or reference selection.

## Exact prompts and observed outcome

### Tight close

```text
Use case: photorealistic-natural
Asset type: cinematic storyboard still for Plotloom
Primary request: Create one stable, eye-level, tight head-and-shoulders close-up of Mara Vale, a tired but precisely focused municipal archivist in her late thirties, concentrating before dawn in a municipal archive reading room.
Input images: Image 1 is a character_identity reference for Mara’s durable facial identity only. Preserve her recognizable facial structure, short dark wavy hair, thin round wire glasses, and overall build. Do not transfer Image 1's pose, framing, crop, camera, lighting, setting, hands, reel, desk action, or any layout.
Scene/backdrop: faint, softly out-of-focus archival shelving and a dusty dawn skylight; the reading room is only a subtle background context.
Subject: Mara only, wearing a charcoal wool coat, with a controlled, inwardly focused expression. The shot state is focused and tired, not smiling.
Style/medium: naturalistic cinematic still photography, realistic skin texture and fine hair detail.
Composition/framing: frozen close framing—Mara’s face fills the frame in a tight head-and-shoulders close-up. Frame from just below the shoulders upward. No other person. Hands, the film reel, the desk, and all work action are deliberately outside the crop and must not be visible.
Lighting/mood: cool dawn light from the skylight, restrained and intimate; stable eye-level camera.
Constraints: maintain only Mara’s durable identity from Image 1; use this prompt for all shot-specific clothing, pose, expression, lighting, setting, and camera facts. No hand, glove, film reel, desk, or work tools visible anywhere in frame. No text, watermark, border, collage, or split screen.
Avoid: reference pose transfer, reference composition transfer, medium or wide framing, visible hands, visible props, extra characters.
```

The retained result is materially tighter than the original rehearsal close:
head-and-shoulders only, with no hands, reel, or desk visible. Hair, glasses,
coat, and face remain consistent with the selected reference.

### Profile medium

```text
Use case: photorealistic-natural
Asset type: frozen Plotloom storyboard keyframe
Input image: Image 1 is character_identity reference for Mara Vale only. Preserve her durable identity—woman in her late thirties, short dark wavy hair, thin round wire glasses, recognizable facial structure and build. Do not copy the reference image's pose, framing, crop, camera, lighting, setting, props, or action.
Primary request: Create one photorealistic cinematic still of Mara Vale carefully turning a fragile aged-metal film spool with her dark-gloved RIGHT hand at an oak restoration desk.
Scene/backdrop: municipal archive reading room: tall archival shelving, card-catalog drawers, oak restoration desk, dusty skylight.
Subject: Mara is the only visible person. She is focused and tired, wearing a charcoal wool coat and exactly one dark archival glove on her RIGHT hand; her left hand is ungloved and may remain unobtrusive.
Style/medium: realistic cinematic archival drama, natural material texture.
Composition/framing: TRUE FULL SIDE-PROFILE MEDIUM SHOT FROM MARA'S LEFT, eye level, stable camera. The camera is positioned on Mara's left and sees only a clean left-facing-profile silhouette/contour, not a three-quarter view and not a front-facing face. Frame her from about mid-torso upward at the oak desk; keep the spool and her dark-gloved right hand clearly visible in the medium shot.
Lighting/mood: cool dawn light through a dusty skylight, quiet controlled concentration.
Materials/textures: worn oak desk, aged metal reel, delicate exposed film strip, charcoal wool.
Constraints: The dark-gloved right hand is actively and carefully turning the fragile spool. Maintain a true side profile. Mara's face remains recognizably in profile. One visible character only. No dialogue speakers. No text, captions, logos, watermark, extra gloves, or extra hands.
Avoid: any three-quarter pose, frontal face, frontal camera angle, transferred reference composition, transferred reference lighting, transferred reference setting, transferred reference action, exaggerated drama, or distorted hands.
```

The profile framing is distinct and identity anchors remain recognizable. Its
prompt language is itself ambiguous: it asks for a camera from Mara's left but
also a “left-facing-profile silhouette,” without defining how that
camera-relative instruction maps to screen direction; the actual result faces
screen-right. The right-hand glove continuity is **not accepted**: the
conspicuous dark-gloved arm is the foreground/near arm, which is visually more
consistent with the left arm in the stated camera view. The still lacks an
unambiguous anatomical cue, so its side is uncertain and a right/left mismatch
is plausible. This trial did not regenerate it.

### Environmental wide

```text
Use case: illustration-story
Asset type: frozen Plotloom cinematic story still
Input images: Image 1 is a character_identity reference for Mara Vale only. Preserve her durable identity: a woman in her late thirties with short dark wavy hair, thin round wire glasses, and a charcoal wool coat. Do not transfer Image 1's pose, framing, crop, camera, lighting, setting, or action.
Primary request: Create the frozen shot "Archive at dawn": Mara continues careful work with one fragile aged metal film spool at an oak restoration desk while the municipal archive reading room is the primary visual subject.
Scene/backdrop: a large municipal archive reading room at dawn, dominated by towering archival shelving and banks of wooden card-catalog drawers; a high dusty skylight visibly throws cool early-morning light and floating dust through the room.
Subject: Mara, deliberately small in frame at the oak desk, focused on gentle conservation work with the fragile spool. Her single dark archival glove is on her right hand; no glove on the other hand.
Style/medium: cinematic, grounded photorealistic film still with authentic archival textures—oak, aged wood drawers, labeled archive boxes, paper, metal shelving, and delicate film.
Composition/framing: strict environmental wide shot, stable eye-level camera. The room, shelving, card catalogs, and dusty skylight dominate the frame; Mara is small, clearly readable, seated at the desk in the lower-middle distance. The complete frame must emphasize the architecture and setting rather than a portrait or close-up.
Lighting/mood: cool blue dawn daylight filtered through the dusty skylight, quiet, focused, lightly atmospheric.
Constraints: Only Mara is visible. The spool remains on the oak desk. No text, no captions, no watermark, no modern computer screens, no dramatic action, no close framing, no reference composition transfer.
Avoid: close-up portrait, medium shot, warm sunset lighting, extra people, extra hands, visual clutter that obscures the shelves, card catalogs, or skylight.
```

The retained wide result is a genuine environmental wide: Mara is small at the
desk, while shelving, card catalogs, and the skylight dominate. At this scale,
the selected hair, glasses, and coat anchors remain recognizable; anatomical
glove-side verification is not claimed.

## Interpretation

This controlled result demonstrates three materially distinct reference-
conditioned compositions from the same frozen identity reference: tight close,
profile medium, and environmental wide. It does **not** isolate a single cause
for that improvement: both the clarified author briefs and the explicit
specialist role-boundary instruction changed together. The profile prompt's
camera/screen-direction ambiguity and its glove-side uncertainty remain
concrete continuity gaps for any future acceptance work; they were retained
rather than concealed or retried.

Focused verification before the trial: the image-specialist skill passed
`quick_validate.py`, and `uv run pytest tests/backend_core/test_image_jobs.py -q`
passed 18 tests (with one existing Starlette deprecation warning). Each real
delivery's server-side Refresh admission returned `accepted`.

Usage and cost telemetry were unavailable for these built-in ImageGen calls.
