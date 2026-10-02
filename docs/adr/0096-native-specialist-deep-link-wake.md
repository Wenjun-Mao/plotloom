# ADR 0096 — Wake queued specialists through the desktop deep link

Status: accepted, 2026-10-02.

## Problem

The Mac bridge's successful `codex queue` call can leave an assignment waiting
in an unloaded chat. A separate app-server process is not a qualified substitute
for the desktop's tool executor and lifetime. The queue/reservation contract is
correct; the missing operation belongs at the Mac desktop-launch boundary.

## Decision

After one acknowledged queue call, the Mac bridge invokes `/usr/bin/open` once
with the documented `codex://threads/<thread-id>` URL. The ID is the already
validated, configured local specialist UUID; no prompt or other query data goes
in the URL. This intentionally changes the visible chat. The desktop owns
loading, scheduling and tools. Do not read status as an atomic guard, resume an
alternate executor, start a turn, steer, interrupt, or resend to wake a chat.
The same rule applies to text and image specialists. Health checks never open
chats. No queue acknowledgement means no open attempt and no automatic retry.

Queue admission and opening are separate outcomes. The bridge returns the
original queue return code plus `wakeState` on success: `open_requested` means
the OS accepted the open request, not that a turn started; `open_unconfirmed`
means opening failed or timed out. The existing 25-second queue deadline plus
a 2-second open deadline fit inside the client's 28-second request deadline.

The container shim emits only the bounded JSON envelope
`{"protocol":"plotloom.native-queue.v1","wakeState":"…"}` for acknowledged
queues. The dispatcher persists `state=queued` and that optional wake state
before surfacing an actionable open-unconfirmed error. The message explicitly
asks the creator to open the existing assistant, not resend. Its reservation
remains until normal terminal delivery handling. Raw subprocess output is never
forwarded or persisted. Ordinary native CLI output has no deployment envelope;
its existing queue-only semantics remain unchanged. A lost/malformed bridge
acknowledgement remains outcome-unknown, never permission to queue again.

Image-send views reconcile their persisted state even after a failed response:
export or queue admission can precede the warning. This is a read, never a
resend or delivery refresh. Retain the original warning if reconciliation also
fails, and respect the owning project/session before updating the view.

## Alternatives and guardrails

Standalone execution, private IPC, native database writes and a status-check
then start sequence were rejected. An agent-owned navigation tool is useful
evidence but is not a bridge API. The documented external deep link closes that
specific integration gap without transferring execution ownership.

Verify exact command order, configured-ID confinement, busy/unloaded desktop
behavior, bounded failures, and queued-receipt/lease retention on open failure.
Do not claim OS open success as generation, delivery or creative acceptance.
Closed-app/sign-in recovery, remote chats and all possible races are not implied
by a local live probe. The historical blocked receipt remains unchanged.

Source: [official desktop deep-link reference](https://learn.chatgpt.com/docs/reference/commands#deep-links).
