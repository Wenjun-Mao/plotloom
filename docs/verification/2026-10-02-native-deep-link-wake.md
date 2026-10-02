# Native desktop deep-link wake verification

Date: 2026-10-02, America/Toronto. Baseline: `6c5479c`.
Scope: ADR 0096, Mac bridge queue-once plus external desktop opening.

## Source and diagnosis

The [official desktop command reference](https://learn.chatgpt.com/docs/reference/commands#deep-links)
explicitly supports `codex://threads/<thread-id>` for opening a local chat.
The installed app registers `codex` as a URL scheme. `codex app --help` itself
accepts a workspace path, not a thread argument; `/usr/bin/open` with the
documented URL is the external interface used here.

The earlier [blocked investigation](2026-10-01-specialist-wake-up-gap.md)
correctly rejected an unqualified standalone executor, but did not establish
this external native-open path. Separate native-navigation evidence was reviewed
against the complete five-turn disposable chat history and originating action
sequence. That result motivated the external-command tests below, not a replay
of the real S01 request.

## Actual external-command and bridge probes

Disposable chat: **Plotloom isolated queue wake probe**,
`01a0faab-a4c9-7c70-9b88-05b23c25161f`. No images or project edits were requested.

1. After unarchiving, native status was `notLoaded`. One CLI queue call saved
   `01a0fac9-2e33-79b0-b6ae-ff19dee11ff1`. A subsequent native status check still
   showed `notLoaded`, with the previous turn unchanged. One
   `/usr/bin/open codex://threads/<probe-id>` exited zero; turn
   `01a0fac9-62b0-77e3-bc29-336c86a0eeea` completed with
   `EXTERNAL_DEEP_LINK_WAKE_ACK_20261002`.
2. A harmless 30-second wait was queued once as
   `01a0facf-bd53-7101-bbe9-c5b2478caa3f`. Native status confirmed turn
   `01a0facf-c0e1-7d01-8044-be67d52d95ee` was in progress. After navigating away,
   the updated **actual `QueueBridge.queue` implementation** queued one harmless
   follow-up using an isolated settings file bound only to the probe and requested
   its deep-link opening. It returned `returncode=0, wakeState=open_requested`.
   The same original turn remained in progress immediately afterward.
3. The original turn completed normally at Unix second `1790914350` with
   `EXTERNAL_BUSY_ORIGINAL_ACK_20261002`. Follow-up turn
   `01a0fad0-4ca5-7fa2-a816-bd85263fd0e4` then ran from `1790914350` to
   `1790914352`, completing with `BRIDGE_BUSY_FOLLOWUP_ACK_20261002`.
   The three new turns were completed, not interrupted. A scoped read-only native
   queue count was zero. The probe was re-archived and the window returned to the
   director. No explicit turn/start, queue/start, steer, or interrupt was used.

## Failure and persistence tests

- Exact native queue then open ordering for both configured roles; URL contains
  only the validated specialist UUID. Unconfigured/malformed requests and health
  checks cannot queue or open chats.
- Open nonzero exit, timeout and OS error retain the queue acknowledgement;
  queue nonzero/timeout and lost bridge acknowledgements never retry or open.
- The shim forwards only the bounded wake envelope, not native subprocess output.
  Malformed acknowledgements fail closed without exposing payloads.
- Dispatcher and registry tests retain queued receipts and reservations across
  open failure/restart, block another submission, and release only on completion.
- All five text-stage routes surface the open warning while reporting queued.
  A real isolated art-storage/API fixture stays exported after that warning,
  refuses a resend and still admits its valid fixture delivery normally.

Focused bridge/manage/dispatcher/registry/routes/art-warning tests: **53 passed**.
Additional art storage, image exchange and character reference regressions:
**26 passed**. Scoped Ruff and `git diff --check` passed. The existing
Starlette/httpx TestClient deprecation warning remains.

Independent review found one P2: image-send errors were shown before reading
the already-exported handoff, leaving stale Send controls. The shared
failed-send reconciliation now performs a read only, retains the original
warning, and respects gallery session ownership. It covers art, character and
media image-send paths. Regression tests cover exported-state controls,
warning retention when the read fails, and old-session rejection. The same
reviewer confirmed resolution with no additional actionable findings and
independently passed 29 focused frontend tests.

Full frontend suite: **274 passed**. TypeScript and E2E type checks passed;
deterministic generated assets rebuilt. Art browser suite: **9 passed**.
The existing Vite large-chunk advisory remains. The 53 focused backend tests
were rerun after the UI fix and passed.

## Deployment and remaining acceptance boundary

`manage.py start` rebuilt the image, reloaded the Mac LaunchAgent using the new
bridge source hash, and recreated only the creator workbench container. Native
specialist chats were idle with empty queues before this operation; the S01
reservation was retained, not treated as permission to cancel or resend.
Container health and authenticated bridge health passed. Installed shim and
LaunchAgent bridge hashes match source, and the HTTP-served frontend bundle
hash matches the newly generated asset.

Before/after API snapshots of accepted art, all art proposals and specialist
bindings/reservations were exactly equal. SHA-256 checks of the S01 frozen
package, dispatch receipt, completion manifest, executor pin and generated PNG,
plus specialist settings, were all unchanged. The delivery PNG remains
`22dfbb6d7d548fc68e24b6d2664b174d6bebd0f3d43258a8897155ce96531dea`.
No production send, delivery-refresh, creative acceptance or lease clearing
was performed. Crash injection was not repeated with that pending reservation.

No actual ImageGen call was made by these probes. Acknowledged OS navigation is
not a startup, delivery or creative-acceptance receipt. Cold app start, sign-in
recovery, remote chats and all possible race timings remain unqualified.
The intentional user-visible tradeoff is switching the desktop's active chat.
The native scheduling probes used the updated bridge implementation with an
isolated binding; a new production ImageGen dispatch through the installed
HTTP bridge remains a subsequent creator workflow check, not a claimed result.

The real S01 worker independently completed before deployment planning, but its
Plotloom reservation remains pending normal delivery observation. The next
creator action is **检查图像交付**, not another Send. Keep that observation and
any creative reference choice separate from deployment acceptance.
