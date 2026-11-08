---
name: video-checking
description: Review generated clips against supplied story actions, references and dialogue using cached evidence, Terra/high reviewers and sampling audits. Produces review recommendations; does not generate, repair or select production media.
metadata:
  version: "0.1.2"
---

# Video checking

Use one primary reviewer per assigned clip. Reuse valid technical evidence; spend
model work on observable story fidelity and uncertainty. Results are recommendations,
not production selections or generation authority. Invocation is manual; bounded
internal workers/audits may operate within that invocation. Preserve any generation
pause. Checking does not authorize source edits, retries, provider/service actions
or invocation of an authoring skill.

## Prepare once

Use a supplied case or construct the compact input in [contracts.md](references/contracts.md)
from the given source, clip and references. Include relevant actions, preserved world
and dialogue; avoid whole-project history and previous quality judgments. Missing
required context is uncertainty, not permission to invent an expectation.

Use the self-contained `scripts/` tools in an existing Python environment. Consult
`--help` for current arguments. Local ffmpeg/ffprobe are required; no provider key,
installation or download is implicit.

- `prepare_review.py` creates or verifies a content-bound evidence bundle. Reuse a
  pinned decode receipt and blind ASR only when they match the actual video.
  Source/reference/reuse/code changes invalidate the relevant cache key. Validation
  checks the current original inputs; a frozen cache is not proof that they remain current.
- Use uniform contact coverage of every shot and native-resolution anchors. Existing
  uniform derivatives may be reused; confirm contact-sheet dimensions match their
  declared frame coverage before review. Prior reviewer-picked failure images must not
  be the sole evidence in a blinded evaluation.
- Additional detail extraction preserves the original and records its frame/hash.
  Preparation/cache errors are tool/input problems, not media-quality rejections.
- ASR may use an approved local cached model/environment, without source words,
  language forcing, hotwords, initial prompt or VAD. Never install/download or use
  a paid fallback implicitly. Missing required recognition blocks a pass; use `needs_review` unless an
  independently observed material defect already supports failure.

Mechanical checks belong in code. Do not repeatedly ask a model to compare hashes
or recalculate clocks already checked by the tools. Technical PASS establishes
bindings/decodability, not correct performance or picture content.

From the skill directory (or use absolute script paths):

```sh
python3 scripts/prepare_review.py prepare /path/case.json --output /path/cache
python3 scripts/review_results.py validate /path/review.json --bundle /path/prepared-bundle-directory
python3 scripts/review_results.py batch /path/batch.json --seed 1024 --per-decision 1
```

For a new blind transcript, `blind_asr.py VIDEO --python EXISTING_PYTHON --model
LOCAL_MODEL_DIR --output NEW_JSON` uses an already installed local environment.
Pin its result into the case before preparation. A batch manifest is an array of
`{review, bundle, details?}` paths (`bundle` is the directory containing
`bundle.json`), with optional `highRisk: true`; relative paths
resolve from the manifest. `detail` and audit options are shown by `--help`.

## Primary review

Default worker: GPT-6.1 Terra, reasoning `high`, when available. With collaboration
tools, use a bounded number of disjoint workers and native fields
`model: "gpt-6.1-terra"`, `reasoning_effort: "high"`, `fork_turns: "none"`.
Send only the skill path, case/bundle paths, output path and permitted scope.
Do not send prior conclusions, suspected defects, intended answers or manager
history. Avoid nested reviewer hierarchies. Respect explicit user model choices;
disclose unavailable or inherited settings.

Each worker reads this skill, the case and [review-rules.md](references/review-rules.md).

1. Open actual reference images and every shot's native contact coverage. Identical
   pixels may have different roles in different shots; judge the current context.
2. Open readable native anchors for writing, hands, props and mouth-state claims.
   Extract a targeted detail when thumbnail evidence is insufficient.
3. Compare sequence/endpoint with authored actions and preserved world. Grade
   material contradictions; describe tolerable variation as minor.
4. Compare blind recognition with expected dialogue. ASR is not perceived listening,
   literal spoken-word/voice certification, proof of silence, or lip-sync review.
5. Write one compact result under [contracts.md](references/contracts.md), citing
   actual evidence viewed, time-bounded findings and limits. Validate it with
   `review_results.py`. Never list an image as viewed without opening it.

Use `pass` for source-compatible evidence, `fail` for an observed material
contradiction, and `needs_review` for unresolved required evidence. Sampled pictures
do not establish every-frame or continuous-motion correctness. Check host modalities;
text/image access alone does not establish audio perception. Leave acting, voice
identity, sound balance and lip sync ungraded without an actual listening method.

## Audit decisions

The coordinator validates reports and audits a reproducible random sample of both
passes and failures, with explicit handling of uncertainty and novel/high-risk
content. Initially qualify on retained labeled examples. Choose a proportionate
sample for the batch; no fixed percentage guarantees reliability. Avoid making a
second complete review of every clip routine.

The sampler in `review_results.py` records selected report IDs and its seed; it does
not claim an audit occurred. The auditor opens actual media at independently chosen
frames/times, not only the worker's summary or screenshots. Record agreement,
discrepancy and evidence. Ask narrowly for missing evidence instead of repeating a
whole inspection. Use existing completion reporting instead of model-driven polling.

## Improve from observed weaknesses

A correctly caught generation defect means the checker worked. Route it under the
owner's existing policy; detecting captions does not authorize prevention research.
For a missed defect, false rejection or wasted checking step:

- Record the source evidence, decisions and specific rule/tool weakness.
- Make the smallest supported correction. Retain a passing counterexample and the
  failure; test held-out retained cases when available.
- Bump the skill version for changed review behavior. Pin active work to its version;
  never rewrite older reports to imply they used newer rules.
- Widen audits for the affected category, reusing unchanged evidence elsewhere.
  Broader quality standards and action authority belong to the owner.

Report actual accuracy/uncertainty, elapsed time and available native usage. Do not
invent missing prices, savings or a comparison baseline. Faster review does not
shorten rendering itself. Final reporting separates audited and unaudited scope,
remaining uncertainty, retained evidence and the next permitted action. Preserve
all original media, previous reviews and failed outcomes.
