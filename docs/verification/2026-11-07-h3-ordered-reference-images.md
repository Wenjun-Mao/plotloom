# H3 ordered reference images · 2026-11-07

The authenticated gateway now accepts 1–9 ordered still images and matching
millisecond anchors through `POST /v1/video-jobs/from-reference-images`.
The deployed implementation is local main revision
`12f99bab4fac3f982782cc0a091e13091b4dd652`; later checkpoints change only
documentation. [ADR 0237](../adr/0237-h3-ordered-reference-images.md) and the
[current plan](../roadmap/2026-11-06-h3-reference-images.md) own the contract.

The first actual five-image request succeeded. Its accepted and terminal native
graphs and persisted inputs pass exact comparison; authenticated native AV
download, decode and real HTTPS playback pass. This checkpoint does not
establish story quality, repeated-run reliability or nine-image learned capacity.

## Qualification

| Evidence | Result and boundary |
| --- | --- |
| Focused gateway/dashboard contracts | 61 passed; API, persistence, strict admission, image integrity/rollback, lifecycle and existing routes |
| Dashboard Node checks | 14 passed; reference-image subtype rendering and existing media controls |
| Quick and static checks | Passed |
| Full local gate | Exit 0, 4087.690 seconds; 5173 Python, 1738 frontend and 366 browser cases, types, deterministic frontend assets/parity, installed root wheel |
| Native ownership discovery | All 417 Python, 190 frontend and 101 browser files owned; seven ownership-guard checks passed |
| Retained-media functional journey | Real authenticated API, SQLite, restart, one fake native submission, retained MP4 transfer/download and full AV decode; no learned execution |
| Pinned native CPU proof | Actual ReferenceToVideo, AddGuide and PackedLayout methods with inert CLIP/VAE/management/image leaves; five ordered encoder refs, five guides, ten VAE calls, original AV latent preserved |
| Mac gateway/dashboard wheel installs | Passed in isolated environments, Python 3.12.13/arm64; exact 50 packaged source/resource members |
| ARM64 Linux image smokes | Both roles passed with network disabled and no production mounts, GPU or Docker socket; inherited dependency closures unchanged |
| Stable independent review | Sol/High source, delta and activation reviews closed; concrete findings fixed before the admitted operation |
| Hosted CI and push | Not requested/not run; no push |

The source wheel SHA-256 is
`701e39cdabb5ceafbcfbe9c083356e77a6f9212d3364bc7b106cac01643ed27e`;
50-member manifest SHA-256 is
`fbe1724c84a31c7a30c17d8e1938a2413efa47ac711b4a84c6037c080d3c3e2a`.
The service lock SHA-256 is
`023b29e28d045d44610fe5425123d02403bfabe10d1fd59338607454f2fbf15c`.
The frozen qualification receipt is `.local/ref2va/qualification-receipt.json`,
SHA-256 `5b85ce04a0854220294bee7bddebaa4d2b1fd1b96a50b2bd0e96264e26dc2ee9`.
Its pre-activation fields describe that earlier checkpoint; subsequent facts
are retained in separate activation and first-job evidence.

Initial offline fixture failures remain in the evidence: missing fake Qwen
health, a file-versus-field hash assertion, a lane-release assertion before the
ordinary dispatcher tick, and missing NumPy for the CPU shim. They were repaired
without live submissions. Native ownership discovery also required narrow
repairs to existing renamed/unowned selectors. No unrelated runtime or test
bodies changed. `media.py` remains 478 lines because its small extension belongs
to existing asset storage; new reference responsibilities are separate modules.

## Exact activation

| Role | Image config SHA-256 | Linux Python | Serving container |
| --- | --- | --- | --- |
| Gateway | `972a7bb1afa95c5bc6055461a3fd574c633e1d8c9044cdcf04023c4faf26c590` | 3.12.14/aarch64 | `07ddbbc91602c1bb1128cabbd719e42c577b8634fb61dc3eb54d441dcdee32b4` |
| Dashboard | `d685e60c768e31ffffb44e5f4c038470adc14a391108c1384530af60d006de6d` | 3.12.15/aarch64 | `8525a2c75c992b9c42cc372d69d8120cb3eebc04adbda369fd4f91dbef56dddc` |

Both serving roles read back all 50 exact installed members. Configuration,
private environment, mounts/security, pre-existing gateway/voice database
rows and inodes were preserved. The 430 existing image bindings survived the
known-schema migration. ComfyUI, Voice Lab and Tailscale identities/configuration
were unchanged. Previous gateway/dashboard containers remain stopped with restart
disabled. The manager selected bounded forward repair for the gateway on the
expanded schema; the preceding binary is retained for audit, not restoration.

Real Chromium on the private HTTPS dashboard played and sought retained AV
without a media error. A 206 byte-range request and full original download
matched the pre-activation SHA-256
`b45d61de379c978517ac73f2aec744072318655507d9461c07d5d421aed0a9d8`.
Activation receipt `.local/ref2va/activation/activation-receipt.json` has SHA-256
`bd66a9ec27e7070e5a2d0bc540e538227f0aa3209e5deed1280fb6dd0696ff79`.

The first activation guard retained a single Docker serialization difference,
`OomKillDisable: null → false`. A continuation then refused before mutation
because it matched case-sensitive human error text. After reassessment, the
separately admitted final continuation used structured inventory and the actual
preserved gateway endpoint. It accepted only that normalization, reused the
created gateway and created only the pending dashboard. Failure receipts and
entered markers remain; the original operation was not replayed.

## First actual production request

The manager substituted one real Shuohao E01-01 job for the initially proposed
generic smoke. The generic fixture was never submitted. Frozen packet
`docs/roadmap/别叫我的名字-shuohao-production/attempts/E01-01/attempt-01`
has manifest SHA-256
`66945a73607d6b7f6ef47dfb453f6e9b62a29667f73467fc9c454e36f18340b3`,
request SHA-256
`fe459c9902c6c6662e2d9f06de9b42573777098bac68753b959dcf02b8c64f12`,
and prompt SHA-256
`294da25badb73f39f1c3a0a83a8fbf19be921ea9edd450f7a5e3ae54fec17fab`.
Five cash-corrected 1672×941 RGB PNGs total 10,397,354 bytes. Inputs are
`contain_pad`, 960×544, seed 20261106, requested duration 11300 ms and
anchors 0/2500/4500/6800/9000 ms, resolved to 0/60/108/163/216.
Native length is 277 frames at 24 fps, or 11.5416667 seconds.

A fresh complete 20,970,379,616-byte Ref2VA checkpoint hash matched
`9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779`;
its stat remained unchanged. Installed node source
`108ceff11e5a5c9a34a57bbc380447cf9941beb673a1bd421abc818de54ccd5c`
and model source matched the CPU proof.

The separately admitted single POST created queued job
`h3_fa5120f9d10146de8f134369a3e27fe7`. Ordinary dispatch then submitted
that same job as native prompt `8fd69ec6-ed4f-465d-949d-894e963e6492`
at 05:00:54 UTC.
Durable intent, raw multipart body, response and known job ID are retained.
The 27-node accepted graph and `client_id` exactly equal the independently
constructed expectation, including unchanged template nodes. Comfy adds only
`create_time` envelope metadata; no node field was normalized. Prompt UTF-8,
full snapshot, ordered rows, source/prepared file hashes and 0600 modes pass.
This proves the native accepted request and persisted readback, not intercepted
transport bytes. Base-20, adopted VAE, five encoder references and five matching
guides are intact; there is no reference audio input.

The initial readback helper encountered host-UID permission denial on a private
container-owned original. The retained failure was resolved through read-only
access inside the existing gateway container. No file permissions, running job,
source or submission identity changed. No creation was retried.

First-job evidence is `.local/ref2va/story-E01-01-attempt-01/actual/`, including
`actual-request-comparison.json`. The same known job completed through its
ordinary authenticated status/output endpoints. No additional story jobs,
broad quality claim or repeated-run reliability are covered here.

## Terminal native AV and operational readback

The job succeeded with native history `success`. Every terminal graph node and
input matches the accepted queue graph and full independent expectation; no
node annotation was ignored. Authenticated output is 1,567,741 bytes with SHA-256
`7cf18263855afdd42740e256fa99a94915106ae844d1246c327e047809821f11`,
matching SQLite, the gateway download receipt and the actual private HTTPS
original-download link.

Video is H.264, 960×544, 277 frames at 24 fps, duration 11.541667 seconds.
Native audio is AAC, stereo, 32 kHz, duration 11.542 seconds. Full ffmpeg decode
of both streams returns 0 with no error stderr. Real Chromium playback advances,
seeks to 7.25 seconds without a media error, and receives a valid 206 byte range.
The complete HTTPS body and actual download-link file match the original hash.
This playback check is muted; subjective picture/native-audio review belongs to
the production manager and is not inferred from successful decode.

Native execution takes 1212.623 seconds. Submission to gateway completion
observation takes 1213.457 seconds (05:00:54.761–05:21:08.218 UTC).
The single current-job log read had no sampler step counters/timings. Native
history reports cached video/audio VAE loader, CLIP loader and sampler-selector
nodes; reference conditioning itself is not cached. This is one measured
five-reference/277-frame run, not a general all-episode throughput promise.

Fresh existing-observer readback confirms Comfy queue empty, all 363 shared-lane
rows done, exactly one succeeded job added (329 total, plus two historical
failed), no voice binding for this job, unchanged Voice counters and service
identities/database device/inode, foreign-key check empty and integrity `ok`.
No additional POST, cache action or service operation occurred. Producer-hold
release remains with the manager.

The exact local original is
`.local/ref2va/story-E01-01-attempt-01/actual/original-native-av.mp4`, with an
independent retained copy at
`/home/wjmao/h3-shuohao-20261106-E01-01-attempt-01/original-native-av.mp4`.
Both survive gateway-managed 72-hour expiry. The manager received the exact
file and technical results before closeout documentation. Consolidated technical
receipt is `actual/technical-receipt.json`, alongside terminal history, SQLite
readback, input hashes, probe/decode and real-browser evidence.
