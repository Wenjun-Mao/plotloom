# Voice specialist reliability and held handoff closeout

Authority: owner goal “Go ahead and tackle 1–4”, following `ef7716f` maintenance
adoption. This is a new bounded experiment, not a replacement for the earlier
failed matrix or controlled retest. No Relay, Plotloom changes, director contact,
merge or push. Runtime source/model configuration was not changed.

## Real-call accounting

| Window | Calls | Result |
|---|---:|---|
| Exact neutral Index probe, Comfy models cold, Qwen-Image running | 1 | Completed |
| Fresh full workflow: paired creation, independent Qwen regeneration, four neutral paths, two Index controls | 9 | 9 completed |
| H3 Ref2VA with exact newly published reference | 1 | Succeeded, complete video/audio decode |
| Exact neutral Index probe after H3, without unloading/stopping other services | 1 | Completed |

Total: **11 voice calls + 1 H3 call**, within the separately approved caps.
No replay, fallback or additional seed search. The H3 observation script
initially expected Voice Lab's `completed` rather than gateway `succeeded`.
Only that observer was interrupted and resumed against its recorded accepted
job; the sole generation continued unchanged. Resume requires one known
accepted job and cannot execute the submission branch.

## Cold and warm CUDA evidence

Both probes pin the original failed trial
`vt_d2688889bdb845149eae046172a7785a`, its source recording, words, seed and
semantic model/settings. The original terminal trial and existing Voice IDs
remain unchanged.

| Measurement | Cold Comfy | Post-H3 resident |
|---|---:|---:|
| New trial | `vt_cdd1eb83664243a0948e894918949adb` | `vt_f8f4d75fd6b9470ba848f17ba0d1b644` |
| Host MemAvailable before, GiB | 74.015 | 30.553 |
| Host MemAvailable after, GiB | 73.060 | 33.424 |
| Sampled peak child RSS, GiB | 6.402 | 7.609 |
| Measured child execution, seconds | 48.562 | 108.140 |
| Peak Torch allocated, GiB | 7.426 | 7.426 |
| Maximum observed voice children | 1 | 1 |

Both native mono PCM16 WAVs are 22,050 Hz, 3.413333 seconds, SHA-256
`f1c005026193dc318335347efb0fed61a9430c19e0ef3320ad8645f61a61f007`.
All voice children exited. No Qwen-Image pause, Comfy cache release, inference
package change or model replacement occurred in this closeout.

These passes establish those exact serialized windows, not a statistical
reliability claim, a CUDA root-cause fix or atomic cross-service admission.
The [operating decision](../adr/0096-voice-lab-shared-host-operating-boundary.md)
retains advisory checks and requires operator-serial qualification windows.

## Full voice workflow

Technical project: `vp_56cb23ecfbe1400aa23753006d13702b`.
Creation: Qwen `vg_6155d99b7d7f4caebd01bb2258fd1361` and MOSS
`vg_c61a36118c4d4705997ad90530841305`; independent Qwen replacement
`vg_cc350efc9e83448a90c0f5b689f1e483`. MOSS hash stayed unchanged.
Old unpublished Qwen audio was retired; its attempt/provenance stayed readable.

| Creator → reuse/control | Trial | Result |
|---|---|---|
| Qwen → Qwen neutral | `vt_afff9aace81a471cb920a83a455d40d3` | Completed |
| Qwen → Index neutral | `vt_e86d12eafb2b4a189314c61c8337b3f4` | Completed |
| MOSS → Qwen neutral | `vt_45e49a93bf8343a1ab1ed0b10d1c1dc9` | Completed |
| MOSS → Index neutral | `vt_93824fcf40414db098d3da54c91e60f0` | Completed |
| MOSS → Index Chinese description | `vt_fd6821387efc4839ba194ff3823b49a3` | Completed |
| MOSS → Index manual strengths | `vt_8e4e8fd273774fdb81cadf2d2f64dcaf` | Completed |

Downloaded the two current creation WAVs and all six takes; each matches its
recorded output hash and native mono format. Qwen/MOSS are 24-kHz FLOAT;
Index is 22.05-kHz PCM16. Reference `sourceSha256` on a reuse trial is not its
new take's `audioSha256`.

The description classifier in this fresh technical run proposed only calm
`[0,0,0,0,0,0,0,1]`; manual control retained explicit anger `0.25`.
Neither the classifier's proposal nor WAV validity proves the desired acting.
Earlier owner listening findings remain bounded, not universal presets.

Published MOSS Voice ID: `voice_5689e99835494d2f8024485523c4dbf6`.
Source hash: `718e7be1c4dae69e2987b6731008d17105800116f4356f0a1f852c02474015c4`.
H3 derivative hash: `e0f6400b8536f238694a445f72e4625cc6f1e81715c3328490be72237450cc9b`.
This is a technical publication, not replacement of the owner's preferred
original MOSS D or a new creative approval.

## Exact H3 consumption and restart

Job `h3_42ebef34fcaa43bfa8457a91ee1cf4d0` used Ref2VA Base-20, 576×1024,
124 frames, requested five seconds, seed 20260923. Backend elapsed 465.456s;
delivered frame duration 5.166667s. H.264/AAC 32-kHz media decoded fully.
Output SHA-256: `4fb3ad9dd3e05c1e9363402c96a6242ff150a5b31e81a6c8c40cd56808da22a8`.
The gateway DB snapshot, source WAV and prepared Comfy WAV all bind the exact
published H3 hash above (332,844 bytes, 5.2s). No Voice ID resolver was added:
the operator resolved the Lab ID and sent verified bytes.

Only idle `plotloom-voice-lab.service` was restarted. Exact project/trials,
original failure, all three published voices and **54 WAVs** survived; SQLite
integrity is `ok`. Gateway, ComfyUI and Qwen-Image were not restarted.
Final services were ready/idle and no voice child remained.

## Browser and packaging verification

- Real FastAPI/file-SQLite fixture: paired generation, independent regenerate
  with sibling unchanged, Index controls and copy-to-manual, explicit publish,
  blind mode, cancelled navigation, project isolation and refresh. The fixture
  uses synthetic test audio, not claimed real-model output.
- Actual Spark UI: two candidates, six reuse takes and the published Voice ID
  restored through reload and the real idle service restart.
- 1440×900 [real-model candidate view](supporting/voice-lab-real-model-closeout.png),
  [fixture candidate view](supporting/voice-lab-multi-engine-candidates.png) and
  [fixture control view](supporting/voice-lab-multi-engine-reuse.png) inspected.
  These are deliberately scrolled section views, not whole-page-fit evidence.
- Final locked service tests: **48 passed**. Root extraction boundary: **13
  passed**. Existing gateway voice-reference regressions: **21 passed**.
  Starlette emits the existing TestClient deprecation warning; no deselections.
- Both web JavaScript syntax checks, scoped root-environment Ruff and
  `git diff --check` passed. Frontend/build/E2E gates for Plotloom were not
  repeated: its runtime/frontend and gateway implementation did not change.
- Service wheel rebuilt; SHA-256
  `67a330278e34b6dbdf62a1d6783caaf4341a3c71872670bf869346596b9623b2`.
  Installed into an isolated target using the service's locked control-plane
  dependencies; CPU app import and packaged web assets passed, with no Torch
  import. This is an installed-wheel smoke, not a fresh GPU solver claim.
- Independent read-only review found a same-receipt concurrent-start race in
  qualification tooling. Fixed all four operators with exclusive creation,
  private mode, file/directory sync and regression proof of one claim among
  16 concurrent starts. Existing-receipt and invalid-resume tests fail before
  side effects. Reviewer confirmed the correction; no other material findings.
  This tool claim is not a cross-service GPU lease. No real calls were repeated
  for the correction. Current tools are deployed together; original raw trial
  records remain unchanged.
- Owned local fixture/browser stopped. Extra screenshot copies moved to the
  private `plotloom-canaries/2026-09-30-voice-reliability-closeout/` directory;
  Git retains the three scoped supporting views. No user assets were deleted.

## Private retained evidence

Under Spark `/home/wjmao/services/plotloom-voice-lab/runtime-inventory/`;
raw records may contain spoken text, private paths and host metadata and are
not committed. They contain no provider secret. Receipt fingerprints:

| File | SHA-256 |
|---|---|
| `cuda-resident-cold-2026-09-30.json` | `cf2171e2592c31f648ec91e8e2f220a676952d6dde718108ae0c411443d756c6` |
| `workflow-closeout-2026-09-30.json` | `726654fe56fe5daa07c226f99a6dba37e5e769b1acbe1e1fde8bad1a396c8c2f` |
| `published-h3-closeout-2026-09-30.json` | `cd1d2d394ea4fbe4a048caafc62daffcd9adb1dd39403eb7730a43349ffea418` |
| `cuda-resident-post-h3-2026-09-30.json` | `9e9c33813b171129a2e58689539085da4690821925c895bd3331efec80f9e1fb` |
| `idle-restart-closeout-2026-09-30.json` | `e208b377147988cd09c26f4e058b05f3ccc284dbf1ab99661658986fdbbbaa4c` |

## Held delivery and remaining boundaries

The [handoff package](2026-09-26-voice-candidate-handoff-draft.md) consolidates
APIs, IDs, immutable media ownership, reproduction and Plotloom-side work.
Director contact remains withheld. No general co-resident concurrency, new
human acting/lip-sync acceptance, clean-solver GPU rebuild, or Plotloom Voice ID
integration is claimed. Usage/cost telemetry is unavailable.
