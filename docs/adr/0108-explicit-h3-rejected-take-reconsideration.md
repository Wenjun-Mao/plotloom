# ADR 0108: Explicit reconsideration of rejected H3 takes

Status: Accepted

## Context

H3 review records are append-only, but the latest `reject` also permanently
locked retained segment proposals. Owners could not reconsider an unchanged
current take without generating another job, which discarded the useful
history relationship and prevented a copy-only alternate choice.

## Decision

Keep `POST /video-jobs/{id}/review`'s existing select/reject contract. Add a
separate `/review/reopen` command that requires a nonblank reviewer, reason,
and current shot selection revision. It accepts only a current, ingested H3
job whose latest review event is `reject`, then appends a distinct `reopen`
event in the same lifecycle transaction as a per-shot selection revision
bump. It neither selects the job nor prepares a segment or generates media.

If the shot has no selection row, create one with a null selected job at
revision 1. Otherwise keep the current selected job and advance its active
segment's `selected_revision` with the row revision, preserving playback.
Timestamp the reopen strictly after the preceding review so ordered history
always presents it last. Original and derivative bytes and earlier review
events remain unchanged. Segment selection after reopening stays a separate
explicit action and continues to require owner listening and review.

## Consequences and guardrails

- Duplicate, non-rejected, non-H3, non-ingested, stale, tampered, and stale-CAS
  requests append no event. Restored projects must pass the established
  recovery acknowledgement gate before this mutation.
- Reopening restores eligibility for deliberate segment reconsideration; it
  does not accept audiovisual quality or imply sound approval.
- API and persistence tests cover retained review history and bytes, null-row
  creation, stale-token refusal, selecting retained media after reopening,
  other-job playback continuity, and refusal paths. Frontend tests cover
  required annotations, read-only/stale/busy locking, refreshed history, and
  the absence of automatic segment or job actions.
- Rewriting the old rejection, adding a bypass to segment selection, or
  regenerating a replacement as the only reconsideration path were rejected:
  each either loses audit history or moves the owner decision to the wrong
  lifecycle layer.
