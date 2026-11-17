# Video-checking skill

## Current status

Approved: build the manually invoked skill proposed in this chat, use GPT-6.1
Terra/high workers, audit samples, and improve demonstrated review weaknesses.
The existing story-generation goal remains paused. No new provider media, service
changes, automatic retry, CI, or push is part of this assignment.

Delivered locally: manually invoked `video-checking` v0.1.1, linked into the
personal skills directory. Implementation and scoped qualification are complete;
the pilot does not establish population accuracy, dollar savings or perceived
audio quality. [ADR 0238](../adr/0238-manual-video-checking-skill.md) records the
optional workflow boundary.

Smallest observable outcome: a Terra/high worker uses the new skill on retained
source-bound clips and produces evidence-backed decisions; repeat preparation
reuses valid derivatives, and stale inputs invalidate that reuse. An independent
audit checks actual media rather than the worker's summary alone.

| Claim | Required evidence | Fresh media | Status |
| --- | --- | --- | --- |
| Reusable manual skill | Concise instructions, explicit-only UI metadata, source/decision contracts | None | Delivered v0.1.1 |
| Tools avoid repeated work | Content-bound cache, reused technical/ASR evidence, meaningful stale-input tests | Retained media and deterministic test fixtures | Passed: cache reuse and 17 focused tests |
| Terra/high can perform review | Blinded retained pass/fail/uncertainty cases, actual image-view trace and validated reports | None | Six of six expected decisions; small curated pilot |
| Auditing and improvement work | Independent actual-frame sample, discrepancy assessment, narrow changes only if demonstrated | None | Random pass/reject audit agreed; uncertainty handled; five validator weaknesses corrected |
| Delivery is discoverable and reproducible | Personal skill install matches versioned source, validator/tests and bounded source review | None | Symlink resolved to source; installed skill validator passed; independent review closed |

Journey: supplied case -> local cached evidence -> one Terra/high primary review
-> compact report -> independent sample/uncertainty escalation. Fixture: six
retained clips copied into an isolated ignored pilot directory. Runtime: existing
Python/ffmpeg and local cached ASR only where needed. Work is finite: one primary
review per case, targeted follow-up for observed defects. Root owns final audit
and cleanup; no user-valued media is removed or overwritten.

Source: `tools/codex-skills/video-checking/`; personal discovery will point to this
same source under `~/.codex/skills/video-checking`. Tools remain self-contained and
do not import Plotloom or Narrative Forge runtimes. Review is optional and scoped
to explicit invocation, not a new product-wide generation gate.

## Delivery boundary

Cost and speed benefits require measurement. Record actual pilot elapsed time and
available native usage; do not invent prices or a comparison baseline. Existing
blind ASR supports lexical review, not perceived voice, performance or lip sync.
Future reference-frame, authoring-handoff and assembly skills are opportunities,
not extra deliverables in this first implementation.

## Pilot and qualification

Two GPT-6.1 Terra/high workers, without inherited chat history or prior quality
labels, inspected six retained source-bound cases using actual image-view tools.
Their v0.1.0 recommendations were two passes, three material failures and one
honest speech uncertainty, matching all six curator labels. The missing primary
ASR in the uncertainty fixture deliberately excludes later production listening
feedback; this does not change that clip's existing production selection.

Recorded worker casework intervals were 90.21 and 87.09 seconds for three cases
each, overlapping across workers. These measurements exclude initial briefing
and do not establish end-to-end speedup. Native usage/dollar measurements and a
comparable previous-review baseline were unavailable.

Seed `2026110802` selected C (pass), E (reject), and the uncertainty case F.
The coordinator chose independent per-shot native frames with seed `2026110803`,
opened those C/E images and all supplied C/E references, and agreed within the
sampled scope. F's absent recognition supports uncertainty, not omitted-speech
proof. No continuous playback, perceived listening or acting/lip-sync acceptance
is claimed.

Independent code review found five gaps: mutable bundle metadata, unbound detail
timestamps, stale original inputs, insufficient minimum evidence/decision checks,
and audio uncertainty incorrectly blocking a supported picture failure. v0.1.1
fixes these with targeted regression tests. Review rules did not tighten to fit
the generation defects. The independently reviewed candidate has no remaining
material code finding; three documentation mismatches were also corrected.

Final C/E reports explicitly reuse their original reviewers' unchanged observations
after matching case/video/evidence hashes and frame metadata. Current validation
and batch selection passed. Old reports remain v0.1.0; they were not rewritten to
pretend newer rules were used. New final-version preparation also demonstrated a
cache hit. Optional local blind-ASR transport was smoke-tested with an existing
cached CPU model, without download or source hints; recognition correctness and
equivalence to older decoding settings are not claimed.

Verification owner: the tools worker ran
`uv run --locked --no-sync python -m pytest tools/codex-skills/video-checking/tests/test_video_checking.py`
with **17 passing tests**. The project `verify.py focused --pytest` selector
refused this skill-local path because it only supports repository `tests/`;
the exact suite ran directly without modifying the runner. The installed source
passed skill-creator's `quick_validate.py`, and metadata explicitly disables
implicit invocation. No full product gate was needed for these self-contained
optional tools; no Plotloom API, provider, persistence or application runtime
changed. CI and push were not requested or run.

Retained local evidence: `.local/video-checking-pilot/` (234 MiB at qualification),
including blinded inputs, separate truth labels, frozen v0.1.0 skill, original
reviews, current C/E revalidation, tool smoke outputs and independent audit.
`audit/v0.1.0/audit.json` SHA-256:
`649d9168aa7c574735ac9c266bb6fb825340818a610ea508e6753451f740308a`.
Retain this finite evaluation evidence for owner review; root owns later scoped
cleanup. No original story media, prior production review or selection was changed.
