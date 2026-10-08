# ADR 0135: End-frame read qualification

Status: Accepted, 2026-10-08.

## Problem

The native E2E run found an unread end-frame setting presented as saved without
an image. The UI conflated unread `null`, a successfully read revision-zero
default and a persisted empty choice. A failed refresh retained its known
decision but also retained H3 preparation eligibility. Ownership omitted the
storyboard revision, and disabling buttons alone could not invalidate an
in-flight H3 source or prompt read.

## Decision

- End-frame read qualification, the last verified decision, editable draft and
  pending save are separate states. Qualification requires both owned setting
  and image-catalog reads to succeed. Ownership includes project, shot, approval
  and storyboard revision; replaced owners cannot publish reads or writes.
- Initial pending/failure never claims a saved empty choice. Revision zero is a
  known no-image default, not a persisted save. A failed refresh retains known
  content and draft but labels them unverified for the current read.
- Pending/failed reads and pending saves withdraw the parent's H3 source-ready
  signal as well as preparation eligibility. This invalidates pending prompt
  callbacks and consent while retaining author seed/text for exact revalidation,
  following ADR 0105. Successful reread requires fresh source review.
- A failed save response leaves the outcome unconfirmed. Require explicit
  rereading before another save or preparation; do not retry the mutation.
  Primary Chinese guidance preserves exact error evidence in secondary details.
  The component owns a stacked error layout and wrapping raw evidence; a shared
  row-style notice must not squeeze guidance or widen the document.
- Reopen guidance describes the action's limits, not an assumed later state:
  reopening alone does not prepare/select media. Route-only playback guidance
  explains that footage is unnecessary rather than implying missing author work.
  Frozen H3 quality is read only from the explicit current-contract field;
  retired profile-name inference is removed, not adapted.

## Alternatives and guardrails

Reject replacing failed reads with a no-image default, using draft-dirty as a
read-failure flag, or merely relabeling an eligible stale decision. The server's
existing revision/approval admission remains unchanged. Unit tests cover paired
reads, refresh/save uncertainty, owner changes and late prompt callbacks. Browser
GET-fault checks inspect pending/failure/recovery at 1280×768, 1280×460 and
1700×900, with zero mutation calls during the read-only exercise. E16/E22 retain
these states in the single reusable acceptance playbook.
