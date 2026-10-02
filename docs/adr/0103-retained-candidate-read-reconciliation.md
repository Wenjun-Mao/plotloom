# ADR 0103: Retained candidate and authoritative media reads

Status: Accepted

## Context

The media reader withdraws its current snapshot during refresh and failure.
The selection context treated that temporary absence as a reviewed-binding
transition. After a creator kept a replacement candidate and saved its intent,
the old binding reappeared on refresh and silently replaced the retained
candidate. A subsequent review could therefore bind the old asset again and
invalidate refinements frozen against its previous binding.

## Decision

Creator retention and reviewed binding are separate state. Reconciliation
observes binding identity only from a ready read, scoped to project and Shot.
The first ready read restores the durable binding, or clears retention when
none exists. A genuine binding identity change likewise restores or clears.
An unchanged authoritative binding preserves the creator's explicit retention
through loading, failure and retry. Project or Shot navigation clears retention
immediately and initializes it from the new scope's first ready read.

The media reader continues withdrawing snapshots and disabling owner actions,
draft autosave and quiescence writers while the read is unknown. Retention
does not establish currentness or grant selection/generation eligibility.

## Consequences and guardrails

- Saving an intent, polling or another same-context refresh cannot silently
  replace the retained candidate with an unchanged reviewed asset.
- Reload/navigation and genuine binding changes still restore durable selection;
  a ready removal clears it, while temporary read withdrawal does not.
- Deferred-read regressions cover intent save followed by the exact review
  asset/intent payload, failure/retry, navigation and binding transitions.
  Existing freshness, failed-read and draft/quiescence tests remain required.
- Returning stale snapshots or special-casing intent-save callers was rejected:
  both would leave the selection contract wrong for other refresh owners.
- Backend frozen-parent admission remains unchanged. Invalidated candidates
  remain history and require fresh preparation rather than revival.
