# Native playback after reboot — 2026-10-08

Status: **FINITE ORIGINAL / SEGMENT / SELECTION PASS; FULL E2E PARTIAL**.
The owner reported a computer crash and reboot. These are fresh post-reboot
observations, not a diagnosis or repair of that crash, the earlier VideoToolbox
failure or the separate intermittent offline media-clock stalls. This continues
the [approved run](../roadmap/2026-10-07-full-creator-e2e-repeat.md) and
[ledger](2026-10-07-full-creator-e2e-repeat.md), using executable `3ad91e4`.
No source repair was needed for this finite native-media slice.

## Exact objects and safe recovery

- Disposable project: `b3a933f7-b6fc-40e3-826f-5162f95a119a`.
- Existing terminal job: `vj_c121f94f27dc4704ac27dbc3cbdd2b8d`.
- Opening shot: `node-b64d6809-7161-5042-a7f8-a3c5c854e733-s1-c1`.
- Original:184,434 bytes, SHA256
  `3d5baba0069c255123894246362c10c4e133d02ce4b030767441bcc6972ac9f3`.
- Native H.264/AAC,832×480,24fps,124 encoded frames,5.167 seconds.

Read-only recovery checked existing completion/dispatch identities and17 declared
delivery-file hashes. Eleven retained dispatch receipts are completed; the ingested
job is current. Dispatch authority was not cleared, replayed or resubmitted.
These checks do not themselves establish every stage's currentness. The known idle
owned8861/8862 runtime was restarted with matching Python/static and the existing
H3 catalogv7 process-only setting. Credentials, protected settings and frozen input
were unchanged. Startup creates local runtime infrastructure, but does not
automatically dispatch or reconcile jobs. Fresh specialist reads report idle and
zero active tasks.

## Controlled exact-byte comparison

Checkpoint193 served the exact original and older successful R1 control through a
temporary read-only FileResponse server. Both played once in headed installed
Chrome154.0.8037.97 using **VideoToolboxVideoDecoder**, platform decoder=true and
FFmpegAudioDecoder. Trusted `playing`/`ended` reached5.167 seconds; browser counters
report124 frames, zero drops and no media error. Both were unmuted at volume1;
this is not audible or creative-quality review. Elapsed native/control times were
5328/5358ms. CDP reported Metal/Apple M5 Pro, video decoding enabled and zero
GPU-process crashes in this experiment.

The control is850,015 bytes, SHA256
`9df1ef084e94025a11ca98ec24fa7bb0dffaa514c4e2ceb6477eec685e0b86fd`.
`193-native-decoder-comparison-summary.json` is explicitly a summary of executed
CLI/CDP results, not a complete raw event stream. Root inspected actual terminal
pixels. No automation/decoder flags or software transcoding were introduced.
The owned diagnostic server/browser were closed. This establishes decodability
now, not the cause of the earlier failure.

## Actual Plotloom original, segment and selection

Checkpoint194 used the actual opening-shot review on isolated8861. Trusted Space
input played **原片预览** to trusted `ended` at5.167 seconds, with VideoToolbox,
zero drops and no media error. HTTP200 returned the exact184,434 original bytes/hash.
Writes were zero and the job readback stayed exact. Root inspected
`194-product-original-terminal.png`; the full returned CDP proof is retained in
`194-product-original-diagnostic.json`.

Actual UI preparation made one POST with `inFrame:0`, `outFrame:120` and
`expectedSelectionRevision:0`, returning201. Segment
`d5c45979-286b-4e62-8a3d-1b28369c49e3` is167,550 bytes, SHA256
`6d50e0291c4544646b85d8a2e7fe5e4bee8088133190abf08022ee15e7b6a5f2`.
Its derivative probe reports120 encoded frames at24fps, zero start offset,
five-second video/audio and160,000 decoded audio samples at32kHz. Preparation
does not select it: selection revision remains0. Original hash and the complete
frozen snapshot stay exact. `194-product-segment-prepare.json` retains the ACK,
source/derivative probes and independent readback.

Actual segment preview reaches trusted `ended` at5 seconds with VideoToolbox,
zero drops and no media error. HTTP200 bytes/hash match the derivative. Preview
performs zero writes and preserves the job. Browser `totalVideoFrames` reports124,
while the derivative probe reports120 encoded frames: separate observed measures,
not an asserted equality or a diagnosed discrepancy. The retained diagnostic also
records the unselected playback guard's404, **video job has no reviewed playback
segment**, without an independently timestamped guard probe.

Explicit **确认用于故事** makes the second and final observed write: selection POST
returns201, selected=true and selection revision1. The review says **Codex QA
(technical only)** and **全程流程验证：只确认片段读取、时长与选用链路，不代表创作质量认可。**
Original hash and frozen snapshot remain unchanged.
`194-product-segment-diagnostic.json` retains the request/ACK, native preview and
final state. Root inspected terminal and selected-state pixels.

A fresh read-only Play checkpoint at16:23:58 UTC returns the selected playback
endpoint as HTTP200/167,550 bytes with the exact derivative hash. Job readback
remains identical, writes=[], and specialist active-task count=0. Story Play
correctly refuses full playback because East and West route shots lack current
selected segments; its two exact-ID review links remain distinct. Root directly
inspected `194-product-play-missing-{1280x768,1280x460,1700x900}.png`: readable
guidance/links, no document-width overflow, no video and zero writes. The short
viewport has an ordinary lower card fold, not hidden links. An unavailable Node
`require` in the first capture script failed after read-only captures;
browser-native hashing completed the diagnostic without a product patch.

All193/194 artifacts remain under `output/playwright/full-lifecycle-2026-10-07/`.
Screenshots alone are not handler or media-quality qualification.

## Independent review and limits

An independent read-only reviewer, requested GPT-6 Luna/Max, reviewed the records,
source and pixels, finding the finite technical claims supported. Effective settings
remain unverified. Relay registration
was denied by filesystem permissions; the native final was collected without
retrying or bypassing the denial. The static **待审片段** label is a minor wording
refinement: selected option and adjacent **已选择片段 · 正用于故事** are accurate.
A neutral **片段** label remains an optional next copy refinement, not a blocking
state error.

All-route playback, native multishot progression, revised media, video-bearing
lifecycle/recovery and supported same-project post-install revision/rebuild remain
open. The earlier decoder failure's cause and computer crash remain unknown.
No all-browser/creative/audio acceptance follows from this one native slice.
Normal8841 remains healthy; both owners and three protected settings retain aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
The qualified890 executable inputs remain unchanged at
`337b81606d8ea3609821dbe0ccae208c1f828da880c24b3009e767da637f5aa0`.
The owned native QA browser is closed; idle8861/8862 is retained for continuation.
