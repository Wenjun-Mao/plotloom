# Private generation gateway dashboard

Status: **OWNER APPROVED — IMPLEMENTATION IN PROGRESS; not yet deployed.**
Date: 2026-10-20, America/Toronto.

## Outcome and scope

Give the owner and colleagues a small, Chinese-language, read-only Spark dashboard
for gateway health, shared FIFO occupancy, recent H3/Qwen jobs and retained outputs.
The proposed address is **https://gx10-1523.tail6040ad.ts.net/dashboard/**.
This is a planned address, not an already deployed dashboard.

Reuse current SQLite records and gateway-managed media. Do not add a database,
generation controls, cancellation/deletion/retry actions, new retention rules,
GPU sampling, live log streaming or a replacement scheduler. No Plotloom authoring
UI, model/runtime tuning, voice-candidate editor or new provider generation is in scope.

## Verified starting point

- Retained specialist checkout: `/Users/wjmao/projects/HU/plotloom-h3-ref2va-gateway`,
  branch `codex/h3-ref2va-gateway`, source `fa56e775`.
  That is not a claim about the current Plotloom main revision.
- Spark gateway uses host networking and listens at `100.64.35.71:8090`;
  its current API is not reachable at `127.0.0.1:8090`.
- Spark runs Tailscale 1.102.4; its DNS name is
  `gx10-1523.tail6040ad.ts.net`, certificate domain is configured, and the
  observed Serve configuration is empty. Ports 443/8091 were not listening.
  Recheck these facts immediately before activation.
- Tailscale documents loopback HTTP reverse-proxy targets. Use Serve, not Funnel;
  do not change the existing API bind address to make it proxyable.
- Existing data root is `/home/wjmao/services/plotloom-h3-gateway/data`.
  `gateway.sqlite3` currently uses SQLite DELETE journaling and user_version 0.
  The authoritative schema is its actual columns, not an invented schema version.
- Jobs retain settings, frozen execution snapshots, timings, errors, Comfy IDs,
  managed filenames, hashes and expiry. The durable shared queue is
  `generation_lane.sequence`, including Voice Lab ownership.
- Existing `GatewayStore`/`H3Gateway` construction performs initialization,
  migrations/reconciliation; the dashboard must not instantiate those owners.
  Existing job GET/output methods can refresh state and buffer complete media;
  they are not the dashboard's read-only list/range-serving implementation.
- Current ordinary job responses calculate duration from frameCount/fps; this is
  expected contract duration, not independently measured output duration.

References: [operator manual](../operations/minimax-h3-gateway-manual.md),
[shared lane](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/lane.py),
[Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve),
[Serve access boundaries](https://tailscale.com/docs/features/tailscale-serve).

## Access decision — owner selected

**Tailscale access only**, selected by the owner on 2026-10-20, with no additional browser login.
The dashboard listens only on loopback; Serve supplies the private HTTPS entrypoint,
and existing tailnet access policy determines who can view jobs and download media.
Anyone permitted to reach this dashboard can view its operational details, including
on-demand prompts. HTTPS alone is not a new per-user authorization policy.

Do not add a password, account database, custom session system or API-key entry
in the browser. This access boundary applies to HTML, JSON, assets, downloads and
native media Range/HEAD requests alike. Keep the existing generation API's bearer
authentication unchanged and outside the Serve dashboard route.

## Proposed design

### Service and HTTPS boundary

- Keep all source under `services/minimax_h3_gateway/`, in cohesive dashboard
  modules/static assets with a documented entrypoint. Target files below ~400 lines;
  split responsibilities before exceeding 500 lines.
- Add a separate lightweight dashboard Compose service, bound only to
  `127.0.0.1:8091`, with restart policy. No GPU, gateway worker, Comfy write access,
  gateway `.env`, API key, Voice Lab secret or Docker socket is mounted.
- Mount the existing gateway data directory read-only, including any live SQLite
  companion files. Use `mode=ro`, query-only, short bounded transactions and no
  schema initialization. Never use `immutable=1`, copy a live database, or change
  production journal mode to accommodate this reader. Verify the deployed mount
  with actual journaling; missing/incompatible state produces an explicit error.
- Use persistent Tailscale Serve on HTTPS 443 for `/dashboard/` only, forwarding
  to the loopback dashboard. Do not proxy `/v1` generation APIs, expose a data
  directory, use Funnel, or reset/replace unrelated Serve configuration.
- The app owns `/dashboard` route paths. Preserve that prefix through the selected
  Serve mapping; test redirects, relative resources and media against the final
  HTTPS URL. Specify the verified mapping in the operations guide rather than
  guessing path-strip behavior. `/dashboard` redirects to `/dashboard/`.
- Existing `http://100.64.35.71:8090` API clients, bearer authentication,
  generation container, ComfyUI and model installation remain unchanged.

### Page and read projections

- Overview: dashboard/database reachability, last successful observation, gateway
  `/health` result and observation age, active lane owner/hold reason and queue count.
  Readiness observations are bounded, briefly cached GETs to the configured existing
  gateway health endpoint, not H3/Qwen inference or browser-selected proxy targets.
  Gateway health failure does not prevent viewing retained jobs.
- Queue: authoritative FIFO sequence, backend/owner, queue-ahead count and recorded
  state/hold code. Compute positions before filtering. A lane held for Voice Lab,
  external work or an unknown outcome must not masquerade as an idle gateway or
  proven running GPU work. Do not invent percentages, sampler steps or ETAs.
- History: default 50 rows, server-enforced maximum 100 and stable cursor pagination;
  job-ID search and backend/status filters. SQL uses validated, parameterized values.
  Light lists do not return prompts, full execution snapshots or raw logs.
- Detail: full copyable job ID, backend/input mode, frozen settings, seed, requested
  and expected contract duration/frame count/FPS, created/dispatch/completion times,
  generation elapsed versus time waiting, error/hold code, Comfy ID, output size,
  recorded SHA256, availability/expiry, and plain-text prompt on demand.
  Internal filesystem paths, credentials and arbitrary graph/raw log content stay private.
- UI labels are Chinese; IDs remain selectable/copyable. Show local timezone clearly.
  The selected job can be reopened through a stable URL/query value and browser refresh.
- Poll lightweight state about every five seconds while visible, with at most one
  request in flight, stale-response protection and failure backoff. Pause background
  polling when hidden. Do not rebuild the selected media element or reset playback
  on each poll; provide manual refresh and clear stale/error state.

### Media and retention

- Preview available MP4s using native video controls with seek/Range support;
  preview Qwen PNG outputs and provide named original-byte downloads.
- Every GET, HEAD and Range request checks the succeeded job, database expiry,
  backend/MIME and confined managed filename. Reject symlinks/traversal and handle
  cleanup between listing and opening without exposing another file.
- Support valid byte ranges/206 and unsatisfiable ranges/416. Never read the entire
  MP4 just to answer a range; no remux, transcoding, muted substitute or fake ended.
  Cache behavior must not turn expiry into renewed retrieval access.
- Preserve 72-hour output and existing 30-day record retention exactly. Distinguish
  expired, missing, not-yet-ready and unknown/unavailable from generation failure.
  A browser already holding downloaded bytes is not remote deletion control.
- Show the recorded hash without claiming the dashboard independently re-probed
  duration, verified every frame, accepted quality or diagnosed a reported jump.

## Ordered implementation and verification

1. Carry forward the settled Tailscale-only access decision. Compare the affected gateway subtree against the serving
   release and current main; preserve unrelated specialist/director work. Record the
   selected read-only/HTTPS boundary in a concise ADR using the repository's convention.
   One serial source owner; a bounded independent review after a stable candidate.
2. Implement dedicated query/projection and confined media-serving modules, then
   static HTML/CSS/JS. Add the dashboard entrypoint/container wiring without running
   generation app constructors or modifying existing API responses.
3. Focused locked tests: query-only/no-initialization, journal/mount compatibility,
   missing schema/lock/read failures, pagination/filtering, genuine shared FIFO/holds,
   timings and unknown outcomes. Cover HTML escaping, secret-free responses and
   the complete chosen access boundary.
4. Test original-byte video/image downloads; GET/HEAD/206/416; expired files still
   physically present; missing files; symlinks/traversal; output cleanup races.
   Use retained media/fixtures, not new provider calls.
5. Run the gateway's full locked suite, targeted lint, dashboard container build and
   a real FastAPI/file-SQLite browser journey. Verify filtering, copyable IDs, direct
   detail reload, seek/play/download, stale/error UI and polling without playback reset.
   Retain desktop and phone-sized screenshots. Main authoring frontend/build assets
   are not changed and cannot inherit unrelated qualification claims.
6. At an observed idle checkpoint (gateway lane/queue and Comfy queue empty), deploy
   only the dashboard service and the new exact Serve handler. Do not stop active
   generation, clear reservations, reboot Spark or restart Comfy/Qwen/Voice Lab.
   Reconcile existing Serve/port state again first; if permission/admin consent is
   required, use its native approval path rather than widening access or bypassing it.
7. Verify from this Mac over the actual HTTPS hostname with normal certificate
   validation: UI, chosen access restriction, native playback/seek/Range, download
   hash equality and expiry/error behavior. Verify original API health/configuration,
   job identities and generation container identity remain intact; do not mistake
   legitimate independent worker progress for a dashboard write.
8. Restart only the dashboard container to verify it recovers without creating new
   records or workers. Verify the persistent Serve/background and container restart
   configuration; a whole-Spark reboot is not required by this assignment.
9. Update the Chinese colleague guide and operator/reproducibility documentation
   with the HTTPS URL, access, read-only scope, expiry, diagnosis limits and exact
   start/status/rollback commands. Save a secret-free receipt with revisions,
   deployment identity, checks, screenshots and remaining limitations.

## Permissions, rollback and stopping condition

The owner approved implementation with “Go” after settling Tailscale-only access.
This covers scoped dashboard code/docs/tests, building/starting its new Spark service,
adding its private persistent Serve handler at an idle checkpoint, and the verification
above. It does not cover new model generation, destructive resets, credentials/ACL
rotation, changes to sampling/media/retention or unrelated service restarts.

Rollback stops/removes only the new dashboard service and its exact new Serve
handler, retaining source/receipt and restoring any exact changed dashboard routing
configuration. Do not run a global Serve reset or delete gateway state/assets.
No database migration rollback is needed because there must be no migration.

Completion means an owner-accessible tailnet HTTPS dashboard meeting the read-only,
queue/currentness/media tests, documented operations and a retained verification
receipt. This does not resolve the colleague's video report or claim creative quality
approval. Preserve the existing specialist integration/merge/push hold; transferring
the broader retained branch into active Plotloom main is not part of this slice.
