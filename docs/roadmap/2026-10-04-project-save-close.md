# Project save-and-close

Status: Reviewed, locally qualified, published and activated, 2026-10-04.
Full remote CI passed; creator usability acceptance is separate.

Completion: [verification receipt](../verification/2026-10-04-project-save-close.md)
binds runtime `c61d019` to 1,088 Python, 464 frontend unit and 153 full unfiltered
browser passes, independent review, normal activation and unchanged existing
project evidence. The live check inspected consent and cancelled it; no real
project was closed or modified. The approved stopping condition is met.

## Approved outcome

The creator can preserve unfinished author input, close and later reopen a
project. The directory also offers confirmed force-close: discard unsent local
edits and keep background jobs running. Close is not deletion.

## Sequence and evidence

1. Fix the unloaded-project drain contract and record lifecycle semantics in
   ADR 0113.
2. Bind newer source/review input to narrow recoverable drafts; add clear normal
   and force-close actions and truthful directory status.
3. Verify draft recovery, save failure, project isolation, explicit force
   consent and unchanged busy-job ownership. Run broader established gates on
   the stable candidate and obtain independent read-only review.
4. Build current static assets, activate the normal installation only after
   checking quiescence, and verify both existing projects remain unchanged.

Stop when the deployed actions and recovery flow are verified and published.
Creator walkthrough acceptance is separate from executed tests.

Initial browser evidence caught missing topbar directory projection, then a
same-instance recovery prompt skipped by a surviving editing flag. The second
failure's trace/screenshot/context are preserved under the task's local
`save-close-2026-10-04/recovery-second-failure` evidence. The method was narrowed
to explicit leave/reopen state coverage, not a longer retry of the same broad
journey. Independent review also proved an in-flight discard race and stale
section-map admission; both now have explicit queue/basis guards.
The directory inspection must complete before exclusive Close, with workspace
ownership captured before that wait. A held-read regression checks navigation
and new input preservation. Its two initial test-interaction failures are
preserved in `ownership-test-initial` and `ownership-test-second`; after the
second, snapshot evidence identified the composed Brief label and verification
was narrowed before returning to broader tests.

## Exclusions

No Chinese manual edits, V1 changes, generation, creative acceptance, job
cancellation, deletion, credential changes, H3 activation or test actions on
the creator's existing projects.
