# F6 first live H3 clip — non-qualifying preserved result

Date: 2026-09-18. This receipt records one isolated live H3 submission. It is
not F6 audiovisual qualification, creative approval, a selected candidate, or
authorization for another clip.

## Result

One normal production H3 I2V attempt was created through the current adapter,
keyframe, identity-reference, snapshot, direct local-capacity accounting, and
ingestion owners. It completed and was retained **unselected**. Objective media
contract validation passed. The attempt is nevertheless **non-qualifying**:
the frozen compiler projection omitted the mandated Mandarin line `我在这里。`
and the quiet-room/no-narration/no-music directions. No second submission is
permitted for this result.

The root cause is the disposable upstream fixture's generic canonical shot:
the normal H3 compiler owns its prompt as an exact projection of frozen shot,
dialogue-cue, and audio-plan fields. Its snapshot contains `交代选择`,
`角色握紧信件。`, and `稳定推进`, with no dialogue cue or audio events. This
belongs in the fixture's author-owned canonical prompt inputs before preparation,
not in a gateway override, later correction, crop, TTS, retry, or post-process.

## Fixture and admission provenance

- Isolated fixture project: `666755c4-ff95-4dd7-853e-8cab98b0f051`, under the
  ignored current-ticket runtime. Its title and technical approval explicitly
  identify it as test-only and not human creative approval, F5 installation,
  canon, or a selected reference.
- Imported original: F2B C01 / Lin Che selected refinement, ImageGen
  `exec-db9ba9a2-5586-4d50-9393-3264809e2cf6`, SHA-256
  `1fb4700c73834b81c2ea3f64d6754cc0b24ba1bfcb472d8993161d2d7a2f2e0d`.
  The durable F2B project-local copy was used and visually inspected before
  admission; retained staging and older roots were not changed.
- Fixture managed asset: `b1d8f8ae-d8b7-4a91-a50a-a843e5535b2f`; C01 identity
  decision `9d59b9b2-1520-450e-a711-b725cf6404a3`; reviewed keyframe binding
  `5bd4baa0-e175-4ebe-af3c-e068d271d2f0`.
- Original geometry is `1145×1374`. The visually checked face-centered
  composition was frozen with the explicit gateway-only
  `cover_center_crop`/`allowCenterCrop: true` policy for Portrait Fast. No local
  derivative, pad, trim, or silent crop was made; original bytes remain bound
  in the snapshot.

## Frozen job and output

| Field | Observed frozen/ingested value |
| --- | --- |
| Plotloom / gateway job | `vj_ebe66930f17e48a59155da3ecbeed6f8` / `h3_057d11698f494f2a87fee35f86c9e79d` |
| Snapshot / request hash | `9331cd8ed4ff3d80786ce08ce03ba82b3c611500605f64be94e3591a78a5e145` / `820ec710f9897e955621cb9bd6542c6355294155c68cf374343903875712777b` |
| Profile and input mode | `minimax_h3_fp8_turbo4_portrait_576x1024_v1`; `cover_center_crop` |
| Requested contract | 8 seconds; 192 frames; 24 fps; `576×1024`; native audio; seed `18092026` |
| Local output SHA-256 | `1a00b5c82fc2452866fe13d70d35845d344ed760c49cc0928f74d8945c7d179f` |
| Decoded output | 8.000 seconds, `576×1024`, H.264 video, AAC audio, 24 fps, 192 video frames |
| Selection | unselected; current; no review decision |

The normal service completed authenticated preflight immediately before its one
submit. The H3 backend binding is retained as its public instance fingerprint
in the frozen snapshot; no key or endpoint is recorded here. The local H3
capacity policy was used, without Wan paid-pilot accounting.

## Playback and limits

The normal local `/media` route supplied the ingested MP4 and a local attended
browser displayed native media controls; playback activation was attempted.
The browser control surface then navigated/closed, and this environment cannot
hear audio. The preserved local review file is
`/Users/wjmao/projects/HU/plotloom/.local/relay/e7f90144-3860-491b-9926-87f055df4e58/outputs/f6-first-submitted-contract-mismatch.mp4`.

Neither controls, codec metadata, decoded frames, nor AAC presence establish
what was said, speaker/voice identity, lip synchronization, room-tone quality,
or music/narration absence. Because the frozen prompt itself missed the
required directions, this clip cannot become such proof even after human
listening. It remains retained only as an objective contract and fixture-failure
record.

## Independent read-only review

An independent Terra/high read-only reviewer inspected the retained snapshot,
API evidence, reconciled MP4, and the relevant ADR/readiness receipts before
this record was released. It confirmed the frozen 8-second/192-frame/24-fps
Portrait Fast contract and the matching H.264/AAC output hash. Its local probe
also found a stereo 32 kHz AAC track with non-silent amplitude; that fact does
not change any sensory limit. The reviewer independently confirmed the exact
frozen compiler projection above and its absence of the required line and
audio-direction fields. It made no file, fixture, runtime, or job change.

## Evidence and stopping condition

The complete API response sequence, fixture data, and current job state remain
under ignored `.local/relay/e7f90144-3860-491b-9926-87f055df4e58/`:
`evidence.json`, `submission-summary.json`, `reconcile-3.json`, and `outputs/`.
No valued pilot, F5 artifact, gateway deployment/configuration, source profile,
or staging asset was changed. There was one H3 submission and zero retry or
second-clip submissions. A corrective fixture design would need separately
approved scope before any new live dispatch.
