# F5 storyboard production-seam receipt — bounded timing evidence, failed correction, and content-preserving grouping split

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

The historical candidate's three sections are respectively 7/19/84s,
7/21/91s, and 7/21/91s (segments/cuts/seconds). Its opening is within the
90-second section cap, but each ending is one second over it. That omission was
not an upstream `novel-storyboard` gate and the prior receipt incorrectly left
the historical candidate sounding section-cap compliant. Both complete routes
remain within 180 seconds (175 seconds), but a route cap does not waive an
individual section cap. Ordered beat claims, source-owned dialogue blocks, H3
prompt structure/cut times, identity/scene/prop references, section order, and
both distinct route consequences pass the recorded pinned checks. No candidate
cut contains footage or consequence language from the other ending.

The candidate is intentionally **not valid for production**. The pinned
`novel-storyboard` `dialogue-fit` gate fails for 12 script-owned r2 lines:

- Opening: beats 3 (5.6s), 5 (6.0s), 7 (6.4s), 12 (7.6s), 14 (7.6s),
  17 (5.6s), and 19 (6.9s).
- Beacon ending: beats 5 (6.0s), 7 (5.6s), and 10 (6.9s).
- Dock ending: beats 5 (6.0s) and 7 (6.0s).

At the pinned script estimator of 4.5 characters/second, each exceeds that
historical candidate's declared 5-second cut maximum. Five seconds is the
upstream default, not a hard pinned limit: `paramsOf` merges the candidate's
`params.maxCutSeconds` over that default, so an explicit value of 8 is accepted
unchanged by the validator. Dialogue text, order, and speakers remain
script-owned; this correction work did not rewrite or split them.

Checks run:

- `novel-storyboard seed` for episodes 1–3;
- pinned `validate` and `checkup` with r2 script, accepted outline and cast —
  16 gates pass; only `dialogue-fit` fails as recorded;
- pinned `render --md` and `render --html` — both produced the linked raw
  reports without a wrapper;
- pinned `selftest` — 254 assertions passed;
- F0 `read_delivery` plus currentness assertion — passed, manifest hash
  `b68b35391fabe7c7e0d21708cae2003d65daef16bd2f0757af5c604c090dc648`.

## 8-second timing correction — failed, preserved

One fresh review-only candidate and its one targeted correction are retained in
the ignored scratch directory
`.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/`.
They consume an exact byte copy of F4 script r2: byte SHA-256
`2dff9844bd36aac4a50c977fe2aa51c3f5b816e1dc05d734eb79aea2024aebfd` and
canonical content SHA-256
`ca7dc718a5164656c1da2bf7e88a6a8c7f8e8922e7269186eb973fb225ee6358`.
The historical F5 package was independently re-read and its
`assert_current(..., current_stage_revision=0)` check passed; this new raw
candidate is only review material and is not a new F0 exchange delivery.

The first fresh JSON candidate is preserved as `storyboard-first-invalid.json`.
It serialized singleton beat claims as `[n]`, rather than the required `[n,n]`,
so the pinned validator rejected coverage and derived durations. The sole
targeted correction normalized those claims and regenerated the raw candidate,
Markdown, and HTML reports. Its raw artifacts are:

- [corrected candidate JSON](../../.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/storyboard.json) — SHA-256 `88b2babc94f2edadc0b1582197c243e46cfd40fe388117686081ed39c1c07dc8`
- [corrected Markdown render](../../.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/storyboard.md) — SHA-256 `d27a627744273248e63776dac19f4a0c92171abd19023ec21fb639d8ba042f8b`
- [corrected HTML render](../../.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/report.html) — SHA-256 `dd95eb6742ac64f92c66888f2623983453cc345f3530127dc16cc10f30e2a48e`
- [pinned validation log](../../.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/validate-correction.log), [checkup log](../../.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/checkup-correction.log), and [explicit cap check](../../.local/relay/6529f443-12be-441f-b046-c3444e76cf1a/f5-eight-second-review/explicit-caps.json)

The correction proves the relevant upstream timing fact: its explicit
`params.maxCutSeconds: 8` passes the cut-length and dialogue-fit gates; its
opening has an actual 8-second cut. It preserves every one of the 22 script
dialogue lines verbatim in speaker/order sequence and retains episode bindings
1/2/3 for `opening`/`beacon`/`dock`. It also meets the strict section caps at
80.3/78.5/78.9 seconds and the complete-route caps at 158.8/159.2 seconds.

It is nevertheless invalid: `E02-06` is 17.5 seconds, exceeding the pinned
15-second segment maximum. `validate` and `checkup` therefore fail exactly one
gate. This follows the targeted correction, so the attempt stops here rather
than applying another resegmentation. The pinned upstream selftest still passes
254 assertions. This is technical failure evidence only, not a valid candidate,
creative review, production admission, or proof that variable-duration H3 can
be deployed. Current production H3 remains fixed to five seconds; any
variable-duration production support needs a separate qualification.

## Reference and production mapping

| Frozen upstream field | Existing owner / exact gap | F5A boundary |
| --- | --- | --- |
| `segment.id`, `sceneIndex`, ordered `cuts[].beats`, `seconds` | Existing `Storyboard.shots` has shot ID/order/duration and `shot_beat_links`; F4 flow indexes are upstream review coordinates. | A later product owner may define traceable source-to-shot mapping. This F5 evidence neither creates nor requires a V2 SceneBeats projection; upstream segment grouping remains review-only metadata. |
| cut size/camera/frame/action/characters/props | Existing `Shot` owns size, movement, visual/motion intent, action, character/location/prop IDs and continuity fields. | Map only after a source-bound candidate/review owner exists; do not make an independent F5 shot store. `S01` and `keeper` are required inputs, not selected media. |
| exact dialogue and per-cut H3 `<d>` blocks | Script owns dialogue; existing `Shot.dialogue`/`audio` and `MediaPromptCompiler.video` own canonical presentation and derived video prompt inputs. | Preserve script dialogue as the source of truth. Upstream `h3Prompt` is review direction, not a dispatch payload. Retire any direct upstream-H3 prompt passthrough rather than add a second media compiler. |
| upstream multi-picture segment alignment and sub-frame needs | No existing Plotloom direct-H3 path accepts multi-picture segment alignment. The H3 transport submits exactly one approved keyframe plus `prompt`, profile, aspect policy, seed and duration. | Represent each required cut keyframe as an existing reviewed-shot/keyframe need; do not claim any scene/identity/prop reference is selected. A segment-to-multiple-input dispatch adapter is a later, separately proven decision. |
| upstream candidate cut/segment limits | The historical candidate declared 2–5s cuts and passed the ≤15s segment gate except dialogue-fit. `paramsOf` allows an explicit candidate cut maximum, as the failed correction's 8-second cut proves; the correction still fails its 17.5-second segment. The current H3 adapter freezes every profile's production contract to 5 seconds, although its catalog public descriptor advertises a 5–15 range. | First produce a fully valid review candidate under one explicit timing contract; only then decide whether a later F5A maps a cut 1:1 to a fixed 5s direct-H3 job or has an explicitly tested split/recomposition rule. No implicit duration conversion. |
| native audio convention in upstream H3 prompt | Current adapter requires `audio=True`, and output validation expects AAC, but no source here establishes deployed speech, speaker attribution, voice consistency, or prompt-control behavior. | Leave these capabilities unknown and reserve their real gateway test for F6; do not decide TTS or voice control in F5A. |

The source basis is `src/plotloom/domain.py` (`Shot`/`Storyboard`),
`src/plotloom/media.py` (the retained video prompt compiler),
`src/plotloom/video_backends/minimax_h3/adapter.py` (allowlisted 5-second
production contract), `transport.py` (one-image payload), and
`src/plotloom/persistence/project/media_video.py` (current approved storyboard,
reviewed selected keyframe, identity/reference and currentness gates).

## Content-preserving segment split — valid review-only candidate

The retained timing correction established that `params.maxCutSeconds: 8` is
accepted unchanged and that all section and route caps can be met, but it left
one deterministic grouping defect: `E02-06` grouped otherwise valid cut
durations `[5, 2.5, 2.5, 2.5, 2.5, 2.5]` into 17.5 seconds. This was not a
script, dialogue-feasibility, cut-duration, or production-H3 issue.

One new derived candidate was made in ignored local scratch, without touching
either frozen earlier attempt, an F0 package, a database, or production source:

- [baseline correction](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/storyboard.json) — SHA-256 `88b2babc94f2edadc0b1582197c243e46cfd40fe388117686081ed39c1c07dc8`
- [derived split candidate](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/storyboard-split.json) — SHA-256 `50165863d45e678c28bcf794c6f9f5444b6aa45eef2caa446595dd638313578a`
- [content-preservation proof](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/content-preservation.json), [explicit cap proof](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/explicit-caps.json), and [raw hashes](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/hashes.log)
- [pinned validation](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/validate.log), [full-input checkup](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/checkup-full-inputs.log), [Markdown render](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/storyboard-split.md), and [HTML render](../../.local/relay/c82e778f-abcb-4649-815d-d1a9b7801ea7/f5-segment-split/report-split.html)

Only the former `E02-06` was split at its existing third-cut boundary. The
first retained `E02-06` is 10.0 seconds (`[5, 2.5, 2.5]`) and the new
`E02-07` is 7.5 seconds (`[2.5, 2.5, 2.5]`). The two affected H3 prompts were
derived again so their local Shot/Picture numbering and timestamps restart at
each new segment: 0/5/7.5 seconds and 0/2.5/5 seconds respectively. No cut
object was rewritten.

The proof flattens every cut object across all three episodes and finds the 71
objects byte-equivalent in order. It also independently compares the 22
script-owned dialogue bindings and H3 `<d>[Chinese]` blocks: source, baseline,
and final each contain the same 22 lines in the same order. The pinned
`validate` and full-input `checkup` pass all applicable gates; pinned selftest
still passes 254 assertions. The derived candidate has 21 segments and 71 cuts
over 237.7 seconds. Explicit non-upstream acceptance caps also pass: sections
are 80.3/78.5/78.9 seconds (each ≤90), maximum segments are 14.3/14.1/14.5
seconds (each ≤15), and routes are 158.8/159.2 seconds (each ≤180).

The optional recipe-card gate remains explicitly skipped because no
`--shots` card library was mounted; this is not recipe-card compatibility
evidence.

### Historical currentness boundary

The original package's preserved currentness record still says
`historical-f5-package-currentness passed` with manifest hash
`b68b35391fabe7c7e0d21708cae2003d65daef16bd2f0757af5c604c090dc648`;
the original source and package hashes are re-recorded in the new raw hash log.
A read-only current-reader recheck is also preserved, but exits before delivery
reading or `assert_current`: today's `CreativeHandoffRequest` rejects six
legacy request fields. It therefore neither refutes nor freshly confirms that
historical currentness record. This is a historical request-schema
incompatibility, not a candidate-content, validation-gate, or timing failure;
the prior package was not rewritten to accommodate it.

### Independent review

An independent attended read-only review compared the frozen script, baseline,
derived candidate, preservation and cap proofs, raw validation/render outputs,
and the current-reader failure. It independently confirmed the sole substantive
change is the 10.0/7.5-second split; the 71 flattened cuts, 22 dialogue
bindings, and all local H3 timestamps reconcile. It agrees that the candidate
is valid review-only resegmentation evidence and that the reader failure is a
historical-schema evidence gap, not a new candidate failure.

The native reviewer task was launched with the recorded selection
`gpt-5.6-terra` at `high` reasoning. No separately inspectable runtime-model
telemetry was returned, so this receipt does not promote that launch selection
into an execution attestation or rely on model self-description.

This review does not establish production support for variable-duration H3;
the deployed H3 contract remains fixed at five seconds. It also does not create
a canonical projection or installation, a selected reference, media dispatch,
voice proof, creative approval, or F5 product acceptance.

## Next bounded action and limits

The next bounded action is director acceptance of this review-only candidate or
selection of a source-bound candidate/review-install owner. Product integration
remains separately scoped. No V2 SceneBeats projection is a prerequisite of
this review work; existing review/keyframe/media owners remain unchanged.

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

### Independent correction review

An independent attended read-only Codex reviewer inspected the preserved fresh
candidate, reports, validation/checkup logs, cap calculation, and source/currentness
log. The reviewer reported its runtime as GPT-5 rather than the requested Terra
label; that attribution mismatch is retained as a verification gap, not relabelled.
It independently found the F4 r2 byte/canonical hashes correct, all 22 dialogue
lines verbatim and in speaker/order sequence, the episode bindings 1/2/3 aligned
to `opening`/`beacon`/`dock`, and two actual 8-second opening cuts accepted by
the configured 2–8 second gate. It confirmed the sole corrected-candidate
failure: `E02-06` at 17.5 seconds over the 15-second segment cap. The reviewer
also confirmed section caps 80.3/78.5/78.9 seconds and route caps 158.8/159.2
seconds, and found no basis to upgrade this technical failure evidence into
creative approval, production admission, deployed H3 timing support, reference
selection, media dispatch, or voice/speaker-control proof.
