# F5 storyboard production-seam receipt — bounded, blocked candidate

Date: 2026-09-18. Baseline: `1364daa49e455836a784c0febf0e434928115b7c`.

## Scope and outcome

This is the first F5 slice only: one frozen, reusable storyboard handoff and a
read-only source mapping. It is not a storyboard installation, Approval,
reference selection, media job, H3 dispatch, TTS decision, UI/schema change, or
F5 product acceptance.

The exact current F4 input is script r2 from disposable project
`d3ad5da3-905e-4eb2-90c8-7d52d1cb4fd0`, canonical content hash
`ca7dc718a5164656c1da2bf7e88a6a8c7f8e8922e7269186eb973fb225ee6358`.
The proof's frozen JSON serialization has SHA-256
`2dff9844bd36aac4a50c977fe2aa51c3f5b816e1dc05d734eb79aea2024aebfd`.
It has the same recursively canonicalized content as r2, but is not asserted
to be byte-identical to the database serialization.
The exact section binding remains `opening → 1`, `beacon → 2`, `dock → 3`;
the complete routes remain `opening → beacon` and `opening → dock`.

The generic F0 candidate exchange supports the `storyboard` stage and produced
the isolated package/job
`ch_f5storyboardproof20260918` under the disposable project's ignored output
home. `read_delivery` and `assert_current(..., current_stage_revision=0)` passed
against the project's `storyboard` head (`revision 0`, `missing`). This only
proves frozen transport/currentness: the project has no storyboard
candidate/review owner, so it cannot admit a canonical storyboard.

## Candidate and deterministic evidence

The raw frozen inputs and derived outputs are local, ignored proof artifacts:

- [candidate JSON](../../.local/relay/e75c2655-e7ce-4053-ab42-38fa26d0d412/f5-storyboard-proof/storyboard.json) — SHA-256 `d0badc8c4768fcb70a407fef6b069ed01aa2764b65069bc90124dc4f26942f65`
- [pinned Markdown render](../../.local/relay/e75c2655-e7ce-4053-ab42-38fa26d0d412/f5-storyboard-proof/storyboard.md) — SHA-256 `748733a8d76e6ab564bf18f6d3acb8abc2aa83dd82ed6b21e3386b00832c08d2`
- [pinned HTML render](../../.local/relay/e75c2655-e7ce-4053-ab42-38fa26d0d412/f5-storyboard-proof/report.html) — SHA-256 `60b8efcc2b5a94faf568ad7c40fcaacd92115d730dd3a4925584a4c98ffb817a`
- [completion receipt](../../.local/relay/e75c2655-e7ce-4053-ab42-38fa26d0d412/f4-current-proof/outputs/20260918T063228536312Z__d3ad5da3-905e-4eb2-90c8-7d52d1cb4fd0/outputs/creative-handoff/jobs/ch_f5storyboardproof20260918/delivery/completion.json) — SHA-256 `7e2819632e44a42beee3ca1b7d361ef3bc65dc602c2cf0e32174c9ecd3febc7e`

The three sections have respectively 7/19/84s, 7/21/91s, and 7/21/91s
(segments/cuts/seconds). All ordered beat claims, source-owned dialogue blocks,
H3 prompt structure/cut times, identity/scene/prop references, section order,
and both distinct route consequences pass the pinned checks. No candidate cut
contains footage or consequence language from the other ending.

The candidate is intentionally **not valid for production**. The pinned
`novel-storyboard` `dialogue-fit` gate fails for 12 script-owned r2 lines:

- Opening: beats 3 (5.6s), 5 (6.0s), 7 (6.4s), 12 (7.6s), 14 (7.6s),
  17 (5.6s), and 19 (6.9s).
- Beacon ending: beats 5 (6.0s), 7 (5.6s), and 10 (6.9s).
- Dock ending: beats 5 (6.0s) and 7 (6.0s).

At the pinned script estimator of 4.5 characters/second, each exceeds the
upstream hard cut maximum of 5 seconds. Dialogue text, order, and speakers are
script-owned; splitting or rewriting them, enlarging a cut, or masking the
failure would change that contract. The first build had a local beat-range
grouping defect; one targeted correction removed it. This final validation has
only the source-timing failure above, so no further candidate revision was made.

Checks run:

- `novel-storyboard seed` for episodes 1–3;
- pinned `validate` and `checkup` with r2 script, accepted outline and cast —
  16 gates pass; only `dialogue-fit` fails as recorded;
- pinned `render --md` and `render --html` — both produced the linked raw
  reports without a wrapper;
- pinned `selftest` — 254 assertions passed;
- F0 `read_delivery` plus currentness assertion — passed, manifest hash
  `b68b35391fabe7c7e0d21708cae2003d65daef16bd2f0757af5c604c090dc648`.

## Reference and production mapping

| Frozen upstream field | Existing owner / exact gap | F5A boundary |
| --- | --- | --- |
| `segment.id`, `sceneIndex`, ordered `cuts[].beats`, `seconds` | Existing `Storyboard.shots` has shot ID/order/duration and `shot_beat_links`, but F4's flow indexes are not canonical Scene Beat IDs. | Bind each F4 flow beat to the existing canonical beat identity before projecting one ordered canonical shot per cut; preserve upstream segment grouping as review-only metadata. |
| cut size/camera/frame/action/characters/props | Existing `Shot` owns size, movement, visual/motion intent, action, character/location/prop IDs and continuity fields. | Map only after a source-bound candidate/review owner exists; do not make an independent F5 shot store. `S01` and `keeper` are required inputs, not selected media. |
| exact dialogue and per-cut H3 `<d>` blocks | Script owns dialogue; existing `Shot.dialogue`/`audio` and `MediaPromptCompiler.video` own canonical presentation and derived video prompt inputs. | Preserve script dialogue as the source of truth. Upstream `h3Prompt` is review direction, not a dispatch payload. Retire any direct upstream-H3 prompt passthrough rather than add a second media compiler. |
| upstream multi-picture segment alignment and sub-frame needs | No existing Plotloom direct-H3 path accepts multi-picture segment alignment. The H3 transport submits exactly one approved keyframe plus `prompt`, profile, aspect policy, seed and duration. | Represent each required cut keyframe as an existing reviewed-shot/keyframe need; do not claim any scene/identity/prop reference is selected. A segment-to-multiple-input dispatch adapter is a later, separately proven decision. |
| upstream 2–5s cuts / ≤15s segments | The upstream candidate passes 2–5s cut and ≤15s segment gates except dialogue-fit. The current H3 adapter freezes every profile's production contract to 5 seconds, although its catalog public descriptor advertises a 5–15 range. | Resolve the script dialogue timing contract first; then decide whether F5A maps a cut 1:1 to a fixed 5s direct-H3 job or has an explicitly tested split/recomposition rule. No implicit duration conversion. |
| native audio convention in upstream H3 prompt | Current adapter requires `audio=True`, and output validation expects AAC, but no source here establishes deployed speech, speaker attribution, voice consistency, or prompt-control behavior. | Leave these capabilities unknown and reserve their real gateway test for F6; do not decide TTS or voice control in F5A. |

The source basis is `src/plotloom/domain.py` (`Shot`/`Storyboard`),
`src/plotloom/media.py` (the retained video prompt compiler),
`src/plotloom/video_backends/minimax_h3/adapter.py` (allowlisted 5-second
production contract), `transport.py` (one-image payload), and
`src/plotloom/persistence/project/media_video.py` (current approved storyboard,
reviewed selected keyframe, identity/reference and currentness gates).

## Next bounded action and limits

The smallest F5A integration decision is to choose one durable owner for the
script's long dialogue: either revise the accepted script to fit the pinned
2–5s upstream cut contract, or change/pin a different upstream timing contract
with an ADR and a fresh candidate. Only after that decision should a thin
candidate-to-existing-`Storyboard` projection bind F4 flow beats to canonical
beat IDs and reuse the existing review/keyframe/media owners.

No project database was edited. No Approval, reference selection, image/media
generation, gateway preflight/dispatch, audio experiment, frontend/schema work,
or human creative approval occurred. This receipt is technical evidence only.

## Independent review

An attended independent read-only reviewer inspected the actual r2 script,
candidate, report, F0 package, both branches, and the source mapping. It
confirmed that the candidate and report hashes match the delivery bytes; all 22
source dialogue lines appear verbatim and in order in H3 `<d>` blocks; ordered
coverage and the `opening → beacon` / `opening → dock` consequences do not mix.
The reviewer independently reran pinned `validate` and `checkup`: exactly the
same 12 `dialogue-fit` failures remain, with a 5.6–7.6 second range. It found
no blocker to this docs-only receipt, and no basis to claim a selected reference,
usable text endpoint, speaker/voice control, or deployed H3 prompt behavior.

The review also confirms the integration boundary: current Plotloom can submit
only one reviewed selected keyframe through its fixed 5-second direct H3 job;
upstream multi-picture segment alignment remains noncanonical review material
until an explicit, tested integration decision. This review is technical only;
it grants no creative approval or production admission.
