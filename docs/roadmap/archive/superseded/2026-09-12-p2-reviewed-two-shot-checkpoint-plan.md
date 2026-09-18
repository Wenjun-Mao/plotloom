# P2: reviewed two-shot audiovisual checkpoint

> **Archive status (2026-09-18):** Superseded historical plan; unresolved items remain unresolved and this file is not an active delivery plan. See [the current tracker](../../2026-09-17-playable-mvp-milestones.md) and [roadmap entrypoint](../../README.md).


Revision 1 — **Approved by the user in the director task; ready for bounded Relay delivery**.
Baseline: clean `main` at `704c5fd62f6db707ee6860e069fe65903b933dc0`.
This is a bounded continuation of [the P2 plan](2026-09-12-p2-wan-audiovisual-pilot-plan.md),
not a replacement of its historical approval or the one-attempt pricing waiver.
User approval authorizes execution within the limits below; each Relay assignment
must state its narrower source and live-call authority explicitly.

## Outcome

Move from technically playable video to two reviewed adjoining shots that play
in order inside Plotloom, survive refresh/restart, and retain exact input,
candidate, review and selection lineage. Close single-clip acceptance separately
from adjoining-shot acceptance. A failed or unreviewable clip is an honest
checkpoint result, not permission to relax the gate.

Current evidence: one real ingested clip with H.264/AAC, measured 5.038005 seconds
and 1048 × 878 pixels; browser playback is proven, audiovisual quality is not.
See [the live receipt](../../../verification/2026-09-12-p2-waived-rate-video-attempt.md).
Shared ledger is 10/100 requested seconds reserved. The historical unknown job
remains unknown and must never be replayed, reconciled speculatively or refunded.

## Scope and non-goals

Use the existing pilot, cinematic-realism character/reference lineage, video
contracts, Atlas Wan adapter and managed assets. Review the existing result
before new spending. Repair concrete defects in review/selection, measured-media
presentation, persistence or simple ordered playback when needed for this journey.
Reuse current UI and contracts; do not create a parallel review framework.

No new provider/model, Grok, TTS, voice cloning, audio replacement/mixing,
transcoding pipeline, timeline editor, full-scene production, branching player,
authentication/deployment changes, broad refactor or V1 runtime access. P3 and
combined Alpha qualification remain separate milestones.

## Consequential choices proposed for approval

- Director handles routine technical and attributed Codex creative review. Assess
  against the frozen intended action/cue and approved identity, not a new story.
  No invented human review. Passing engineering checks never auto-creates Approval.
- Permit pilot-only explicit candidate review/selection after real review passes.
  Any necessary pilot input refinement must preserve story meaning and use normal
  revision/Approval boundaries, with the actual reviewer recorded. No database
  patching or transfer of historical Approval to edited content.
- Permit at most **two new 5-second, 720p, native-audio Wan requests**: one targeted
  correction of the first clip if needed, and one adjoining clip. If no correction
  is needed, make only the adjoining request. No spare-budget retries or third call.
- Extend the exact-dollar-rate waiver only to these two potential requests. The
  prior waiver is exhausted; this extension requires approval of this revision.
  Actual dollar cost remains unconfirmed. The shared 100-second cap stays intact;
  this checkpoint stops at at most 20 total reserved seconds from the 10-second
  baseline. Enforce the checkpoint allowance before dispatch alongside the existing
  durable ledger; a prose limit alone is not an enforcement mechanism.
- Record requested resolution separately from actual pixels and source aspect.
  Investigate 1048 × 878 using existing input/output metadata and authoritative
  provider evidence only as needed. Do not assume a preset promises exact raster
  dimensions, silently crop/stretch, or generate a new clip to diagnose this.
  Unproven preset conformity stays explicitly unverified; a creative pass cannot
  be presented as resolution-contract qualification.

## Checkpoints

### A. Review the existing clip without spending

Verify source/output hashes, frozen intent and reference lineage. Review the full
clip at normal speed and relevant frames, not only the retained screenshot.
Check same-person identity, temporal face/anatomy stability, intended simple
action, framing, continuity and visible defects. Inspect audio through genuinely
audio-capable tooling: exact cue/language/speaker, intelligibility, lip sync,
ambience and unwanted music. Transcription alone is insufficient for voice,
sound quality or synchronization; waveform/track presence is not listening.

Record pass/fail/unassessed per dimension with time-localized evidence. If tools
cannot assess audio, retain a local review pack and request only the missing
audio assessment. Continue offline product fixes, but do not generate an adjoining
clip while first-clip usability is unresolved. No general audio-tooling project.

### B. Complete the bounded product journey

Fix only diagnosed defects preventing review, explicit selection, ordered
two-clip playback or durable reopening. Ordered playback needs play/pause, seek,
repeat and final-frame hold; preserve native aspect and show missing/stale media
clearly. Never concatenate canonical timing by silently trimming/stretching media.
Use a real FastAPI/file-SQLite journey with retained or synthetic fixtures for
offline plumbing; synthetic clips do not count as creative evidence.

If the first clip has one concrete correctable creative defect, director reviews
one revised frozen prompt/input and permits the single correction slot. A repeated
failure of that class, or a defect requiring recasting/story change, stops live work.
After first-clip usability passes, review an existing suitable adjoining keyframe;
if absent, permit one original and at most one refinement through the project
Codex image-specialist workflow with the approved identity reference. No external
image API spending; exclude known defective reference candidates. If those images
do not pass, stop before video. Keep action/cue consistent with the pilot story.

Generate the adjoining clip once. Review the cut at normal speed, muted and
audio-only for identity, screen direction, state/action continuity, dialogue
ordering and sound discontinuity. A deliberately silent second beat may pass
continuity but cannot prove cross-shot voice consistency; report that limit.

### C. Verify, accept and publish

One scoped independent review of the stable candidate, addressed findings, and
proportional regression verification. Demonstrate reviewed selections and ordered
playback after same-storage process restart, seek/repeat/final hold, staleness and
revocation behavior, and no duplicate request or partial adoption. Preserve parent
evidence and the historical unknown job.

Focused tests during edits; on stable product changes run locked Python tests,
frontend unit/typecheck/build/static freshness, real-server browser tests and
wheel/installed-wheel smoke as applicable. Receipt-only work needs diff/hash and
artifact checks, not a repeated full product suite. Record exact commands and gaps.

Publish a secret-free receipt and update the capability matrix/P2 status without
rewriting prior evidence. Keep clips and full review pack locally; GitHub gets
safe hashes, review findings and supporting stills. Record technical, creative,
audio, resolution and cross-shot results separately. Merge/push verified work to
main without force; report CI separately. Archive completed coordinator tasks;
preserve data, `.env` and Relay history.

## Execution authority after approval

Director may proceed A → B → C, sequence bounded Relay assignments, review results,
fix routine scoped regressions and complete delivery without asking at every step.
Use the existing clean main checkout and one Terra-high source owner at a time;
no unnecessary worktrees or unattended child agents. One attended, scoped reviewer
may support final acceptance. Follow current Relay readiness and completion rules;
do not reset registrations or bypass a branch/ownership refusal. Material assignment
changes require director review; never silently expand a frozen assignment.

Live work uses only the existing authoritative pilot database/artifact root and
shared ledger identified in the receipt. Verify baseline before spend, process-only
runtime enablement, credentials in memory, one upload/submit per admitted attempt,
no POST retry/fallback/replay. Known-ID bounded polling/retrieval may continue
without another generation, preserving pending state on deadline. Stop owned
services and checkpoint on interruption; resume by stored job identity, not resubmit.

## Escalation and exit

Ask the user only for: unavailable genuine audio assessment; material story,
identity or aesthetic tradeoff; additional paid attempts beyond the approved
envelope; provider/model or security-boundary change; or inability to preserve
existing work. Unknown submission stops new paid work until disposition is reviewed;
never release its reservation on inference. No spending to compensate for tooling
gaps. A failed gate is reported, not waived by the coordinator.

Success: two usable clips with attributed review, explicit current selections,
ordered local playback and durable lineage; no blocking recast/action/dialogue or
sound contradiction. Single-clip-only success and blocked audio review remain
distinct partial outcomes. This qualifies a bounded two-shot pilot, not universal
voice/identity fidelity or P3 branching playback.

Delivery includes baseline/final commit, tests, ledger delta, known limitations,
and available usage measurements (unavailable if not exposed). Next milestone
after acceptance: plan P3 short sequential scene preview, then pause-and-choose
branching playback; neither is authorized by this plan.
