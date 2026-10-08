# ADR 0136: Route-owned project load availability

Status: Accepted, 2026-10-08.

## Problem

The native lifecycle walkthrough reloaded an exact shot link while its project
was closed. The service correctly refused409 `project_closed`, but aggregate
loading retained only a generic error. The host rendered a blank draft/editor,
misreporting missing shots and inviting first-save work. Existing tests even
asserted that fabricated blank editor. A failed matching refresh, however, must
not discard already loaded content or component-local authoring buffers.

## Decision

- Store the route-owned load failure in the canonical workspace snapshot:
  closed only from structured409 `project_closed`; missing only from the
  authoritative project read404; other aggregate/network errors unavailable.
  Existing read ownership and route epochs reject replaced/late results.
- With no accepted snapshot matching the requested server project, show a
  dedicated unavailable host, not an editor, unsaved draft or missing-entity
  diagnosis. Preserve the exact project/entity/hash URL. Guidance and sidebar
  describe availability; raw evidence stays in secondary reading details.
- Explicit retry only rereads. Reopening requires the existing directory action;
  no implicit open, save, generation or sample fallback occurs. The aggregate
  loader owns explicit `read-only` versus ordinary active-run continuation:
  rereading may inspect run progress but never calls Resume or credential-based
  automatic continuation. Existing normal load behavior stays separately named.
- A failed current Resume occurs after accepted reads. Preserve the same safety
  lock and payload, but name `continuation-failed` rather than reporting a failed
  project read; exact continuation evidence stays in separate diagnostic details.
- Matching refresh failures retain the accepted payload and mounted editor,
  withdraw writes and require a successful current read. Beginning/replacing a
  read, successful acceptance and local-workspace reset clear failure metadata.
  Dismissing a global error does not erase project availability.
  Retained refresh failures say that this read did not finish, not that the
  already loaded project disappeared; exact diagnostics remain in reading details.
- Existing unsafe-draft inspection/discard and real unsaved local work remain
  distinct. This is not permission to erase drafts or weaken lifecycle admission.

## Alternatives and guardrails

Reject special casing the shot warning, translating English without retaining
the reason, or unmounting every editor on refresh failure. Regressions distinguish
authoritative/non-authoritative404, closed links, initial/destination failure,
matching refresh, explicit retry with queued/running jobs and zero resume writes,
genuine absent shots, late responses and local
drafts. E19/E21/E22 require actual closed-link pixels and zero implicit writes.
