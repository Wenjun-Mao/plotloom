# U4 opening H3 reviewed-English trial · 2026-09-24

## Scope and source

One authorized H3 trial tested the [reviewed-English direction package](2026-09-24-h3-reviewed-directions-offline.md) for the accepted six-second `opening-s1-c1` cut. The new trial is an isolated supported copy at `.local/relay/real-shot-reviewed-en/{outputs,application}` under project `fbb913c8-534b-4439-ba68-211e70ec743d`. It retained comparison jobs A and B, their original and derivative bytes, and their unselected status. The 8832 first-trial and 8833 comparison services and project roots were not changed. No new ImageGen asset, alternative provider, automatic fallback, source edit, or second H3 submission was made.

The copied keyframe is the same reviewed 1672×941 PNG, independently hashed as `7c4c375db892b1b1cbc02136df59ab7fb627affbaf9437e2202b9fb939627d48`. The accepted shot still says `沈岚把铜质熔断器放在两条并列插槽之间。`; its sole resolved spoken line remains `一枚，只够一边。`.

## Fresh preview, frozen request, and sole dispatch

The server's fresh source inventory had seven review fields and source hash `56e55747592801bdb21d9dc99b96d488a6784155ff8a2bfc796b9f78fc989d3b`. The complete compiled prompt matched the offline proposal byte for byte, SHA-256 `685b03af7d41648e9857ffd84995d67c030920165797b141a6b51e8beed66c3c`. It used English composition, action, camera, voice, performance, and explicitly reviewed physical-sound directions; the Chinese action was absent from provider directions and the Chinese dialogue appeared once inside `<d>`. No retired “only vocal utterance” instruction was present. The seven exact field mappings and full prompt are preserved in the [offline preview](2026-09-24-h3-reviewed-directions-offline.md); the fresh source/prompt hashes were checked again at preparation.

Prepared job `vj_6dbfa8a977cd4fc2b44e926b29c0f01b` froze compiler `plotloom.h3-i2va.v3-reviewed-en`, request hash `aada7155c7d4455c634d566379acf332aa4664b046a3ec513507f2e91bf296f7`, and the exact reviewed package. The provider binding retained adapter 5, capability 6, and endpoint fingerprint `2a2a8dfc62e5be12fb81ae400b215b7d9dbb39060679c26e4a84319762d1fcdb`. Request controls matched A/B: `minimax_h3_quality1_landscape_960x544_v1`, quality 1, 8 seconds / 192 frames / 24 fps / 960×544, native audio, seed `20260923`, and explicit `cover_center_crop` of the same PNG. The canonical authored cut stayed six seconds.

Before the one POST, gateway health was `ok`, contract 6, zero queued jobs, zero active dispatches, and concurrency 1; its catalog included the exact profile resolution. The attempt was recorded before dispatch at 05:13:22 UTC in the isolated root. Exactly one submit at 05:13:37 UTC returned known prediction `h3_edad2aa192f64831b5531cc47010c9fe`. Only that ID was reconciled. No ambiguous outcome or retry occurred.

## Retained media and review boundary

The original ingested current and unselected, SHA-256 `7f1fb4000f4e51dc3d39387987fd1d90a7cc2888beee22d8081bf7668b64bdb4`. Trusted observation reports 8.000 seconds, 192 frames at 24 fps, 960×544, H.264/AAC. The public segment API prepared an unselected `[0,144)` proposal, ID `b27a0c6a-4570-461c-a783-1118196e5e4b`, SHA-256 `464deab878728589b588fd8ac97538e44661aff8d161e5b6c82caa64f2b7ab4e`. It reports 6.000 seconds, 144 frames, an exact 0–6-second audio interval, and 192,000 decoded 32-kHz samples. Local asset SHA-256 checks matched both recorded hashes. The original was retained unchanged.

The credential-free loopback review service is `com.plotloom.real-shot-reviewed-en` on port 8835. It reports the video backend disabled while both media routes continue to serve range requests after restart. The [workbench](http://127.0.0.1:8835/v2/?project=fbb913c8-534b-4439-ba68-211e70ec743d&stage=storyboard&entity=shot%3Aopening-s1-c1#video-segment-review-vj_6dbfa8a977cd4fc2b44e926b29c0f01b) shows all three unselected candidates; use these exact C links to avoid confusing visually similar cards:

- [Full eight-second original](http://127.0.0.1:8835/api/v2/projects/fbb913c8-534b-4439-ba68-211e70ec743d/video-jobs/vj_6dbfa8a977cd4fc2b44e926b29c0f01b/media)
- [Proposed six-second segment](http://127.0.0.1:8835/api/v2/projects/fbb913c8-534b-4439-ba68-211e70ec743d/video-segments/b27a0c6a-4570-461c-a783-1118196e5e4b/preview)

The headed workbench was inspected at 1440×900 and 1920×1080 without browser console errors; screenshots are in `output/playwright/h3-c-manager-{1440,1920}.png`. Both exact C media elements loaded unmuted with controls, expected browser durations (8 and 6 seconds), and `readyState` 4. Sampled frames at 0.5, 4, and 5.5 seconds showed a continuous keeper/switchboard shot and no obvious subtitle in those frames. This is visual sampling, not a whole-video or dialogue-quality verdict.

No agent or manager listened to and transcribed the Mandarin track. The director still needs to audition the full original and proposed segment, including the six-second boundary, for the prior extra action sentence, intended-line clarity, other vocalizations, and visual story fidelity. Ingestion and playable media do not establish that the speech defect is fixed. All three candidates and all three proposals remain unselected; the other 26 route cuts still have no current selected playback.

## Verification and provenance

The implementation baseline was pushed at `8835cb4` after a full backend run of 747 passing tests, scoped API Ruff checks, and lockfile verification. This trial changed no tracked runtime code. Read-only checks after generation confirmed 8832 still has only A, 8833 still has A/B, and the new isolated 8835 root has A/B/C; all reported unselected. The pre-dispatch record, exact reviewed request, service entrypoint, and no-credential service setup are retained in `.local/relay/real-shot-reviewed-en/`. Browser screenshots and sampled frames are local untracked evidence.
