# ADR 0197: Exact image instruction access and host delivery ownership

Status: accepted for implementation; activation and provider E2E remain separate.

## Problem and evidence

The paused image attempt `17006dd2-f4e4-432d-b9f8-bbe75a4806c2`
could read its frozen package but could not read its pinned image skill. The
exact native rollout records `cat .../plotloom-image-specialist/SKILL.md`
returning `Operation not permitted`. Image workers supplied no source read
paths; the resource resolver and admission checks covered text only. The skill
also described manual pin/copy/publication steps that conflict with package v8's
trusted-host ownership. A no-generation native sandbox probe reproduced the
denial and succeeded when granting the exact skill file alone.

## Decision

For current Codex Exec image package v8, admission and worker launch verify the
source revision, execution contract, skill version and frozen skill SHA-256.
The child receives read access to that single regular in-checkout skill file.
No checkout, sibling skill, validator, runtime or credential access is added.

The skill names separate current Codex Exec and manual specialist-chat
procedures. The worker owns reference viewing and one ImageGen call; the trusted
host owns preflight, native identity, copying, validation, publication and staging
cleanup. Image assignment v5 states this division explicitly.

Reject granting the source root or ignoring a missing skill: both weaken the
frozen contract. Reject running the manual publisher inside the worker because
it would create two owners for native evidence and delivery.

## Consequences and guardrails

Instruction/profile hashes change. Existing frozen attempts, receipts and run
policies remain evidence of their original contract; do not repin or replay them
under this change. UNKNOWN capacity stays fenced. A completed model turn does
not prove a CLI exit code or authorize settlement.

The registered worker now persists its actual `Popen.wait()` result in private
`exec_process_exits` before telemetry interpretation. The witness binds immutable
attempt bytes and exact CLI/worker identities; it cannot be replaced. It does not
by itself settle remote work.

Explicit authenticated `POST /exec-recover-no-remote-dispatch/<attemptId>` accepts
only the exact current UNKNOWN snapshot. The native host alone constructs the
proof; callers cannot supply a fabricated exit code or proof. It requires the
unchanged original package and exact unique session, empty delivery/stderr,
positive CLI/worker PID and process-group absence, no validator intent, complete
stable terminal stdout and contiguous native rollout ordinals. Every tool must
be one literal awaited read-only `exec_command` with a completed structured
result. Only exact package `cat`, package inventory `ls` and pinned-skill `cat`
commands are admitted. Native command events and stdout command pairs must agree
with that inventory. Unknown tools, extensions, unsupported source forms,
incomplete calls, resumed turns or ambiguous evidence preserve UNKNOWN.

The host retains the original UNKNOWN snapshot and proof in
`exec_recovery_evidence`, and atomically transitions that exact attempt to
`settled/no_remote_dispatch`, releasing only its slot/budget. This distinct
terminal result states no remote invocation; `processExitCode` remains null.
It neither claims the CLI never started nor that its exit was observed. Normal
failure still requires a genuine exit code. Project reconciliation records this
as a failed checkpoint; it does not restore generation authority or replay the
frozen policy. Receipt-only current-v8 reconciliation validates against its
admitted profile; new admission still requires exact current-host equality.
The project may last have observed `running` when the host independently passed
through UNKNOWN and recovered. It may accept this one typed terminal transition
only with unchanged recorded CLI process identity and no conflicting session;
ordinary running-to-settled shortcuts remain forbidden.
After explicit cancellation/takeover, the no-dispatch proof also permits native
proposal cancellation, with truthful wording distinct from never-started work.
Recovery does not drain queues. Old unrelated UNKNOWN attempts
remain unchanged. Same-UID hostile evidence writers remain outside the existing
same-host trust contract.

Regression checks cover exact-file grants, stale revisions/hashes, symlinks,
admission rejection and manual-versus-host prompt ownership. The native probe is
permission evidence, not generation, creative acceptance or provider E2E.
