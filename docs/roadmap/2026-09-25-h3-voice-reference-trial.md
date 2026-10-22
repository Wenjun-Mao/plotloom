# H3 voice-reference and lip-sync trial · 2026-09-25

## Decision and boundary

Test whether H3's native Ref2VA path can keep the same character's Mandarin
voice recognizably consistent across two visually distinct shots **while**
speaking the authored lines with convincing mouth motion. Success means a
human can watch and hear the result and accept the performance; matching a
pre-recorded waveform sample-for-sample is not the goal. A separate dub and
lip-sync stack is a later alternative only if native generation fails.

This is a Spark-only, unselected specialist experiment. It does not change
Plotloom authoring, the public H3 gateway, model-quality catalog, production
profiles, or existing FL2VA checkpoints. Plotloom's H3 use takes priority: if
its queue becomes occupied or the director reports new use, pause trial
dispatch. Preserve all current services, models, experiment evidence, and
generated results. Do not remove the setup without explicit confirmation.

## Evidence and feasibility gates

- The deployed Spark ComfyUI reports PyTorch 2.14.0+cu130. The gateway and
  ComfyUI queues were empty at preflight, but other resident models left only
  about 30 GiB of available host memory; recheck immediately before a run.
  Current memory-pressure averages and swap-in/out were zero, but kernel logs
  record an NVIDIA allocation failure on September 23. Model admission must
  fail closed on memory pressure rather than retrying or stopping other services.
- Current FL2VA uses a separate checkpoint. Ref2VA is absent and requires a
  separately stored model under `/home/wjmao/models/comfyui-h3`. The
  [Comfy-Org model card](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/README.md)
  prefers `int8_convrot` with cu130. The [reported FP8 Ref2VA metadata defect](https://github.com/Comfy-Org/ComfyUI/issues/15567)
  makes the pruned INT8 ConvRot checkpoint the first candidate. Verify its
  download checksum and load before generating. No conversion or mutation of
  the working FL2VA model.
- The installed `MiniMaxH3ReferenceToVideo` accepts audio and image
  references; `MiniMaxH3AddGuide` can anchor a first-frame image. The reference
  path is a different conditioning contract, not a transparent switch in the
  existing gateway. Confirm the actual workflow graph and memory fit with a
  minimal dry run before a full creative comparison. The first trial uses the
  Ref2VA base checkpoint at 20 `res_multistep` steps and native 12/3 shifts;
  it does not reuse an FL2VA Turbo LoRA or introduce a new Ref2VA LoRA.

## Ordered bounded trial

1. Freeze two input shots and their existing first-frame images: U4
   `opening-s1-c1` and `opening-s1-c2` (same C01 speaker, different framing and
   dialogue). Record source paths, hashes, lines, seeds, prompt, checkpoint,
   sampler, dimensions, steps, and frame count. Use a copy of the retained
   director-reviewed C original as the **test-only voice reference**; record
   its exact audio interval and quality. Do not edit the canonical assets.
2. Install only the needed Ref2VA checkpoint in the Spark model root. Run
   one isolated, short native-audio canary with the C01 image/voice references
   and first-frame guide. Check load, dimensions, duration, playable AAC,
   absence of obvious input-frame distortion, and no collision with the
   production gateway. If model loading or memory fails, stop and report that
   cause before changing other services.
3. If the canary is technically sound, generate the adjacent C01 shot with
   the same voice reference and its own reviewed first frame. Retain the
   original FL2VA pair as a practical comparison baseline, not a controlled
   estimate of the reference's isolated effect; no broad seed sweep until
   these two outputs are reviewed. All trial files and receipts live in a
   dated Spark experiment directory, not ComfyUI's shared loose output.
4. Inspect each original MP4 and the two-shot sequence. Separate objective
   checks (frames, resolution, audio stream, duration, hash) from attended
   creative checks: correct and complete Chinese words; no extra speech or
   subtitles; voice sounds like the same person across cuts; mouth movement
   matches audible syllables; character appearance and first-frame pose stay
   coherent. Note any scene-audio contamination from the reference.
5. Record a clear verdict: native Ref2VA useful, inconclusive, or unsuitable.
   Only after an accepted result should we discuss gateway integration and a
   durable `VoiceReference`/provenance contract. If lip-sync or exact dialogue
   remains unreliable, evaluate separately produced voice plus dubbing/lip-sync
   as an explicit next design, not an automatic fallback in this trial.

## Stop rules and retained evidence

At most one canary plus the one adjacent-shot follow-up are admitted without a
new review of results. Do not resubmit an unknown-outcome ComfyUI request.
Do not interrupt active Plotloom jobs, stop unrelated services for memory,
alter the public gateway, or delete assets as an experiment cleanup shortcut.
Retain a secret-free receipt with exact model/workflow versions, hashes,
resource observations, results, and human notes. A technically valid video is
not by itself proof of voice identity or lip-sync quality.

## Trial checkpoint · 2026-09-25

The planned C1 and C2 Spark runs completed successfully. Both eight-second
960×544 MP4s passed stream inspection and full decode; each has native AAC
audio. ComfyUI's queue is empty, and Qwen-Image remained online. The runner,
frozen prompts/graphs, per-shot receipts, both videos, and a consolidated
README are retained under
`/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-voice-2026-09-25/`.
The README records exact IDs, hashes, timings, and resource observations.
The user's first review found good, matching-sounding voices in both shots and
no extra speech or subtitles. C2 has good visible lip-sync. C1's line occurs
off-screen, so it is not a lip-sync failure or a usable lip-sync sample. The
voice-continuity result is promising, but a second visible-speaking shot is
needed before claiming cross-shot lip-sync consistency. With the user's
approval, a targeted C1 visible-speaking retake was generated from the same
medium-shot first frame, reference, seed and line. Its 2/4/6-second stills
show the face and mouth in frame, and the MP4 passed stream inspection and
full decode. After being asked to compare words, mouth timing and voice with
C2, the user reported, "It's all good." Treat that as acceptance of this
bounded retake, not general reliability or numeric lip-sync measurement.
Native Ref2VA is now a candidate for a separate gateway-integration plan;
no gateway-integration decision has been made. The Spark experiment README
and `c1_visible_receipt.json` retain the exact evidence.
