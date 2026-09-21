# ADR 0071: Character-stage image review

Status: Accepted, 2026-09-20.

## Context

F2B already stores cast-owned exploratory reference proposals, their frozen
requests, delivery candidates, explicit reference decisions and immutable
managed assets. Its authoring panel intentionally combines preparation,
handoff, refresh and selection controls with review. That makes image
comparison difficult, although no new persistence or generation contract is
needed.

## Decision

The original decision added a separate GET-only gallery. Review showed it
separated readable images from the decisions a creator came to make. Replace it
with the focused `stage=characters` workspace surface: existing F2A cast text
review followed by the image-first F2B review. It composes the existing
accepted-cast, character-reference decision, proposal/delivery and managed-asset
owners directly. Accepted cast supplies the admitted subject list; decisions
supply the selected identity reference; proposals and deliveries supply candidate
state and refinement parent; managed assets supply bytes. It needs no Story
Bible, script or storyboard and persists no presentation state or projection.

The Chinese presentation marks selected-current, merely-current candidate,
historical/stale, missing and failed evidence separately. It exposes a frozen
direction only when the stored proposal's frozen snapshot actually contains it.
IDs, hashes and provenance remain in separate collapsed technical details.
Ordinary viewing performs only reads. Explicit controls beside the images retain
the existing selection CAS/reviewer/notes request and manual proposal prepare,
copy, refresh and cancel lifecycle. Preparation is only a manual specialist
handoff, not ImageGen dispatch. Reopened or stale cast retains evidence but
disables selection, refinement and preparation.

## Consequences and guardrails

- A stale or reopened cast is presented as stale evidence rather than silently
  promoted to current; its retained candidates and selections do not become
  usable merely by viewing them.
- Missing managed assets remain visible as missing evidence and are never
  replaced with a substitute image.
- A proposal's currentness and each delivery state remain distinct; a current
  proposal is not a selection, and a delivered output is not creative approval.
- Retire the standalone `?view=character-reference-review` destination, its
  duplicate creator-stage navigation and `CastReferenceStudiesPanel`. Reuse its
  image/lineage/status presentation with CastPanel/API owners. Story, Art,
  screenplay, storyboard and Play remain independently owned.

## Acceptance correction — 2026-09-20

The initial gallery presentation did not fully preserve those owners at the
image boundary. A current decision is now the exclusive hero owner: when its
primary asset record is absent or its image cannot be read, the hero states
that selected reference as unavailable and does not substitute a current or
historical candidate. Alternatives remain visible only in their own comparison
cards.

One error-aware asset presentation owns absent metadata and browser HTTP/decode
failure for selected, candidate, complementary, historical, and lineage-parent
images. Its failure state is keyed by project, subject, and asset identity, so
an old failure cannot carry into another subject or project. Gallery fetches
are abortable and invalidate their request owner on unmount and project change.

Refinement lineage is now a recognizable parent card with its image, role, and
focusable link to the parent candidate; unavailable or missing parent evidence
remains explicitly unavailable. These are presentation-only corrections: they
do not change the canonical decision, proposal, delivery, or managed-asset
owners. In the integrated Characters stage, ordinary viewing remains GET-only;
only the explicit decision and handoff controls write through their existing
owners.

## Cast-session currentness amendment — 2026-09-20

The Characters workspace, rather than either sibling panel, owns one monotonic
cast session. Cast accept, reopen, and save invalidate that session before their
requests are dispatched; while such a transition is pending, retained image
evidence stays visible but every image mutation is disabled. The resulting cast
state then admits the gallery and triggers a guarded read refresh for current
directions and decisions.

Every image mutation captures the project/cast/subject session and its own
operation owner before dispatch. Only that still-current operation may apply a
returned assignment or draft reset, report an error, clear busy state, or start
a refresh. Unmount, project change, subject switch, and cast-session invalidation
all reject late success and rejection effects, even when transport ignores abort.
This is React presentation currentness only: it changes no F2A/F2B API,
persistence, CAS, reviewer/notes, asset, or provider contract.

## Live session ownership correction — 2026-09-20

The preceding amendment described the intended boundary but its first evidence
did not prove it. A gallery refresh compared its captured render's `castSession`
with the same captured expected value, while its read owner changed only on a
project change. A read begun before a cast transition could therefore still
publish old directions/decisions or an old error after a newer same-character
revision had settled. `SubjectGallery` was keyed only by subject ID, so the
same character retained a prior session's busy flag, drafts, parent choice, and
assignment area after reopen/save.

`CharactersPage` now owns a live, monotonic session reference. Accept, reopen,
and save replace that reference before dispatch; the rendered identity also
tracks the resulting cast status/revision/hash. Initial gallery reads, session
refreshes, and action-triggered refreshes all acquire a new read owner and may
commit only if both that owner and the live session still match. A subject gallery
is keyed by cast session plus subject, so a same-subject transition deliberately
creates fresh local controls while the prior mounted operation is refused.

Focused deferred tests hold a refresh through reopen/save, settle the newer
accepted same-character revision, then release old success and rejection; neither
may replace current evidence or show an error. A second deferred test proves a
pending prepare cannot strand controls after reopen/save, old local drafts are
absent, and the fresh control dispatches. A symmetric held selection rejection
after reopen/save cannot surface an old action error. A production-browser proof
exercises cast accept, reopen, and save against the FastAPI/file-SQLite fixture
and checks the gallery's r1 → read-only reopened → editable r2 sequence. These
guardrails remain presentation-only and preserve the existing F2A/F2B contracts.

## Characters workspace usability amendment — 2026-09-20

The integrated surface still exposed its implementation hierarchy: the global
shell repeated stages 01–05 in a context rail, always-open inspector data
consumed working width, accepted cast text was reduced to a hash and reopen
control, and one mixed image-action form combined a selection decision with a
future refinement request. These were presentation defects, not missing owners
or lifecycle guards.

The sidebar remains the one primary stage navigation. Project context and
inspector status remain reachable in a closed, keyboard-accessible “查看技术详情”
disclosure. The accepted cast renders its retained author text first, with
“编辑角色设定” as the explicit existing reopen action and a separate “创建新角色
提案” action that only prepares its existing manual task. Image review separates
“选用这张图” (reviewer, reason, and existing CAS selection) from “基于这张图
调整” (recognizable parent thumbnail and direction). Its creation continues to
prepare only a manual task; copy, refresh, and cancel remain separate actions.
Frozen directions, copied task text, IDs, hashes, and delivery provenance stay
available only through closed details.

This changes no F2A/F2B API, persistence, provider, generation, selection,
reviewer/notes, asset, or cast-session ownership contract. The session guards
remain the authority for all reads and mutations.
