# ADR 0124: Requesting-client reads before exclusive project lifecycle actions

Status: accepted within G5 demonstrated-blocker scope, 2026-10-06.

## Problem and evidence

Native Save-and-close saved the shared Root successfully but collided with its
own Script GET holding a shared project lease. The full gate retained 185 passes
and one safe409 failure. Draft draining alone cannot settle requesting-client
readers. A Script receipt can also mount a fresh report iframe after JSON settles;
directory collection GETs acquire project handles too. Blanket409 “version
conflict” guidance falsely described this busy rejection.

## Decision

The API-client instance owns ephemeral per-project read admission and complete
JSON response-body lifetimes. A lifecycle attempt pauses new target reads and
directory collection reads, permits unrelated project reads and existing draft
PUT/DELETE drains, and waits admitted readers before exclusive Close/Snapshot/
Delete. Queued reads are abortable and are not inflight readers. Current registered
authoring, review and media draft drains await writes only; canonical saves that
await refreshes are not substituted for these drains.

Read admission resumes immediately after the exclusive response/body settles,
before directory projection refresh. Draft close admission remains held through
final cleanup. Failure and epoch invalidation resume read admission without
claiming a successful mutation; CAS, late-edit and cross-client rejection remain
unchanged. Only explicit revision_conflict receives merge guidance; project_busy
explains occupation and explicit retry.

Shared report frames acquire their own navigation ticket before mounting a fresh
iframe whose first src is the real report URL. Preserve URL, server CSP and the
existing sandbox grants. Load completes that ticket; error, owner invalidation and
StrictMode cleanup cancel only that ticket. Queued invalidated frames never mount;
old events cannot settle a newer navigation. Outline's existing availability probe
now tracks its entire body, then its separate iframe navigation.

Cancellation/cleanup does not prove a browser request released a server lease.
An attempt observing cancellation or an unsettled reader after30s fails closed;
the authoritative exclusive gate can still reject other/unknown occupation.
No automatic retry, lease bypass, editor-tree unmount, credential persistence or
queued-request logging is introduced. Direct media/asset loads retain server
admission; these tickets do not claim to track every browser resource.

October9 follow-up: Storyboard cancellation followed by Snapshot reproduced a
busy refusal through the real UI. Specialist status GETs used a separate fetch
owner outside the lifecycle barrier. All browser JSON API owners now share the
same read admission, including specialist status and image-terminal previews;
isolated API-client instances retain independent scopes. Preserve specialist
error parsing and dispatch semantics. Full body lifetime, queued admission,
failure/resume and real cancel-to-snapshot regressions guard this boundary.
Read completion is independent of domain success: a fully received409 after
cancellation has settled, while aborted or interrupted transport has not. Parse
domain errors outside the admitted response-body lifetime; never infer completion
from headers alone or retry the lifecycle mutation automatically.

## Alternatives and guardrails

Reject sleeps, fixture readiness delays, blanket retries and weaker exclusive
server admission. Reject rehosting retained HTML in srcDoc: it adds CSP and report
semantics without solving this bounded lifetime problem. Keep separate read and
draft barrier scopes. Regress complete JSON/collection bodies, real report
navigation, queued abort, cancellation/deadline, failure/resume, StrictMode and
existing late-edit/CAS/epoch/save-close/snapshot/delete paths before publication.
