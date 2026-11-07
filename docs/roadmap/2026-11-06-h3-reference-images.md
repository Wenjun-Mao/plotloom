# Native ordered Ref2VA images through the public gateway

## Current status

Updated November 6, 2026. Implementation and qualification owner is the H3
specialist, chat 01a0983e-0e5f-7171-950e-011adaf53303. Manager and final
closeout owner is chat 01a1902a-80b6-7d80-a166-9c980850982f. Authoritative
checkout is local Plotloom main with existing owner storyboard changes.
The typed route, frozen snapshot, native graph and lifecycle implementation
are complete. Independent Sol/High source review is closed after fixing the
dashboard subtype projection. Focused checks (61 tests), isolated gateway and
dashboard wheel installs, 14 dashboard UI checks, retained-AV functional QA and
the pinned native CPU ordering/layout proof pass. All 5,173 Python cases passed in the final full gate; its unfiltered
browser and root-wheel steps remain running; shared activation and the one learned smoke remain unperformed and
require manager coordination. No shared service has been changed. Stop at the qualified generic gateway handoff and exact install
readback. The matched-B experiment remains paused.

## Acceptance

| Claim | Required evidence | Fresh media | Status |
| --- | --- | --- | --- |
| Ordered timed images reach the native encoder and guides | Authenticated public request, durable restart, exact full Comfy envelope, original prompt and image bindings | No | Passed: authenticated API/restart and complete envelope, retained AV download; pinned real native CPU methods with inert leaves |
| The ordinary lifecycle remains safe | Input refusals, partial rollback, FIFO, cancellation, UNKNOWN, tamper and retention checks, existing-route regressions | No | Passed focused contracts including existing dashboard/voice/schema regressions; final full gate running |
| Five references work with the installed learned runtime | Exact manager-admitted E01-01 request through public API to terminal download and native graph/readback | One actual story job replacing the generic fixture | Await final cash-frame manifest and exact dispatch admission |
| The package can be activated | Stable independent review, applicable full local gate, exact package and installed source readback, protected-state preservation | No | Independent review, Mac wheel and exact ARM64 image smokes passed; full Python5173 passed, browser/root-wheel running; activation pending |
| Shuohao source fidelity | Exact UTF-8 source prompt and five requested times preserved in final request | No | Exact prompt and times match the final fake-transport request; final story frames are under cash-reference revision |

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
No measured five-image capacity or runtime is available. Keep `ref_image_size`
at `match` and retain the shared single-inference FIFO.

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
No story submission is authorized until its final exact package and fresh window.

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
not duplicate suites. Scratch evidence is `.local/ref2va/` pending the final
retained package receipt. The functional journey used five distinct retained
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
The Mac proof used Python 3.12.13/arm64. It does not replace the required exact
ARM64 Linux image smokes. Both currently serving roles import the package from
`/opt/venv/lib/python3.12/site-packages/plotloom_h3_gateway`; a historical
`/app/src` overlay would not update these installed artifacts. Prepare source-only
overlays at the actual installed location, preserving the exact existing runtime
dependency closures, and prove their image config digests/rootfs separately.

## Staging and recovery decision

Runtime source is local commit `12f99bab4fac3f982782cc0a091e13091b4dd652`.
Two source-only ARM64 Linux overlays passed their isolated zero-generation
smokes, with 50 exact installed members, networking disabled, no production
mounts, GPU or Docker socket. Gateway image config SHA-256 is
`972a7bb1afa95c5bc6055461a3fd574c633e1d8c9044cdcf04023c4faf26c590`
(Python 3.12.14); dashboard is
`d685e60c768e31ffffb44e5f4c038470adc14a391108c1384530af60d006de6d`
(Python 3.12.15). Each retains its pinned base rootfs layers plus the source
layer. The manager accepted staging evidence; serving cutover remains separately
admitted. Exact image/rootfs, wheel/lock, dependency and interpreter evidence is
consolidated in `.local/ref2va/qualification-receipt.json` pending closeout.

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
