# ADR 0100 — H3 dashboard submission boundary

Status: accepted by owner, 2026-10-21. Extends ADR 0099's read-only surface.

## Problem and decision

Colleagues need single H3 image-to-video creation without Bruno or a browser API
key. Keep the independent CPU-only dashboard and its read-only SQLite/media
mount. Add one fixed-target server-side POST to the existing authenticated
`/v1/video-jobs/from-image`; the gateway alone validates media, admits records and
dispatches through the existing FIFO. No new generation owner or persistence.

The dashboard receives only a dedicated gateway-key file, not the complete gateway
environment. The browser gets neither credential nor an arbitrary HTTP proxy.
Require exact same-origin POST and a custom request header, bounded bodies,
allowlisted existing image contracts, no redirects or automatic upstream retries.
Uncertain transport/upstream acceptance is explicit and never replayed automatically.
Tailnet members allowed to reach the console may now create H3 jobs, not just view.

Settings reuse copies prompt/scalars into the form but never dispatches or tries
to recover original input files/URLs. New images must be supplied explicitly.
The UI preserves drafts after failure and disables duplicate in-flight submits.
The dashboard-only seed projection is a decimal string: JavaScript numbers cannot
represent the gateway's full 63-bit seed range. The generation API stays unchanged.

## Alternatives and guardrails

Embedding bearer keys in JavaScript, browser storage or URLs is rejected. Direct
SQLite insertion bypasses admission and is rejected. No catch-all API proxy,
custom queue/idempotency database, T2V, batch or management controls are added.
Tests cover JSON/multipart, admission failures, oversized input, same-origin
checks, credential confinement, uncertain outcomes and no replay. Existing native
media/download and read-only tests remain. Retention/model/runtime are unchanged.
Native HTTPS permission remains an administrator gate, not grounds to widen access.
