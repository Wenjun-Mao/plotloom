# H3 cross-framework replication: partial study record

> Historical snapshot, superseded by later execution. The campaign eventually reached 23 completed paired blocks (69 fixed assessments), plus A/B originals in partial block 24; C in that block remained unstarted and the last window 26 was restored. The owner then cancelled the remaining fixed-272 plan in favor of staged mixed-style groups. The 14-block counts and open-hold observations below remain the record of the November 11 pause, not the final checkpoint or a current service-health claim. See the [November 13 direction review](h3-multistyle-group1-results.md#direction-review-after-completion--2026-11-13) for the reconciled results and their limits.

**Status at pause, November 11, 2026.** Fourteen of the planned 272 paired blocks were completed and assessed: 42 of 816 first-attempt outcomes. Three first-generation outputs in block 15 were produced, but the block was not fully collected or assessed. The study is paused. The owner is reconsidering its value while moving toward native H3; no further study execution is implied by this document.

This is a descriptive record of an incomplete study, not the planned confirmatory analysis. The 14 completed blocks are an early subset of the frozen sequence. They do not establish a winner, a population failure rate, a statistically reliable improvement, or equivalence in scene and speech quality. This summary does not substitute for original videos, detailed assessments, raw observations, seeds and runtime/source provenance if those are later deleted; deletion can make independent reinspection and faithful reproduction impossible.

## Question and design

The study asked whether changing the current configuration or the entire framework path improved the chance that a first output would be free of unintended dialogue overlays, while not worsening speech and critical scene fidelity. The owner chose a 15-percentage-point improvement as worth serious consideration, subject to the quality conditions.

The frozen study compared three arms, using the same raw fixture and seed within each block and each arm's own encoder and media preparation:

- **A:** current Comfy path, INT8 ConvRot DiT and NVFP4 Qwen, native RES20, Quality 8/base 20.
- **B:** Comfy BF16 logical DiT/Qwen, Euler 20, video/audio shifts 12/3. A-to-B compares a configuration package, not precision alone.
- **C:** vLLM-Omni BF16 logical weights and its own complete native Euler 20 path. B-to-C compares whole paths; effective conditioning, posterior handling, normalization, encoder arithmetic and model-time handling differ.

The intended sample was 272 independently drawn scene/fixture/seed blocks, 816 clips, with randomized arm order and no caption-driven rerolls. Draws came from 17 scene instances in a single story and two physical settings. The intended inference was limited to that challenge mixture, not all stories or H3 usage. The primary result was caption-qualified first output, requiring valid AV and no unowned screen-space dialogue, subtitle or speech bubble across the complete frame set. Original failures remained failures even if later recovered. Speech, action, applicable attribution/sync and intended silence were separate components; uncertainty did not count as a pass.

The planned two contrasts used exact paired tests and 97.5% intervals with predefined rules. They were planned for the complete sample; no such confirmatory claim is made from the partial results here. Blinded reviewers fixed their observations before source comparison and arm disclosure. For many audio and visible components the available assessment method was not qualified for a reliable conclusion.

## Completed observations

A read of the 42 retained `fixed-assessment-01.json` records produced these **descriptive first-output counts**:

| Arm | Caption PASS | Caption FAIL_OBSERVED | Critical scene FAIL_OBSERVED | Critical scene UNCERTAIN |
| --- | ---: | ---: | ---: | ---: |
| A | 14/14 | 0/14 | 9/14 | 5/14 |
| B | 13/14 | 1/14 | 9/14 | 5/14 |
| C | 12/14 | 2/14 | 10/14 | 4/14 |

These counts are not an efficacy estimate or ranking. The three observed caption failures occurred in block 2 for B and C, and block 10 for C. Every fixed joint-observable-quality outcome was **NON_PASS** under the study's strict rule. This reflects observed critical-scene failures and/or unqualified components; it is not a finding that every clip was unusable, or a substitute for human viewing and listening. Speech fidelity was recorded as uncertain for all 11 sampled speech-bearing blocks in each arm; three blocks were classed as no-source-speech/silent, and their intended speech absence was also recorded as unqualified. Some narrower phonetic comparisons did pass, but they do not qualify attribution, sync, subtle cutoff, silence or complete speech fidelity.

Per-block caption / critical-scene fixed statuses follow. `P` = PASS, `F` = observed failure, `?` = uncertain/unqualified. Block 1 uses the earlier first-triplet assessment schema; its caption and critical-scene results agree with the first-triplet checkpoint.

| Block | Fixture | Seed (decimal) | A | B | C |
| ---: | --- | --- | --- | --- | --- |
| 1 | E03-26 | 1711287588374304734 | P/F | P/F | P/F |
| 2 | E02-10 | 1184727101119985319 | P/F | F/F | F/F |
| 3 | E03-15 | 9062518607697183866 | P/? | P/? | P/F |
| 4 | E03-04 | 3099493628002611114 | P/F | P/F | P/F |
| 5 | E03-01 | 396756112201801547 | P/? | P/? | P/? |
| 6 | E03-05 | 7850906672376409324 | P/? | P/? | P/? |
| 7 | E03-09 | 2264375386252690315 | P/F | P/F | P/F |
| 8 | E03-26 | 3252329247808983233 | P/F | P/F | P/F |
| 9 | E03-18 | 526703132248056131 | P/? | P/? | P/? |
| 10 | E03-20 | 7944870663297582049 | P/F | P/F | F/F |
| 11 | E03-09 | 6575973028315350640 | P/? | P/? | P/? |
| 12 | E03-20 | 6388289378680417239 | P/F | P/F | P/F |
| 13 | E03-09 | 1142369379247171504 | P/F | P/F | P/F |
| 14 | E03-19 | 1377783184748840791 | P/F | P/F | P/F |

Examples of recorded visual issues include an extra or early cut in block 14 across all arms and a jacket removed from a stool in block 12 despite the literal source requirement. The literal scoring rules matter: these observations do not by themselves measure overall creative quality or prove which pipeline caused the issue.

## Prior six-clip pilot

The separate completed pilot used two seeds in one scene and six clips. One of two current-configuration A clips contained dialogue overlays; neither of the two B nor two C clips did. One B clip's source speech remained uncertain. This was descriptive, not evidence that BF16 or vLLM-Omni reliably avoids captions; the pilot explicitly recommended retaining Comfy as the working production path at that time rather than inferring a migration from six clips. The pilot's source report and its separate evidence archive are not the replication study's completed sample.

## Interruption, retained state and native H3

Block 14 fully closed at approximately 03:55 UTC on November 11. Block 15's original A, B and C primary generations succeeded and were retained. Its controller stopped around 05:23 UTC at the B collection capacity guard after Spark available space fell below the 56 GiB admission threshold. B collection and six perception calls remained untouched. The original controller must not be blindly restarted, and these first outputs must not be represented as assessed or rerolled. Fourteen blocks had fully closed; block 15 was not a fifteenth completed block.

The known original service-restoration obligation remained open at pause; the last observed two user services were stopped. The window-17 retention forecast expired without establishing either deletion or continued later protection. Prior point checks verified the preserved copies then examined, but some original paths were unknown. Current remote process, service and data state must be checked before any service or retention action; this historical record is not a current health check.

A native H3 direction is a product decision, not a conclusion demonstrated by this incomplete experiment. Before deleting or moving files, distinguish this obsolete comparison's data from model weights, runtime assets and original-service data still needed by production or a future native H3 workflow. In particular, some models, audio-model and VAE/audit paths under the earlier caption-pilot directory were mounted by this replication; their presence in an old-looking directory does not make them disposable. Keeping the written summary alone will not preserve those assets or make the experiment independently auditable.

## Sources and provenance at time of writing

- Reviewed [replication plan and status](别叫我的名字-shuohao-production/quality-decisions/caption-analysis/2026-11-09-cross-framework-replication-plan.md), including design, first triplet, later checkpoints and interpretation limits.
- [Six-clip pilot report](别叫我的名字-shuohao-production/quality-decisions/caption-analysis/2026-11-09-cross-framework-results.md) and [first-triplet checkpoint](别叫我的名字-shuohao-production/quality-decisions/caption-analysis/2026-11-10-replication-first-triplet-checkpoint.md).
- Historical local source: `.local/ref2va/cross-framework-replication-20261109/visual-assessments/*/fixed-assessment-01.json` (42 records) and `blocks/b0002` through `b0014/assessments-fixed-01.json`. A local check matched all 39 block-2-through-14 assessment bytes and SHA-256 hashes against their fixed-block records. Block 1's three fixed records were cross-checked against the first-triplet checkpoint. No complete 272-block dataset or final confirmatory report was produced. These paths may cease to exist if cleanup removes the study tree.
- Historical pause and recovery details: `.local/ref2va/cross-framework-replication-20261109/RESUME.md`, particularly `CRITICAL CURRENT BLOCK15 CAPACITY HOLD` and `USER-REQUESTED PAUSE`. These are operational records and may also be removed in cleanup.

This document records what the evidence supported at the pause. It should not be read as proof that a remote backup, all raw AV, the future native-H3 runtime, or a final service restoration exists.

## Model cleanup

The assistant misunderstood the owner's cleanup scope and mistakenly removed the Spark copies of the BF16 diffusion and text-encoder weights used by arms B and C, the comparison's VAE weights, and its Qwen2.5 Omni audio-review weights. The owner subsequently clarified that the earlier experiment was to be cleaned up, not this ongoing three-arm study. The quantized native H3 weights in `/home/wjmao/models/comfyui-h3` were retained. Recovery used the original pinned sources and the retained generated-output hashes. All 12 assets have since been restored and verified, as recorded below. Study outputs and the remaining operational records were not removed as part of this model cleanup; the window-17 service-restoration obligation remains open.

## Model restoration completed — November 12, 2026

The earlier pending-recovery status is now resolved: all 12 mistakenly removed current-study weights were restored and matched their original byte sizes and SHA-256 hashes. Canonical files are under `/home/wjmao/models/h3-three-arm-study`, with same-inode compatibility links at the existing study paths and no duplicate payload storage. The two generated B VAEs also matched exactly. Unused image/package/build-cache cleanup preceded restoration; final available space was approximately 215.26 GiB. The study remains paused and its separate block15/service-restoration holds were not changed. See `.local/ref2va/study-model-recovery-20261112/RESULT.md`.
