# ADR 0099 — Private read-only generation gateway dashboard

Status: accepted for the owner-approved dashboard slice, 2026-10-20.

## Problem

Colleagues need to inspect job status/settings and retained original media without
SSH or the generation API key. Existing per-job GETs can reconcile state, and
constructing the generation application initializes storage and workers. The API
listens on the Tailscale address; Serve's HTTP proxy targets loopback. Widening the
generation listener or embedding credentials in browser code is not necessary.

## Decision

Run a separate CPU-only, loopback-only dashboard process/container within the
existing H3 service module. Mount existing gateway data read-only and query SQLite
with `mode=ro`/query-only, bounded transactions, no migration and no generation owner.
Private persistent Tailscale Serve exposes only `/dashboard/` over HTTPS.
The owner selected Tailscale access only: existing tailnet policy controls readers;
there is no extra password, browser API key, session store or public Funnel.

Use the shared lane's sequence/hold state as queue authority, including external
Voice Lab ownership. Recorded occupation is not proof of active GPU computation.
Contract duration is frameCount/fps, not a fresh media measurement. Metadata lists
are lightweight; prompts are separately requested and rendered as text.

Serve only database-owned, backend/MIME-matched, unexpired regular output files.
Pin no-follow file descriptors before original-byte GET/HEAD/Range streaming;
never expose a static output directory, transcode a clip, or extend retention.
The generation API, its credentials, profiles and workers remain unchanged.

## Alternatives and guardrails

Adding unauthenticated routes to the externally bound generation app would broaden
its surface and require a generation-service restart. Reusing constructors/refresh
GETs would silently introduce a second mutation owner. Browser bearer storage or
another account system adds authority/state this viewer does not need.

Tests must prove no initialization/writes, current reads with actual journal/mount
behavior, honest unknown/held states, bounded pagination, expiry and no-follow media
handling, browser seek/poll stability and actual HTTPS prefix/access behavior.
Reader or health failure is explicit, not a reason to reset state or replay a job.
Roll back only the dashboard and its own Serve handler. This is not Plotloom
integration, a diagnosis of reported playback defects, or creative acceptance.
