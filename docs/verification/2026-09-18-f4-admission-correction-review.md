# F4 admission-correction independent review

Date: 2026-09-18. Scope: format-10 folder admission, prepared-publication
lifecycle/recovery blocking, cancellation/late delivery, exact section mapping,
route-cap timing, currentness, report labeling, and ScriptPanel async ownership.

## Method

An independent Terra read-only reviewer inspected the stable source and focused
tests. It made no edits, started no service, and evaluated only the F4 boundary
named above.

## Finding and disposition

The first pass found a P1 proof gap: the browser recopy/reload assertion checked
only the package location, not the immutable `request.json` bytes; and target
currentness was shown at delivery but not acceptance. The correction adds an
on-disk byte comparison after browser reload/recopy, a ready-candidate
target-change acceptance regression, and a deferred project-switch UI
ownership regression. The reviewer found no remaining P0–P2 implementation
defect in the reviewed boundary.

## Limits

This review validates offline admission/UI contracts and tests. It does not
approve the historical specialist candidate, create a new candidate, or grant
human creative approval. Fresh current-contract specialist proof remains the
director's next bounded action.
