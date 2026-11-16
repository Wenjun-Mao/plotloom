# Native ordered Ref2VA images through the public gateway

## Current status

Updated November 7, 2026. Implementation and qualification owner is the H3
specialist, chat 01a0983e-0e5f-7171-950e-011adaf53303. Manager and final
closeout owner is chat 01a1902a-80b6-7d80-a166-9c980850982f. Authoritative
checkout is local Plotloom main with existing owner storyboard changes.
The typed route, frozen snapshot, native graph and lifecycle implementation
are complete. Independent Sol/High source review is closed after fixing the
dashboard subtype projection. Focused checks (61 tests), isolated gateway and
dashboard wheel installs, 14 dashboard UI checks, retained-AV functional QA and
the pinned native CPU ordering/layout proof pass. The final full local gate
passed: 5173 Python, 1738 frontend and 366 browser cases, types, deterministic
assets and installed root wheel. Manager-admitted activation and exact installed
readback passed, including protected data and real private HTTPS playback,
seek and original download hashes. The single admitted E01-01 production job
succeeded; its accepted/terminal native graphs, full snapshot and all five
source/prepared hashes match the frozen package. Original native AV downloaded
and decoded, and real HTTPS playback/seek/download passed. The generic gateway
technical handoff is complete. The manager owns actual picture/native-audio
creative review and any further production. The matched-B experiment remains paused.

## Acceptance

**Documentation follow-up · 2026-11-16:** Complete. The
[dedicated colleague guide](../operations/minimax-h3-reference-images-client-guide.md)
now provides full Bruno/curl upload and URL examples, timeline/readback and
route-specific limits. Existing entry points and operator/dashboard/timing docs
were aligned. Actual parser, shell syntax, local-link checks and read-only Spark
health passed; the independent Terra/high finding was resolved. See the
[documentation verification](../verification/2026-11-16-h3-reference-images-docs.md).
This follow-up changed no runtime or creation behavior and dispatched no job.

| Claim | Required evidence | Fresh media | Status |
| --- | --- | --- | --- |
| Ordered timed images reach the native encoder and guides | Authenticated public request, durable restart, exact full Comfy envelope, original prompt and image bindings | No | Passed: authenticated API/restart and complete envelope, retained AV download; pinned real native CPU methods with inert leaves |
| The ordinary lifecycle remains safe | Input refusals, partial rollback, FIFO, cancellation, UNKNOWN, tamper and retention checks, existing-route regressions | No | Passed focused contracts including existing dashboard/voice/schema regressions; final full gate passed |
| Five references work with the installed learned runtime | Exact manager-admitted E01-01 request through public API to terminal download and native graph/readback | One actual story job replacing the generic fixture | Passed one actual five-image/277-frame run: native success, exact graph, authenticated original download and full AV decode; no repeated-run or nine-image capacity claim |
| The package can be activated | Stable independent review, applicable full local gate, exact package and installed source readback, protected-state preservation | No | Passed: independent review, full local gate, Mac wheel, exact ARM64 smokes and serving readback; protected data and private HTTPS playback/download retained |
| Shuohao source fidelity | Exact UTF-8 source prompt and five requested times preserved in final request | No | Passed against actual accepted native graph, persisted snapshot and source/prepared files; no creative acceptance implied |

## API and ownership

Add authenticated POST `/v1/video-jobs/from-reference-images`. Callers own the
original prompt, ordered images, requested times, duration, seed, resolution
and aspect policy. Trusted gateway code validates those values, freezes all
input identities, derives native frame indices and constructs the graph.
The route accepts 1–9 single stills, one guide per image, with no reference
audio, free-form graph, quality selector or model override.

JSON carries `prompt`, `resolution`, `aspectPolicy`, `durationMs`, optional
`seed`, and ordered `references` entries containing `sourceUrl` and integer
`atMs`. Multipart carries one `request` JSON field with the same typed fields
and ordered reference metadata without URLs, plus repeated `images` parts in
the corresponding order. Reject mixed URL/upload entries, duplicate JSON keys,
unknown fields and duplicate scalar parts. Bound total upload bytes to 20 MiB and each input
to the existing image decoding limits.

Use the existing Ref2VA canvases 960x544 and 576x1024, and requested duration
5000–15000 integer milliseconds. Preserve requested millisecond values. First reference is
at zero, subsequent times are strictly increasing and precede the requested
end. Resolve to the nearest 24 Hz video frame with positive half ties upward.
Reject collisions after quantization. Each guide is exactly one still, so
interval overlap and negative/end-relative interpretation are absent from
this contract. Ceil requested frame count onto the native 17k+5 grid.
The Shuohao example requests 11.3 seconds, produces 277 frames, and maps
0, 2.5, 4.5, 6.8, 9 seconds to frames 0, 60, 108, 163, 216. Return both requested
and resolved times and the actual 277/24-second output clock.

## Storage and native binding

Use the existing Ref2VA model family and immutable versioned
`inputMode=reference_images` snapshot. Keep the parent jobs contract intact.
Extend the exact known frame-binding child schema with `reference_1` through
`reference_9`, using its lossless known-shape migration and existing asset
retention. Freeze original and prepared hashes, ordered filenames, requested
times, guide indices, prompt SHA, seed, canvas, clock, renderer and VAE policy.
The snapshot enters the existing lane commitment. Dispatch cross-checks all
job columns, binding rows and actual files before its one native submit.

The pinned Comfy node uses ordered `ref_images.ref_image_0` onward for
`<Picture 1>` onward. Every image also enters its matching AddGuide node.
Chain AddGuide conditioning into BasicGuider and keep the original AV latent
from ReferenceToVideo. AddGuide returns conditioning only. Prompt bytes pass
directly to ReferenceToVideo without translation or rewriting.

Ref2VA uses `minimax_h3_ref2va_pruned_int8_convrot.safetensors`, expected SHA
`9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779`, Base-20
RES/simple and the adopted VAE policy. Existing readiness checks establish
node/filename availability, which is distinct from a fresh full weight hash
and learned capacity. Verify those separately before the live smoke. The
image-only route has independent readiness from the voice-reference route.

## Small journey, resources and qualification

First exercise one public five-image request with retained PNGs through a real
local API, SQLite, restart, fake Comfy transport, retained MP4 transfer and
download. Compare the entire submitted graph and exact UTF-8 prompt bytes.
Offline tests refuse unexpected real submission. Test 1/5/9 images and all
timing, count, multipart, geometry, rollback and tamper refusals. Existing
FL2VA, voice, Qwen and shared-lane tests supply regression evidence.

Five reference images are encoded for the text encoder and native reference
blocks, and again for five timed guide states. This adds conditioning tokens,
image encodes and memory relative to the current single-image voice route.
The admitted five-image/277-frame case completed in 1213.457 seconds from
submission to gateway completion observation. One measured execution does not
qualify repeated-run performance or the nine-image capacity envelope. Keep
`ref_image_size` at `match` and retain the shared single-inference FIFO.

The initially proposed generic retained-image learned smoke is superseded,
unperformed. The owner's later explicit overnight real-story authority permits
ONE exact E01-01 production job to supply the same five-reference, 277-frame
integration evidence and the separate creative review input. It uses the final
manager-frozen five cash-corrected frames, original byte-exact Shuohao prompt,
960x544, 11300 requested milliseconds, times 0/2500/4500/6800/9000 and the
manager-issued seed and dispatch identity. Do not treat current frame paths as
admitted while they are under revision. No separate generic POST is necessary.

This substitution changes the prospective fixture, not the gateway contract.
It answers whether installed model, encoder and chained conditioning execute
together and return valid native AV. Preserve the first outcome and stop after
terminal readback or a known failure. UNKNOWN requires exact reconciliation
without replay. Technical AV integration and source fidelity do not establish
creative quality; the manager owns the production plan and creative judgment.
Any further story submission needs its final exact package and fresh manager
admission; the first job's one-POST grant cannot be replayed or expanded.

Root coordinates with the manager before every shared service mutation or
live job. The manager confirms resource quiescence and ownership, and owns
final closeout. Preserve existing jobs, holds, database identity, voices and
unrelated files. Use normal source-only package activation and exact installed
readback. Run focused checks during implementation and the required final
local full gate on the stable candidate. CI and push remain off.

## Primary native sources

- [Pinned Comfy node](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/comfy_extras/nodes_minimax_h3.py)
- [Comfy multiframe workflow](https://docs.comfy.org/tutorials/video/minimax/minimax-h3-multiframe)
- [MiniMax model specifications](https://github.com/MiniMax-AI/MiniMax-H3#model-variants-and-input-specifications)

## Qualification evidence

Root owns all execution; independent reviewers reused the stable diff and did
not duplicate suites. Evidence is `.local/ref2va/`, with separate frozen
qualification, activation and terminal technical receipts. The functional journey used five distinct retained
QA images, the byte-exact Shuohao source prompt and real SQLite/API/restart,
then one captured fake Comfy submission and a derived retained AV file. The
original story JSON SHA-256 is
`e52fec3505f90b5e8be564654cac3c0a4978d242f5a5079b01be2b93ad27ddee`;
the prompt SHA-256 is
`294da25badb73f39f1c3a0a83a8fbf19be921ea9edd450f7a5e3ae54fec17fab`.
The download decoded as H.264/AAC, 960×544, 277 frames/24 fps, 32 kHz audio.
It is a scaled/trimmed retained MP4, not newly generated Ref2VA output.

The CPU proof executes actual pinned ReferenceToVideo, AddGuide and PackedLayout
methods against the captured graph, with inert CLIP/VAE/management/image leaves:
five ordered encoder items, five reference blocks, ten VAE calls, five guides at
0/60/108/163/216, original AV latent unchanged. Five reference spans correctly
shift the target origin to text length + 5. Target AV positions match a baseline
with the same references and no guides. No learned weights, GPU or live service
was used. This cannot establish learned capacity or image adherence.

Initial fixture failures are retained: a missing fake Qwen health response, a
file-versus-prompt hash assertion in the standalone QA, a lane-release assertion
made before the ordinary next dispatcher tick, and absent local NumPy for the
CPU shim. These were fixture/envelope issues, not hidden live retries. The same
terminal QA job was read on restart and released by the ordinary dispatcher;
no new submission was made. NumPy 2.2.6 was installed only into ignored scratch.
`media.py` remains 478 lines: its small change extends existing asset storage
with private writes and rollback; new ordered-reference responsibilities are
separate modules. No handwritten source exceeds 500 lines due to this change.

Native ownership discovery exposed pre-existing map drift: one renamed browser
support path and seven existing V3/publication test files lacked current owners.
Only those exact path/selector entries were corrected, with independent read-only
classification. No test bodies or unrelated runtime behavior changed. Native
ownership discovery now passes for all three suites.

The independently installed pure-Python gateway wheel is SHA-256
`701e39cdabb5ceafbcfbe9c083356e77a6f9212d3364bc7b106cac01643ed27e`.
Its 50 packaged source/resource members match the checkout exactly; the manifest
SHA-256 is `fbe1724c84a31c7a30c17d8e1938a2413efa47ac711b4a84c6037c080d3c3e2a`.
The service lock hash is
`023b29e28d045d44610fe5425123d02403bfabe10d1fd59338607454f2fbf15c`.
The Mac proof used Python 3.12.13/arm64. Separate exact ARM64 Linux image
smokes passed as recorded below. Both serving roles import the package from
`/opt/venv/lib/python3.12/site-packages/plotloom_h3_gateway`; a historical
`/app/src` overlay would not update these installed artifacts. The source-only
overlays use the actual installed location and preserve the exact existing runtime
dependency closures; their image config digests/rootfs are independently retained.

## Staging and recovery decision

Runtime source is local commit `12f99bab4fac3f982782cc0a091e13091b4dd652`.
Two source-only ARM64 Linux overlays passed their isolated zero-generation
smokes, with 50 exact installed members, networking disabled, no production
mounts, GPU or Docker socket. Gateway image config SHA-256 is
`972a7bb1afa95c5bc6055461a3fd574c633e1d8c9044cdcf04023c4faf26c590`
(Python 3.12.14); dashboard is
`d685e60c768e31ffffb44e5f4c038470adc14a391108c1384530af60d006de6d`
(Python 3.12.15). Each retains its pinned base rootfs layers plus the source
layer. The manager accepted staging evidence and separately admitted serving
cutover. Exact image/rootfs, wheel/lock, dependency and interpreter evidence is
frozen in `.local/ref2va/qualification-receipt.json`; activation evidence is
separate in `.local/ref2va/activation/activation-receipt.json`.

The manager selected **gateway forward repair on the expanded current schema**
for this rollout. Preserve the preceding gateway container stopped and with
restart disabled for audit only. Do not restore that old binary after migration,
reverse the schema, reset/copy data or add a compatibility layer. If startup
fails, retain admission/UNKNOWN evidence and diagnose a bounded forward fix.
Dashboard recovery remains independent, subject to fresh idle/uncertainty checks.
Record original restart policies durably before stopping either selected role.

This is an explicit recovery preference, not a claim that the preceding serving
binary cannot read the schema. The Git parent has a strict DDL guard that rejects
the expansion; the actual serving image lacks that guard and its captured
`Store._migrate` accepts the expanded synthetic schema. The local method check
does not qualify an operational binary rollback. No serving change or schema
reversal was performed by that investigation.

The final E01-01 input packet was admitted for exactly one POST:
`docs/roadmap/别叫我的名字-shuohao-production/attempts/E01-01/attempt-01`.
Manifest SHA-256 is
`66945a73607d6b7f6ef47dfb453f6e9b62a29667f73467fc9c454e36f18340b3`;
request SHA-256 is
`fe459c9902c6c6662e2d9f06de9b42573777098bac68753b959dcf02b8c64f12`.
The manager selects `contain_pad` for all five 1672×941 opaque RGB PNGs,
totaling 10,397,354 bytes. All eight input members match after routine transfer
to `/home/wjmao/h3-shuohao-20261106-E01-01-attempt-01/input`. The subsequent
manager admission, rather than packet preparation, authorized submission.
The manager owns actual motion/native-audio creative review. The generic
learned fixture is superseded and has never been submitted.

Fresh read-only model preflight hashed the entire 20,970,379,616-byte Ref2VA
checkpoint and confirmed the expected `9255f52b…5779` identity with unchanged
file stat. Actual installed native node `108ceff1…5ccd5c` and model-source
`8e4cdda6…a4d518` match the pinned CPU proof. The check did not load weights,
access a GPU or invoke cache maintenance.

## Activation and first actual request

Activation completed at 04:50 UTC on November 7. Gateway container is
`07ddbbc91602c1bb1128cabbd719e42c577b8634fb61dc3eb54d441dcdee32b4`;
dashboard is
`8525a2c75c992b9c42cc372d69d8120cb3eebc04adbda369fd4f91dbef56dddc`.
Both have the exact 50 source/resource members. Effective configuration,
private environment, mounts/security and pre-existing gateway/voice database
rows/inodes were preserved. Comfy, Voice Lab and Tailscale identities/configuration
were unchanged. Preceding containers remain stopped with restart disabled.
Actual private HTTPS playback advanced and sought to 7.25 seconds without a
media error; a 206 range and the complete original download matched the
pre-activation SHA-256 `b45d61de…8d8`.

Two bounded activation failures are retained. The first configuration guard
found only Docker's `OomKillDisable: null` to `false` default normalization.
The first continuation then refused before mutation because of case-sensitive
human error-text matching. After reassessment, a separately admitted continuation
used successful structured inventory, the preserved actual gateway bind and
only the exact normalization. It reused the created gateway and created only
the pending dashboard. No original operation was replayed.

First-story admission SHA-256 is
`57f6d9a562edcab1e074fda01b2753c533bc1a15f1c8cddd9f8e42ac1d283a07`.
One authenticated POST created queued job
`h3_fa5120f9d10146de8f134369a3e27fe7`. Ordinary dispatch then submitted
that same job as native prompt `8fd69ec6-ed4f-465d-949d-894e963e6492` at
05:00:54 UTC. Durable intent, multipart body, creation response and known job
identity are retained; no generic or duplicate POST occurred.

The actual accepted queue record has 27 graph nodes. Its complete graph and
`client_id` equal an independently built full expectation. Comfy adds only
`create_time` to envelope metadata; no node annotation was ignored. Persisted
prompt UTF-8 bytes, snapshot, ordered bindings, all original/prepared hashes,
0600 file modes and guide frames 0/60/108/163/216 pass. This is native accepted
request/readback evidence, not a claim of intercepted transport bytes.
Evidence is `.local/ref2va/story-E01-01-attempt-01/actual/`.

The first readback helper could not read a private container-owned original
through the host UID. Its traceback is retained. Read-only access through the
existing gateway container resolved that capture issue without changing file
permissions, product code or the running job. The same known job is followed
through its ordinary status/output endpoints; terminal evidence follows.

## Terminal technical outcome

The same job succeeded. Its terminal history retains the same exact 27-node
graph, with no annotations ignored. Original authenticated output is H.264,
960×544, 277 frames at 24 fps (11.541667 seconds), plus AAC stereo 32 kHz audio
(11.542 seconds). All streams decode fully with ffmpeg exit 0 and no error
stderr. The 1,567,741-byte original SHA-256 is
`7cf18263855afdd42740e256fa99a94915106ae844d1246c327e047809821f11`.
It matches SQLite, authenticated output and the actual private HTTPS download
link. Real browser playback advanced, sought to 7.25 seconds and served 206
byte ranges without a media error. This browser check was muted; it does not
claim subjective native-audio inspection.

Native execution ran 1212.623 seconds; submit-to-gateway-completion was
1213.457 seconds (05:00:54.761–05:21:08.218 UTC). Existing logs did not emit
sampler step timings. Native history records four cached loader/configuration
nodes, not cached reference conditioning. These are one-run measurements,
not a general throughput estimate.

Fresh ordinary readback confirms an empty Comfy queue, all 363 lane rows done,
one new succeeded job (329 total, two historical failed), no voice binding for
this job, unchanged Voice counts/service identities/database device and inode,
no foreign-key violations and SQLite integrity `ok`. No extra generation,
service operation or cache action occurred. The manager owns producer-hold
release and any expansion.

Technical receipt is
`.local/ref2va/story-E01-01-attempt-01/actual/technical-receipt.json`.
The byte-identical original is retained locally beside it and independently at
`/home/wjmao/h3-shuohao-20261106-E01-01-attempt-01/original-native-av.mp4`,
outside gateway-managed 72-hour expiry. The manager received the exact file
and measured result for the separate creative gate. See the
[verification record](../verification/2026-11-07-h3-ordered-reference-images.md).
