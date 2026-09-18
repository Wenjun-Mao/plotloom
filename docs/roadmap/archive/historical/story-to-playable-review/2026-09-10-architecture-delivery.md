# Reviewer B — architecture boundaries and bounded delivery

> **Archive status (2026-09-18):** Historical/supporting record retained for context and evidence; it is not an active delivery plan or a completion claim. See [the roadmap entrypoint](../../../README.md).


Status: self-contained planning prompt; not dispatched. Copy this entire file
as the prompt. Source and supporting documents are published for GitHub-only
review as described below. Work independently of Reviewer A.

## Purpose

Challenge the technical roadmap from Plotloom's existing text-authoring workbench
to a small playable branching audiovisual story. Your report will help choose
safe, minimal implementation slices. The costly errors are rewriting working
domain code, introducing a production bypass, losing media provenance, repeating
paid/uncertain submissions, or building infrastructure without a usable result.

## Evidence binding and access

Discovery: https://github.com/Wenjun-Mao/plotloom, review branch `codex/m1b-alpha`.
Source anchor: [`9afbefd2f82a620d79b82cd6607571057f23a6c4`](https://github.com/Wenjun-Mao/plotloom/tree/9afbefd2f82a620d79b82cd6607571057f23a6c4).
Use that exact source tree, not the older `main`. The user authorized publication
of the source and packet to this repository. If source is unavailable to you,
state that and provide conditional design critique from this prompt; never
silently inspect another revision and treat it as this one.

The [proposed roadmap](../../superseded/2026-09-10-story-to-playable-alpha.md) and
[ADR 0026](../../../../adr/0026-story-to-playable-product-direction.md) are subsequent
committed documentation-only review drafts, NOT files claimed to exist in the
source baseline. Open them at the same packet revision as this prompt and report
that revision separately. Local `.env`, databases, media, complete LLM traces and private
canary/review packs are excluded. No credentials or private endpoint/IP is needed.

Useful exact-source paths if accessible:

- `docs/adr/0012-approved-storyboards-and-production-units.md`
- `docs/adr/0016-versioned-authoring-quality-gates-and-approval.md`
- `docs/adr/0023-bounded-delivery-and-evidence.md`
- `docs/adr/0024-pluggable-text-backends-and-independent-qualification.md`
- `docs/adr/0025-provider-readiness-and-versioned-admission.md`
- `src/plotloom/domain.py`, `media.py`, `media_jobs.py`, `artifacts.py`
- Relevant media/profile/Approval boundaries in `api.py`, `persistence.py`
- `src/plotloom/alpha_acceptance.py`, `frontend/src/pages/StoryboardPage.tsx`
- `docs/roadmap/archive/superseded/2026-09-02-capability-matrix.md`, `docs/roadmap/archive/superseded/2026-09-07-m1c-completion-plan.md`

Read targeted ownership paths, not the whole repository. Historical ADR context
may describe older behavior; implementation and dated receipts must be separated.
Narrative Forge and shuohao-skills inspired the product, but no V1 runtime or
third-party source ingestion is part of this assignment.

## Supplied current-state summary

Four canonical authoring stages, project lifecycle, revision/session drafts,
deterministic DAG, bounded correction, exact unit repair, immutable evidence,
atomic installation, DialogueCue/AudioPlan/entity states and Gate/Approval exist.
Explicit text adapter ID/version and frozen V3 snapshots preserve V1/V2 history.
Private HTTP/LAN/Tailscale and profile-scoped secrets are supported.

Retained verification reports 524 Python passes/9 historical-media skips, 115
frontend passes and 23 real-FastAPI browser journeys. A prior real text canary
worked; a later probe only checked connectivity. Formal independent text
qualification remains open: 9/9 runs across three stories, >=30/36 first-pass
stages, bounded attempts, three blinded reviews and no secret/unknown/partial
install failures. Independent runner support needs checking, not assuming.

Current media creation is intentionally hard-blocked at API/repository/worker
until ProductionSnapshot exists. Historical adapters/tasks do not establish
usable media production. ADR 0012 calls for approved immutable snapshots, ordered
contiguous production units within a scene, reference roles and artifact hashes.
Managed binary assets, rich candidate selection and playback remain to build.

## User decisions and proposed delivery

Story-first, cinematic realism, select/refine proposals with detailed editing.
Preserve future imported images. Early images can be generated in the development
conversation and imported, without impersonating Plotloom provider runs. Native
audio in first supported video pilot. In-app sequential preview, then playable
branching with end-of-node pause, last-frame hold and untimed choices.

Proposed sequence:

1. Q: narrowly finish independent text qualification; do not relabel old evidence.
2. P0: controlled import, immutable originals, revisioned role/reference selection,
   three keyframes and a clearly labelled still animatic that survives refresh.
   Can proceed on an existing reviewed board while Q remains explicitly open.
3. P1: one image integration using approved ProductionSnapshot, same artifact
   store/selection UX, explicit capabilities and retained task evidence.
4. P2: one image-to-video clip, short authoritative line and environmental audio;
   native audio quality inspected, downloaded output validated and playable.
5. P3: several clips in simple-cut sequential preview; measured playback durations
   distinct from authored time, no silent retiming or duplicated dialogue.
6. P4: derived frozen playback manifest; canonical graph/edge effects/joins,
   exactly-once choice effects, restart, complete versus incomplete preview.

Proposed amendment: pre-Approval visual exploration uses its own versioned brief
and immutable snapshot, producing candidates only. Production still requires
active storyboard Approval and explicit reviewed reference promotion. Existing
blanket media hard stop remains until that amendment is accepted and implemented.

Media profiles use explicit versioned adapters, not model-name heuristics. Unknown
submission is not failure eligible for blind replay. Download/ingest failure is
distinct from remote generation failure. Replacing selections makes dependents
stale without rewriting historical tasks. Shared-node media reuse must respect
incoming state, not merely match a shot ID.

## Requested review

Provide prioritized findings with concrete failure scenarios, affected ownership
layer, source evidence (if inspected), and smallest durable remedy. In particular:

- Is the exploration/production split sound and small enough? What cannot be
  deferred without making P0 a throwaway or bypassing Approval?
- Trace authored intent → visual proposal → reference binding → snapshot →
  provider request → validated artifact → selection → playback. Find missing
  owners, concurrency guards, hash/version boundaries and stale semantics.
- Falsify restart/cancel/unknown-outcome and output-ingest safety. Address local
  upload/download security, secrets, originals, rights metadata and file cleanup.
- Examine native audio, provider duration mismatch, reference-mode restrictions
  and optional provider prompt expansion without contaminating canonical truth.
- Test canonical branch/state/join equivalence and manifest pinning. What happens
  when two incoming paths require visibly different state in a shared clip?
- Propose one bounded P0 implementation brief: observable outcome, exact scope,
  smallest useful tests, one real browser journey and stopping condition.
- Identify what can be removed/deferred and what would require changing an
  existing accepted contract. Do not propose a new framework without a concrete
  requirement the existing seams cannot satisfy.

Keep direct observations, supplied claims, inferences and hypotheses distinct.
List the commit/files actually inspected and material unavailable evidence. For
current provider/API assertions use primary endpoint docs; otherwise label them
unverified. No code edits, service calls, paid generations or acceptance claims.

One owner/focused checks/stable-candidate review is preferred. There was severe
past cost from repeated large contexts, redundant agents and test/review loops;
more instrumentation is not an outcome. End with ranked Use/Test/Park candidates
and cheapest sufficient verification, not an exhaustive speculative task tree.
