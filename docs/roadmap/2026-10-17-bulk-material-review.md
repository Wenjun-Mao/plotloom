# Whole-pack gallery approval

Status: approved for implementation and the consolidated delivery permissions
below, 2026-10-17. Actual material approval remains creator-owned; no live creative
approval or generation is authorized by this implementation approval.

Owner clarification, 2026-10-18: all existing project data is development testing
material. If a current-contract implementation makes identified projects
incompatible, remove those affected projects completely without backup/recovery;
do not introduce compatibility or migration machinery solely to retain them.
Compatible projects may remain. The manager owns exact live targets and safe
quiescence; active workers and UNKNOWN dispatch still cannot be silently settled.
This later instruction supersedes preservation assumptions below where they
conflict. The bounded JSON design currently requires no incompatible reset.

## Outcome and agreed scope

Replace repetitive normal-case input in the final autopilot material-review
dialog with one explicit whole-pack approval. The creator reviews the gallery,
opens details for exceptions, and can approve a good pack without typing or
clicking through every frame. The current example has five reference sets and
42 first frames; those counts are an acceptance fixture, not product limits.

Owner decision: **whole pack first**. An unresolved problem blocks the final
handoff; do not add partial pack approval or a new repair/generation workflow.
The owner also wants foreseeable delivery permissions bundled into one plan
approval, so routine execution can continue without milestone approval delays.

Source baseline: retained checkout `/Users/wjmao/.codex/worktrees/b30f/plotloom`,
`f2858efa1b93854fe299cd97e2c839f5c763c6ed`. Installation is
`/Users/wjmao/projects/HU/plotloom`. The current finished project
`a99d5422-61fd-4768-89f4-118e82bbed75` and its outputs must remain intact and
unapproved by the agent. Previous Art-navigation and material-recovery fixes are
complete and are not reopened by this work. Narrative Forge V1 is out of scope.

## Root cause and approach

This is an intentional but burdensome review contract, not just a missing button.
`MaterialReview.tsx` initializes blank frame drafts; `completeFrame` requires
intent, sources, compatibility and per-character prose. Backend
`FrameObservation`, `VisualIntentInput` and `SamePersonReviewItem` independently
require those inputs. `record_handoff` atomically validates the exact pack and
creates the facts consumed by video eligibility. Removing stars or populating
“looks good” would misrepresent authored evidence and leave the contract wrong.

| Approach | Trade-off | Decision |
| --- | --- | --- |
| Explicit whole-pack structured approval, details for exceptions | One final action for the good case; requires a truthful new approval basis | Recommended |
| One Pass action per frame, then submit pack | Removes prose but keeps 42 normal-case clicks | Not selected |
| Auto-fill existing observation prose | Claims observations the creator did not write | Reject |

Keep existing currentness, identity-uncertainty and atomicity protections. Amend
the approval contract rather than bypassing it for this caller. Record the new
decision in a concise ADR linked to [ADR 0162](../adr/0162-pre-video-autopilot-authority.md),
[ADR 0146](../adr/0146-explicit-unassessable-identity-review.md) and
[ADR 0101](../adr/0101-accessible-creator-confirmations.md); update the
[autopilot contract](../creative-workflow/pre-video-autopilot-contract.md).
Those current contracts remain authoritative until the approved change lands.

## Proposed experience

1. Open a compact gallery of the exact current reference sets and first frames,
   grouped by scene with readable shot labels. Preserve the full story/routes,
   script, original/cropped image distinction, generation disclosures and
   cross-shot lineage as accessible details. Every supplementary reference used
   for identity comparison remains visible, not just the primary image.
2. Show intent/source context already available from the exact saved storyboard
   or existing reviewed intent. Label it as saved/suggested context endorsed by
   this action, not newly authored observation. Permit intentional edits in
   details; do not require retyping unchanged context.
3. Each frame can be flagged for visual incompatibility, identity mismatch or
   inability to assess identity. Show the problem count and a direct way to open
   affected details. Only exceptions require explanatory input.
4. One final action, provisionally **“确认全部素材并继续”**, explicitly confirms
   the displayed reference use, frame suitability for the displayed intent and
   each depicted character's identity/state, except separately recorded
   uncertainties. Show exact scope/counts and consequences beside the button.
   No normal-case per-frame checkbox, compulsory essay, extra confirmation
   round, or scroll-tracking gate. Nothing is human-approved merely by opening
   the dialog, loading an image or leaving a default untouched.
5. A visual/identity failure or unresolved flag blocks the entire handoff.
   `unassessable` requires its own nonblank reason and separate hold/authorize
   choice. Explicitly authorized uncertainty can proceed under ADR 0146 but
   remains unassessable, never PASS; the bulk action cannot choose it implicitly.
6. Closing/cancelling creates no approval. The existing final handoff only enables
   subsequent manual video preparation; it never creates a video preview/job or
   sends generation. Do not add partial approval, draft autosave or automatic
   repair to this slice.

Detailed authoring remains available where needed. Do not redesign the separate
manual per-shot workbench. If known missing pixels or unavailable current-bundle
reads prevent review, show a retryable blocking state; do not silently approve
unseen substitute material or infer observability from shot labels/model prose.

## Contract and persistence boundaries

- Introduce a versioned whole-pack request/receipt basis, expected to use a v3
  handoff receipt. Bind explicit structured assertions to the exact project/run,
  run revision, bundle hash, reference decision/asset set, ordered frames and
  visible-character targets. Recompute and compare the entire scope on submit;
  the button never approves whatever happens to be latest at execution time.
- Persist per-target structured judgments as **bulk-confirmed human judgments**,
  not detailed authored observations. Store the versioned assertion wording/basis,
  exception decisions and unchanged optional comments so readback explains what
  was confirmed. Do not fabricate identity/state/compatibility notes or a name.
- The bounded source probe found existing receipt/comparison JSON sufficient;
  no SQL migration is planned. Existing SQL note columns can represent absence
  with empty strings only for the new typed basis. Shared writers/readers must
  require exact receipt linkage and expose that basis in projections. An empty
  note or discriminator alone is never authority. Reject missing, forged,
  cross-project or mismatched receipt/binding/review links.
- Keep ordinary manual request models' nonblank authored-note requirements.
  Add the bulk variant to the narrowly typed persisted/read contract and trusted
  handoff owner, not a global optional-fields loophole. Shared eligibility must
  validate the new basis consistently; do not make only the UI or video entrance
  tolerate it. Separate receipt-shape/link validation from eligibility/currentness
  to avoid recursive receipt -> review -> receipt checks.
- Represent unchanged intent as a source-bound endorsed storyboard/current-intent
  basis. Trusted code resolves exact saved revision/shot/source IDs and validates
  them on read; an edit is actual creator input. The current review projection
  does not expose a human binding's complete saved intent/source references:
  extend its typed bundle/read contract to include that exact intent ID,
  revision, hash and displayed context, bound into the confirmation hash. Do not
  use an unbound suggestion appendix or rewrite retained bundle bytes. Preserve
  an existing reviewed intent and exact cross-shot target-use lineage by default.
  Ordinary shared images retain their one-current-intent rule; conflicting intents require
  explicit resolution, not last-write-wins or overwritten source authority.
- Preserve the atomic lifecycle transaction: preflight every reference, intent,
  frame and exception before writing any approval, intent, binding or review.
  Then append one immutable receipt and validate final admission. Failures roll
  back the whole pack. Keep exact geometry, source lineage, latest-review and
  reference-currentness guards, including character-free frames and multi-person
  frames. A later FAIL/HOLD cannot fall back to an older PASS.
- Preserve existing supported detailed submissions and immutable v1/v2 receipts
  through their existing readers; do not rewrite history or build a general
  compatibility service. The new UI must distinguish bulk confirmation from
  detailed evidence on readback. Frozen jobs, requests, packages and generation
  receipts remain unchanged.
- Project changes, stale bundle/CAS, read-only admission or lost currentness
  invalidate pending consent. Use the existing synchronous in-flight guard and
  fresh durable observation after an uncertain acknowledgement; never replay
  the handoff blindly. Preserve focus, keyboard navigation and safe cancellation.

## Ordered delivery and verification

One source owner works serially in the retained checkout. Bounded independent
read-only review is useful for the approval/provenance boundary; no parallel
writers. Use the repository's model-selection guidance at native dispatch.

1. **Lock the contract.** Add the linked ADR and precise request, stored-basis and
   read-validation design. Verify no recursive authority dependency and enumerate
   all downstream readers before changing acceptance. Recheck the actual diff
   and current project-preservation needs; choose the smallest cohesive modules.
2. **Implement shared facts and atomic handoff.** Extend typed contracts, source-
   bound intent planning, writers, readback and admission together. Keep old
   detailed inputs strict. Prove the good bulk path and hostile/partial inputs
   with focused backend regressions before building on it.
3. **Implement the gallery and exception flow.** Split cohesive UI/state helpers
   as needed, prefill source context truthfully, show blockers, and wire the one
   final action. Add focused frontend and browser coverage; refresh checked
   static assets using established build tooling.
4. **Exercise realistic boundaries early.** Before the final release gate, test a
   current-shaped 42-frame/5-reference pack with genuine geometry provenance,
   machine provisional and human-bound frames, existing/cross-shot intent reuse,
   supplementary references, multiple/no visible characters, uncertainty, flags,
   stale scopes, project switches, read-only state, broken reads and lost ack.
   Use isolated owned fixtures/temporary projects, not live creative approvals.
5. **Review and qualify a stable candidate.** Obtain one independent source review;
   fix concrete in-scope findings with focused reruns. During development use
   `scripts/verify.py focused`, then reviewed module unions for `story-authoring`,
   `creative-production` and `media-lifecycle` at appropriate depth (`--show`
   first). Extend `scripts/testing/module-ownership.json` for new tests. Do not
   run every module as a disguised full gate after each edit. Because this changes
   the public approval/persisted-read contract, one stable final
   `uv run --locked --no-sync python scripts/verify.py full` is required by
   `AGENTS.md`. Reuse unchanged evidence after narrow corrections; repeat full
   only with a documented invalidation reason. Keep hosted CI and human product
   acceptance separate from local qualification.
6. **Deliver and activate under the approval below.** Commit/push verified scoped
   changes normally after checking remote divergence, then perform the existing
   preserving same-installation activation when safely idle. Verify readiness,
   exact finished-pack readback and UI availability without submitting a live
   material approval or starting generation. Record revision, checks, preservation
   evidence and any remaining gap; stop with the new flow available to the owner.

Primary touchpoints: `frontend/src/features/autopilot/MaterialReview.tsx`,
`contracts.ts` and relevant same-person presentation/types; backend
`autopilot_handoff_contracts.py`, `same_person_review_contracts.py`,
`persistence/project/autopilot_review_bundle.py` and its typed/read validators,
`autopilot_handoff.py`, `handoff_visual_intents.py`,
`media_keyframes.py`, `media_same_person_reviews.py`, and shared
`project_storage/handoff_validation.py` / `autopilot_validation.py`. Review actual
consumer dependencies, not just these paths. Existing tests include
`test_autopilot_handoff.py`, `test_autopilot_creator_confirmation.py`,
`test_same_person_review_contract.py`, `test_cross_shot_handoff.py`,
`frontend/tests/autopilot-review.test.ts` and
`frontend/e2e/autopilot-review.spec.ts`.

Acceptance: the good pack needs no typing/per-frame approval clicks; all reference
and frame targets are exactly covered; one explicit final action commits truthful
structured judgments; any unresolved problem yields zero partial approvals;
uncertainty remains explicit; stale/forged/incomplete input grants no eligibility;
manual detailed review and existing receipts still work; confirmation creates no
video work; the current completed draft and unrelated UNKNOWN jobs remain intact.

## Consolidated execution authorization granted with plan approval

The owner's approval authorizes the following end-to-end work, without
separate milestone approvals:

- Scoped implementation, ADR/contract/document updates, generated static assets,
  fixture changes, routine root-cause corrections and narrowly related refactors
  needed to meet the acceptance criteria. Engineering names/shape remain the
  implementer's decision within the agreed contract; material pivots do not.
- Bounded subagent work: implementation can transfer serially to a delegated
  source owner, with only one writer at a time; independent review/verification
  stays read-only. Include focused/module checks and the single required stable
  final gate, plus
  non-generative tests against isolated temporary test data and normal cleanup.
- Normal scoped commits and push to `origin/main` under repository rules, with
  remote divergence checks, no force-push and no bypass of failed gates.
- Existing-installation preserving upgrade, frontend activation and service
  restart at `/Users/wjmao/projects/HU/plotloom`, only after positive evidence
  that workers/validators/queues and relevant writes are idle. Use existing
  configuration/credentials; do not print or change them. Never cancel a new
  generation merely to deploy. If busy, leave the healthy runtime in place and
  finish source/qualification work while awaiting a safe activation opportunity.
- Read-only pre/post-activation verification of the finished project, all retained
  output identities/hashes and unresolved job reservations. Do not navigate,
  submit or force-refresh the creator's open Safari form. Account for a possibly
  open old-client review; a stale submission must fail safely without being
  reinterpreted as bulk consent. Surface any required user-controlled reopen.
- Planned recovery from an in-scope failed activation: restore a known-qualified
  reader-capable build without deleting or rewriting creative data. After a v3
  receipt exists, do not blindly downgrade to code unable to read it or remove
  that receipt to enable rollback. Establish this reader boundary before rollout.

Not covered: approving real materials on the creator's behalf; any new image/video
generation or provider/cost change; deleting/resetting/archiving user projects or
evidence; settling UNKNOWN dispatch; a SQL migration or expanded historical
compatibility system; partial pack approval; unrelated features; unsafe restart,
forced git recovery or broad cleanup. If an uncovered action or material
scope/risk change is genuinely necessary, preserve evidence, proceed with other
covered work where possible, and request a decision rather than assume consent.

Stopping condition: qualified, pushed and safely activated whole-pack review is
available, with actual creative approval still owned by the user. If native
permissions, unsafe activity or an uncovered material blocker prevent that final
step, leave the running installation/data safe and report the exact remaining
action. The explicit implementation approval grants these bounded permissions;
the earlier planning request alone did not.

## Implementation checkpoint · 2026-10-18

Source candidate implements [ADR 0191](../adr/0191-whole-pack-human-material-confirmation.md):
typed v3 bulk judgments, exact saved intent projection and source endorsement,
shared receipt-bound admission, a compact gallery with exception details, and
one explicit final whole-pack action. Canonical source text has its own exact
source-owned type; intentional author edits retain existing manual bounds.
Missing current or retained-original image pixels block the final action.
No SQL layout transition, incompatible-project reset, live approval, generation
or UNKNOWN settlement was required or performed by the implementation worker.

Focused evidence includes 47 earlier detailed backend regressions, current
source-bound/cross-shot selection (22 pytest), expanded current bulk API/hostile
input/long-source/reopen cases (20 pytest), six bulk frontend cases, and 18
browser cases including the 42-frame/five-reference one-action fixture and lost
acknowledgment. The current-shaped backend pack uses genuine validator/geometry
provenance, multiple/no visible characters, mixed human/provisional bindings,
and separate uncertainty authorization; its final-source rerun passed (one case,
108.17 seconds). Four current detailed/v1/v2 snapshot/recovery/API regression
cases also passed. Independent delta review closed the long-canonical-source
finding and reported no further production defects. The manager's isolated
read-only real-project admission passed on the same frozen source: current v2
review, five reference sets, 42 frames and 42 saved intent contexts. Compatible
data required no reset.
These are technical fixture checks, not creative acceptance.

The reviewed three-module contract union was expanded with `--show` and ownership
updated. Its broad run loaded the earlier source before the independent-review
source-type correction, so the manager directed its exact owned process group
to stop: interrupted exit 130, not a module pass. The native ownership preflight
and then-current type check passed before interruption. Do not restart that
invalidated broad run; the manager owns one stable final full gate after focused
corrections, independent delta review and read-only real-layout admission.
Commit, push, activation and final release evidence remain manager-owned.
