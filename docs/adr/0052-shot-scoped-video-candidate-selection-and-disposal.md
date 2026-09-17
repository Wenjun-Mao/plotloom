# ADR 0052: shot-scoped video candidate selection and disposal

## Decision

Video jobs are immutable candidate attempts, and video reviews are immutable
review history.  Neither is the selection authority.  Each project/shot has a
separate, revisioned selection record that names zero or one current ingested
candidate.  Selecting supplies the expected selection revision and atomically
replaces that record; a stale intent fails rather than winning by arrival order.
Preparing another candidate does not change that record.

Project-folder databases created immediately before this authority existed use
one explicit, writable format-8 transition.  It admits only the exact known
pre-selection project schema, creates the selection table transactionally, and
backfills a shot only when its latest retained review is `select`. Existing
selection rows are never rewritten.  Read-only inspection, closed-project
admission, restore validation, and any unknown schema fail with a clear
transition-required or unsupported-schema error; none creates a table as a
fallback.

Runtime startup admits an active folder through that same writable registry
open before it reads startup-recovery state. A closed folder remains excluded
and receives an empty recovery plan; startup never opens it implicitly. This
keeps the one-time transition on the normal production path instead of letting
an earlier read-only recovery inspection make an otherwise admitted project
unstartable.

Disposal is an explicit candidate operation.  It rechecks the shot, project,
selection revision, job state, and selected candidate before marking only named
ingested candidates `discard_pending`.  Project storage then removes an owned
blob only when no retained video job references it and finalizes the rows as
`discarded`, retaining their immutable request, review, and accounting facts.
An interrupted cleanup remains `discard_pending` and can be retried; it is not
made playable while pending.  There is no Trash or automatic backup layer.

## Consequences

Route and branch players project from the selection record, so replacing one
shot safely changes only that shot.  Active or unknown-outcome jobs and
cross-project/shot IDs cannot be discarded.  Content-addressed bytes shared by
another retained video job stay in place.  This supersedes the previous
"latest review wins" projection in ADR 0051 without changing its route-order
authority or playback guards. The transition is intentionally not a generic
project migration framework or continuing read authority: after it commits,
the selection table is the only authority.
