# F6 deployed H3 audiovisual qualification readiness

Date: 2026-09-18. Baseline: `ec4822a87919f40d943c2888a0c49a32ab96f80a`.

## Scope and result

This is a read-only readiness receipt for the next bounded F6 qualification. It
does not create a project, reservation, media job, upload, generation, poll,
selection, deployment/configuration change, or source/runtime/profile change.
It also does not revisit F5A delivery or treat its technical review as human
creative approval. The in-app headed production UI remains valid technical F5A
evidence; native Chrome is not a prerequisite invented for that review.

The owner-configured private gateway was safely inspected through its
credential-free root only. The local production configuration is enabled for
the trusted `minimax_h3_gateway` catalog and has a separate model-key value;
the configured root is an HTTP root without userinfo, query, or fragment. No
credential or endpoint value is recorded here. `GET /health` and
`GET /openapi.json` returned HTTP 200. Health reported `status: ok`, profile
contract version 4, exactly the six source allowlisted profiles, `inputModes`
`["image", "text"]`, zero queued/active jobs, and `dispatchConcurrency: 1`.
The schema contains the image and text creation routes plus read-job/output
routes. No protected job endpoint was called.

This is a point-in-time, unauthenticated public readiness observation, not the
transport's authenticated preflight. Immediately before the bounded future
generation, normal Plotloom preflight must recheck the configured key, local
media probes, and the exact health catalog. Today's idle result must not be
used to reserve capacity or assume it remains idle.

This establishes deployed-interface readiness, not generated-output proof. The
previous gateway-only V4 canary separately proved one 8-second I2V output
(192 frames, 8.000 seconds, H.264/AAC) at
[the unified-canary receipt](2026-09-15-h3-unified-contract-live-canaries.md).
The older one-line Mandarin probe proves only its exact five-second result;
neither receipt proves this F6 speaker, prompt, voice consistency, or human
audio acceptance.

## Contract mapping and blocker

| Layer | Evidence | Current consequence |
| --- | --- | --- |
| Gateway | `services/minimax_h3_gateway/src/plotloom_h3_gateway/contracts.py` accepts whole `durationSeconds` 5--15; `profile_catalog.py` snaps duration to the 24-fps `17k + 5` grid. Eight seconds is exactly 192 frames. `gateway.py` freezes that requested duration/frame count before dispatch. | The deployed H3 service can represent a five-to-fifteen-second 8-second I2V request, subject to normal future admission. |
| Plotloom production adapter | `src/plotloom/video_backends/minimax_h3/adapter.py` has per-profile `duration_seconds = 5`, and both `production_contract()` and `compile_image()` reject any other duration. Output validation also requires the profile's fixed 124-frame, about-5.167-second result. | **Current production Plotloom is fixed5.** It cannot dispatch the proposed 8-second clip, even though the gateway can accept it. No bypass or client-side pad/trim is permitted. |
| F5A review evidence | The fresh accepted storyboard freezes review-only 2--8 second cuts and at-most-15-second segments, but explicitly creates no selected reference, media request, or dispatch. See [F5A receipt](2026-09-18-f5a-fresh-specialist-production-review-receipt.md) and its frozen `storyboard.json`. | A multi-cut, up-to-15-second upstream segment is not one H3 clip. F6 must not send it as a fixed5 request, split it implicitly, or claim an 8-second experiment realizes that segment. |

The root cause of the proposed 8-second qualification block is therefore an
intentional current adapter/output contract mismatch with a broader deployed
gateway capability. It belongs in the production adapter contract, not in
prompt wording, a gateway change, a queue workaround, or an automatic
post-processing path.

## Smallest next assignment, in order

1. Change and test only the current Plotloom H3 production contract so an
   explicitly requested 8-second I2V job freezes its selected profile,
   requested duration, 192 expected frames, 24 fps, geometry, native-audio
   requirement, aspect policy, seed, and output-duration validation in the
   job snapshot. Bind those duration/frame expectations in submit and poll
   response validation as well as physical `ObservedVideo` validation; the
   current transport only establishes a plausible 5--15-second envelope.
   Keep five seconds as the profile default; reject other durations until they
   are deliberately qualified. This needs the corresponding concise
   contract/ownership decision record before implementation, because it changes
   a persisted runtime contract. That record must settle that public-profile
   `durationSeconds`/`frameCount` are defaults, while duration/frame count are
   immutable per-job values, and align the snapshot, adapter, gateway response
   validator, UI/public-capability projection, and tests.
2. Verify that focused adapter/transport/job tests reject a mismatched duration,
   frame count, geometry, codec, or output duration before any live call. Then
   run one isolated, manually attended 8-second I2V clip through the normal
   production adapter/accounting path. It is not a text-to-video probe and has
   no alternate provider, retry, fallback queue, or TTS/lip-sync system.
3. Run the second clip only if the first passes the objective checks and an
   attending human hears the intended line. It uses the same reference and
   profile to compare speaker/voice continuity. Stop at two clips; failures
   produce an honest F6 result and no third attempt.

The future request must preserve the 8-second item as its own frozen media
unit. It may borrow a single line or ambience direction for a test prompt, but
it does not turn a 2--8 second F5 cut or a multi-cut 15-second F5 segment into
one video, nor silently pad, truncate, stitch, or trim any output. Mapping F5
review direction to future production media remains an F7 design choice.

## Bounded test input and acceptance

No F5 reference is selected: F5A deliberately has none. The proposed input
for this experiment is instead explicitly **test-only**: the F2B disposable
cast study's selected refinement r2 for `C01` / Lin Che. Its durable
provenance is recorded in [the F2B receipt](2026-09-18-f2b-cast-identity-proof.md):
ImageGen task `exec-db9ba9a2-5586-4d50-9393-3264809e2cf6`, SHA-256
`1fb4700c73834b81c2ea3f64d6754cc0b24ba1bfcb472d8993161d2d7a2f2e0d`.
The currently retained staging byte was hash-checked during this readiness
work. F2B itself establishes no production Shot, Approval, selected keyframe,
or cross-shot claim, so its raw bytes must never be posted directly to H3.
The later bounded assignment must first create an isolated, explicitly
test-only F6 admission fixture through the ordinary production keyframe,
identity-lineage, snapshot, and accounting owners. That fixture must leave F5
and canon untouched and leave both generated clips unselected; it is not an
F5-selected, canonical, or production-approved asset.

The first future clip is a visible, single-speaker Lin Che close/medium view:
one short Mandarin line (`我在这里。`), quiet room tone, no narration and no
music, for an 8-second native-audio I2V request using the explicit test-only
reference and a frozen reviewed profile/aspect policy. The conditional second
clip uses the same speaker/reference/profile with a different short Mandarin
line (`我会等你。`) and the same room-tone constraint. These are qualification
prompts, not F5 scene installation or a claim that F5 dialogue has been
produced.

Objective admission/output checks are separate from sensory acceptance:

- Objective: one normal job snapshot per clip; 8 requested seconds; 192
  frames at 24 fps; frozen selected-profile geometry; H.264 video plus AAC
  audio; and no unexpected crop/pad/output-duration deviation.
- Attended human audiovisual review: the intended words are heard with no
  omissions; the voice is attributable to the intended speaker; visible mouth
  movement is consistent with the words; native ambient audio is present; and,
  after both clips, the same speaker's voice is materially consistent.

Codec metadata, decoded samples, a non-silent audio measurement, duration, or
timeline movement may establish only the first category. They cannot establish
what was heard, speaker identity, lip consistency, ambience suitability, or
voice continuity. A failed or unavailable attended review means native audio is
not yet sufficient; it does not authorize a new TTS/post-production stack.

## Stop condition and open decisions

The next assignment stops after its adapter contract evidence and at most two
unselected, isolated clips with the observations above. It must leave normal
accounting/provenance intact and make no F5/F7 selection, no historical-job
poll/replay, no retained-data rewrite, and no media compiler or SceneBeats
reconstruction. It must not claim a final F6 result until a human reviewer
actually hears and views both qualifying outputs.

Material open choices remain: whether a passed native H3 result is sufficient
for production dialogue versus separate audio later; whether later F7 mapping
uses one reference or a controlled adjacent-reference pair; and which reviewed
F5 direction, if any, receives a production reference/clip binding. None is
decided by this receipt.

## Independent review

An independent Terra/high read-only review inspected this mapping against the
current gateway, adapter, transport, and F2B/F5 boundaries. It confirmed the
fixed5 contract mismatch and the need for request-derived 8-second duration,
192-frame, and delivered-duration checks in both response and observed-output
validation. It also identified the F2B admission guard recorded above: a
disposable test fixture must use normal production keyframe/snapshot provenance
rather than raw gateway submission. No contrary finding or scope expansion was
identified.

## Read-only verification

- Inspected the current adapter, transport, gateway profile/schema/dispatch
  owners and F5A/F2B receipts.
- Queried the configured gateway's `/health` and `/openapi.json` only; no
  credential, endpoint, job, prompt, output, or response body was retained.
- Recomputed the retained F2B r2 file SHA-256 against its recorded provenance.
- Ran documentation-link/reference and working-tree diff checks after the
  tracker update; no runtime suite applies to this documentation-only slice.
