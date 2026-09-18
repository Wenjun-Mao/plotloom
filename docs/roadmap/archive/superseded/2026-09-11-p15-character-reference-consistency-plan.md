# P1.5 — Approved character references and cross-shot identity

> **Archive status (2026-09-18):** Superseded historical plan; unresolved items remain unresolved and this file is not an active delivery plan. See [the current tracker](../../2026-09-17-playable-mvp-milestones.md) and [roadmap entrypoint](../../README.md).


Status: **Approved revision 1**. The user approved implementation with “go”,
including the repository skill and replaceable specialist execution boundary.
No implementation or visual qualification is claimed by this document.

## Current checkpoint — user-directed consolidation

Implementation candidate `09f0397` is merged into local main for safekeeping and
a clean restart, not accepted as complete. The
[director review](../../../verification/2026-09-12-p15-director-review.md) owns the open
corrections: reviewer attribution, proposal-refinement UI, frozen-reference visual
comparison, and remaining entrypoint/story-first evidence. Preserve the existing
pilot; do not repeat generation merely to repair these gaps.

Correction candidate status is recorded separately in the
[P1.5 correction receipt](../../../verification/2026-09-12-p15-corrections.md). It is
implementation/verification evidence only: stable gates and independent director
review remain required, and it does not revise the retained pilot history or claim
milestone/Flow completion.

The user has suspended Flow development/recovery pending a replacement plugin.
The execution instructions below describe the original approved assignment;
do not redispatch it or repair its frozen lifecycle. Future delivery starts from
the consolidated main under a newly selected workflow. Video remains out of scope.

Baseline: clean, pushed `main` at
`05f73b63d078b4993f3b646b31ef09342f939012`. P1 manual original/refinement jobs and
usability corrections are integrated. See ADRs 0028 and 0029.

## Outcome and diagnosis

From a story with no images, propose a character's appearance, explicitly select
an approved reference set, and use that same identity in three genuinely distinct
shots. Compare the actual results before admitting any move into video.

Current code supplies textual `CharacterV2` anchors and, for refinement only, a
`parent_output` image. A `protagonist_reference` VisualIntent label is not a
versioned visual identity bound to a character ID. Consequently, successful jobs,
hash verification and same-shot refinement cannot establish cross-shot likeness.
Fix the reference/production-input contract, not a repeated name in the prompt.

Reuse managed raster storage, provenance, manual job exchange, selection and
preview infrastructure. Do not build a second asset platform or automation bridge.

## Approved decisions

### 1. A small, project-owned character reference set

- Bind each set to a stable canonical character ID, never merely a display name.
  One primary image and up to two optional complementary views; this is an
  initial product bound, not a claim about the image tool's maximum capacity.
- Allow managed imports and actual specialist-generated proposals. Preserve
  originals and provenance; missing rights information remains explicitly unknown.
- Selection creates an immutable, revision-checked reference decision containing
  exact asset hashes, character-context fingerprint, reviewer and notes. Replacing
  or revoking it preserves history. Candidates are not approved automatically.
- Describe stable face/build/recognizable features separately from costume,
  expression, pose, lighting and allowed story state. Images are identity guidance,
  not authority to copy their outfit, background or camera framing into every shot.
  A desired change to narrative facts goes through canonical editing/reapproval.
- Character rename alone must not accidentally transfer identity to another
  character. Deleted/changed relevant character context requires explicit review;
  unrelated character edits should not invalidate every reference in the project.

### 2. Story-first bootstrap without circular Approval

Introduce an explicit **character-reference proposal** job target alongside the
existing approved-shot target. It freezes the saved character context and visual
direction; no invented shot ID or fake storyboard Approval is allowed. This is
exploratory visual development, not an approved production keyframe.

Use the same Prepare → Copy → built-in ImageGen → Refresh mechanism. Offer a
proposal/refinement route and controlled import; an unapproved proposal may be
an explicitly labelled refinement input but never masquerades as an approved
identity reference. Refresh publishes candidates, not reference approvals.
Existing shot generation retains its storyboard Approval requirements.

### 3. Identity inputs travel with every applicable shot job

- Derive applicable cast from the shot's authoritative character membership, not
  the broader resolved-context union of scene members, speakers and entity states.
  Context-only/off-screen speakers must not silently become visible characters.
  Ambiguous authored depiction requires clarification in authoring, not inference
  by the image specialist or another hidden LLM call.
- New identity-aware original and refinement jobs freeze a role-mapped list of
  character IDs, reference-set revisions, asset hashes and actual reference bytes.
  Multi-character mappings must remain separate. Missing required references or
  excessive attachments produce actionable admission errors, never silent omission.
  Character-free shots require no identity set.
- `character_identity` and `parent_output` are distinct roles. The parent guides
  the requested edit; it cannot override approved identity. Canonical story state
  governs costume/injury/etc. Any unresolved conflict is surfaced before dispatch.
- Extend Prepare, package projection, copy instructions, complete-package
  verification, delivery ingestion and currentness together under a new version.
  The specialist must actually view/use the delivered references; a hash or claimed
  attachment alone is not proof of use or visual fidelity.

### 4. Honest applicability and review

- Freeze dependencies; reference replacement/revocation or relevant context change
  invalidates affected jobs and reviewed selections/previews. Unrelated references
  do not. Late delivery cannot silently become current or selectable.
- Keep existing snapshots, manifests and hashes readable and unchanged. Historic
  assets/previews are not retroactively labelled identity-reviewed. Existing P0
  exploration remains usable; a newly qualified cross-shot preview must explicitly
  meet the new reference and review requirements, with no legacy-job bypass.
- Provide side-by-side primary reference and shot candidates, clear dependency/
  stale status, and a recorded same-person review bound to exact images and
  reference revisions. This is a separate visual decision, not a replacement for
  storyboard Approval or a fabricated automatic face-recognition score.
- Full identity qualification requires reviewed results, not merely attached
  references. A different pose/expression/outfit can pass; a different face cannot.

## Bounded delivery

### Specialist execution boundary — agreed direction

Ship a repository-scoped `.agents/skills/plotloom-image-specialist/SKILL.md`
with the implementation. Keep it short and versioned with the job contract;
reuse existing tested delivery utilities rather than duplicating validation in
instructions. Do not create or modify a personal skill or user-level AGENTS.

- **Plotloom owns durable state:** frozen creative briefs, character references,
  assets, ingestion, applicability and review decisions. Task memory is never the
  authority for identity, retries, completion or approval.
- **The skill owns the operating procedure:** read/check the job version, view
  role-mapped references, use built-in ImageGen, preserve identity versus allowed
  state, and return truthful outputs/metadata to the designated delivery location.
  Missing tools or conflicting inputs are reported, not bypassed through an API.
  A skill does not grant ImageGen access. The specialist cannot approve its own
  result, alter canonical content or edit source code.
- **The task is replaceable:** default to a fresh task per job or small related
  batch; retain a task for an active refinement session when useful. A fresh
  task needs only this skill and the self-contained frozen job package, not the
  director's conversation history or a predecessor's hidden context.
- **Model choice is launch configuration:** keep model and reasoning effort out
  of the creative job contract and skill's required behavior. Terra remains the
  current default; Luna Medium/High suitability can be tested later against the
  same delivery and visual gates, without a new model-comparison milestone now.
  Record the actual executor model/effort when available; do not invent telemetry.
- **Development checkout is explicit:** allow a selected branch/worktree and
  record its exact commit and skill version/hash. Uncommitted skill/tool changes
  cannot serve as the reproducible acceptance candidate. Reject unsupported job
  versions rather than silently modifying the frozen job to fit the checkout.
- **Production uses approved main:** start from a clean, approved `main` revision
  and pin the code/skill used for the whole job. An update to main applies to later
  jobs, not in-flight execution. This may use a read-only pinned snapshot; the
  active job must not depend on a mutable branch name alone.
- **Data outlives checkouts:** exchange, assets and retained delivery evidence
  reside outside disposable worktrees. Resolve the explicitly configured exchange
  for this job, with existing confinement and project checks; never guess another
  checkout's database or `.env`. Worktree cleanup must not delete those assets.

This is a project skill and manual backend workflow, not a new orchestration
framework, automatic bridge or guarantee that every task host exposes ImageGen.
Keep backend request identity separate from observed executor provenance.

### Checkpoints

1. **Vertical slice:** record the implementation ADR, add reference decisions and
   proposal target, then prepare/import/select one character and generate one
   reference-conditioned shot through the real manual workflow. Include focused
   persistence/API/browser coverage. Do not spend successive checkpoints solely
   expanding validation machinery before attempting this visible outcome.
2. **Cross-shot slice:** complete role mapping, refinement, dependency invalidation
   and side-by-side review; generate the three-shot pilot, explicitly select results
   and replay a labelled still animatic. Preserve currentness across refresh/restart.
3. **Acceptance:** one independent Terra review after the candidate stabilizes,
   stable full gates, and a concise source-bound receipt. Reopen only concrete
   findings. No new benchmarking or orchestration framework.

### Regression evidence

Cover imported-original preservation, project/character isolation, optimistic
revision conflicts, proposal versus shot authority, missing references, two-character
role mapping, off-screen/character-free cases, original/refinement precedence,
tampered packages and bytes, stale/revoked/late delivery, history compatibility,
refresh/restart, and retention/delete guards. Use retained images for automated
tests; identify simulations honestly rather than claiming ImageGen execution.

On the stable candidate run the established locked Python, frontend unit/typecheck,
E2E typecheck, build/static freshness, real FastAPI browser, wheel/install gates.
Preserve scoped docs, generated static assets and a 1440×900 workflow screenshot.

Exercise a fresh specialist task with no previous conversation for at least one
of the three pilot shots, using only the project skill and frozen package. This
reuses the planned pilot rather than adding an extra image-generation batch.
Verify executor provenance and unsupported-version handling; demonstrate retained
delivery remains usable independently of the original specialist checkout. Do
not remove real user worktrees just to perform this test.

### Real visual exit test — before video

- One fictional protagonist, cinematic realism, three authored shots in one coherent
  moment: a close facial view, a materially different three-quarter/side view, and
  a wider action view. Preserve useful identity visibility; do not pass by repeating
  a composition, cropping the same image or hiding the face in every difficult view.
- Generate each shot through its own frozen job with the same approved references,
  not merely by editing the preceding shot. Exercise one targeted refinement if a
  mismatch needs correction. Keep all attempts and honest actual-tool provenance.
- Independently compare face structure, distinctive features and visible build;
  inspect pose, costume/state and shot intent separately. Record each shot's
  same-person judgment, discrepancies and reviewer. Acceptance: all three read as
  the approved person, with no unresolved identity or authored-state contradiction.
  A numerical proxy or file hash cannot substitute for viewing the images.
- Finish with selected, identity-reviewed shots in a persisted still preview;
  refresh and restart, then replace a reference and demonstrate that the old
  qualification becomes stale without erasing it.
- Limit the initial experiment to two proposal candidates, three original shots
  and at most two targeted additional generation requests. These are a planned
  operation bound, not enforced account billing limits. If unresolved, retain the
  result and reassess the reference/prompt contract before another batch; do not
  weaken review or reroll indefinitely.

This proves one-character cross-shot feasibility, not universal consistency or
multi-character visual qualification. Automated two-character mapping coverage is
required now; a live two-character scene remains a named follow-up before claiming
that capability. Still success does not qualify motion, voice or cross-cut audio.

## Non-goals and authority

No video, external image APIs, automatic specialist bridge, face recognition,
embeddings/LoRA/training, exhaustive asset libraries, identity aging/transformations,
cross-machine transport, V1 code, user-data resets or user-level AGENTS edits.
Text qualification Q stays explicitly separate and open.

Use one fresh implementation owner from the consolidated baseline;
do not restore retired Flow registrations or reuse historical assignments. Default
delegated model is Terra, with later specialist-model evaluation as above. Admit
`.agents/skills/plotloom-image-specialist` and required code/test/docs/migration/static
paths up front. Local commits and isolated development data only; merge/push needs
separate authority. Product data and `.env` remain untouched.

The director can make routine fixture selections and conduct development review;
in-product reference adoption remains an explicit creator/reviewer action. Escalate
changes to these boundaries, an unmet visual exit test after the bounded experiment,
or a need for new external services. Return observable results and limitations,
not just test counts. This revision authorizes a fresh implementation assignment;
it does not authorize main integration, push or video work.
