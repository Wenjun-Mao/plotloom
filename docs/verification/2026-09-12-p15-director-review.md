# P1.5 director review — acceptance withheld

Candidate: `09f0397` in `/Users/wjmao/.codex/worktrees/f6c8/plotloom`.
Scope: artifact/code review against approved P1.5 revision 1, plus the focused
image-job suite. No product repair, merge, push, Flow reset or acceptance performed.

## Subsequent user-authorized consolidation

The user subsequently instructed: save the work, merge to main, restart clean,
and do not develop or repair Flow while its replacement plugin is being built.
Candidate `09f0397` was fast-forwarded into local `main` as an **incomplete
checkpoint**, not product acceptance. The code references below now resolve in
the primary repository. Retired worktree paths are historical provenance only.

Next work starts from main and the required corrections below. Do not wait on,
resume, repair or reset the old Flow assignment. Its unresolved lifecycle is
preserved as historical evidence, not a gate that authorizes more plugin work.
No push or video work was authorized by this consolidation.

## Confirmed progress

- Candidate worktree was clean; implementation and browser corrections are committed.
- Independently ran `uv run --locked pytest -q tests/backend_core/test_image_jobs.py`:
  **16 passed**, one dependency deprecation warning. Full-suite numbers in the
  coordinator report were not independently rerun during this review.
- Viewed the retained primary image and all three original deliveries listed in
  the pilot receipt. The fictional face, bob hairstyle and eyebrow mark remain
  recognizably consistent in the close, three-quarter and wider action images.
  This is Codex visual judgment, not human review or universal identity proof.
- Reference and delivery evidence remains in the isolated pilot directory outside
  the disposable worktree. No additional generation is needed just to repair UI
  or evidence wording.

## Required corrections / acceptance gaps

1. **Truthful review attribution.** The pilot receipt calls the review human,
   without identifying human participation; the observed workflow is agent-operated.
   Identify actual reviewer provenance, label Codex review as such, and distinguish
   product review decisions from independent engineering acceptance. Do not rewrite
   immutable history to fabricate a person or erase earlier attribution errors.
2. **Expose character-proposal refinement.** Backend/API accept
   `parentCandidateAssetId`, but `prepareCharacterReferenceProposal` in
   `frontend/src/managed-media.tsx:335` always sends an original request. Proposal
   cards expose Copy and Refresh only. Provide the planned candidate-to-refinement
   selection and frozen-parent UI path; verify it with retained assets.
3. **Implement the actual visual comparison surface.** The same-person review
   panel (`frontend/src/managed-media.tsx:478`) renders IDs, revision labels and
   forms, not frozen reference images. A separate current-reference card renders
   only the current primary, not all frozen complementary references. Show the
   exact reference set bound to the selected candidate alongside it, with roles,
   character mapping and stale status. Test replacement/history and multi-reference
   display without relying on the reviewer opening package files manually.

Before declaring the remaining specialist boundary complete, explicitly check
that its operational entrypoint pins the code/skill for the job and rejects
unsupported versions before generation; merely asking the executor to report a
commit/hash afterward is not that guarantee. Include a real story-first UI journey
without downstream stages/Approval: the existing proposal backend test starts
from a full-project fixture and does not alone establish this browser experience.

## Flow diagnosis — separate from product acceptance

The run admitted `frontend`, but its started `p15-finalize` task admitted only
`docs/roadmap` and `docs/verification`. Commit `09f0397` changes two frontend E2E
files after that task's baseline `2666ce8`. Thus this is an exact task-contract
scope violation, not a missing top-level run envelope.

The plugin director independently confirmed that the pinned 0.9.13 runtime has
no supported task-level retirement/reissue for this started claim. A new task,
revert, or broadening the old contract cannot retroactively legitimize the commit.
No repository unplug was authorized or performed. Preserve the existing history.

At review time a source-only correction exception was proposed but not approved.
The subsequent consolidation direction above supersedes that proposed recovery.
P1.5 is not accepted and video remains out of scope.
