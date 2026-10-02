# Persistent specialist wake-up investigation

Date: October 1, 2026 Toronto (native probes October 2, 03:27–03:34 UTC).
Baseline: clean retained local `main`, `f1cd4617fd73b55d922e1c5b5146ec51e970267a`.
Outcome: blocked execution-boundary investigation; no implementation or deployment.

## Root cause and ownership

The creator's real single S01 Send at 03:16 UTC received HTTP 200 and native CLI
exit 0. Plotloom recorded queued; native queue contained item
`01a0fa9c-9861-7702-bc3f-970b515a296a` with client ID
`01a0fa9c-985e-73c1-86ae-a91d8e37aea6`. The image specialist was `notLoaded`
with no new turn. The creator subsequently opened the specialist and confirmed
it started. This is retained manager/creator evidence, not a replay by this worker.

`services/creator_workbench/host_bridge.py` invokes only `codex queue`;
`codex_client.py` forwards its acknowledgement without retry. The missing
operation is native execution startup, after queue admission. Plotloom's frozen
package, reservation and delivery-validation contracts are not the failing layer.
Neither a new Send nor lease cleanup can fix startup safely.

The bridge remains unchanged. No mutation, wake, steer, interrupt, resend,
lease cleanup or project reset was performed against the real specialist/request.
No image generation, provider fallback or creative acceptance occurred.

## Native transport and admission evidence

Executable: `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`.
Experimental schemas were read from the supplied
`/tmp/plotloom-codex-schema.XAaYx3/v2` bundle. Their existence alone is not a
guarantee of execution safety.

| Probe | Result | Limit |
| --- | --- | --- |
| `app-server proxy` | Failed: no `~/.codex/app-server-control/app-server-control.sock` | No supported connection to the existing desktop writer established |
| `app-server daemon version` | Same missing-socket failure | No daemon start/restart attempted |
| Standalone `app-server --listen stdio://` | `thread/loaded/list` empty; `thread/read` of this running worker returned `notLoaded` | Status is process-local, not evidence the desktop is idle |
| Empty isolated queue/start | `-32600`, `queue is empty` | No turn returned; empty must be treated as no-op by a future adapter |
| Unloaded queue/start | `-32600`, `resume the thread before starting a queued message` | Start does not itself acquire/load the thread |
| Idle owner `thread/resume`, queue/start | Resume returned idle; start returned one inProgress turn | Standalone execution only, not ImageGen qualification |
| Busy owner queue/start | `-32600`, `thread already has an active or pending turn` | Queued work not started by that call |
| Second process resume while first owns idle thread | `-32600`, `thread … already has an active writer` | Exclusive ownership also blocks an alternate client from starting an existing idle writer |
| Concurrent two-process queue/start for same queued ID | Owner returned one turn; nonowner rejected with resume-required | Writer exclusion protects this tested race; not a shared-desktop-transport qualification |
| Repeated queue/add with same client ID | Returned a different queued ID; later list showed one entry for that client ID | Do not infer stable queued IDs or exactly-once execution across lost acknowledgements; production still never retries |

Standalone test target: `01a0faaa-15e4-72f3-9d80-d3bf5dfd3f5e`, rooted in
`/tmp/plotloom-wake-isolated`, with harmless acknowledgement prompts and explicit
no-tool/no-edit instructions. Native read after transports closed reported
`notLoaded`; persisted turns `01a0faaa-165e-7d90-bfe1-403bd3c81db6`,
`01a0faaa-5834-70e1-92ec-c613023d442f` and
`01a0faaa-8ab9-7330-96c5-75f336ebf66a` were interrupted. The first appeared
during queue-add testing, so queue-add/start responses alone do not prove which
client consumed a message. These probes do not claim completion or content
acceptance. Closing a one-shot standalone transport is not a qualified
long-running specialist completion path. Disposable pending messages remain;
do not confuse this target with production or start its queue during cleanup.

After proxy failure and the incomplete standalone path, method was reassessed.
Manager authorized one desktop-backed test rather than extrapolating from
process-local ownership/status.

## Desktop idle consumption

Explicitly isolated desktop chat: **Plotloom isolated queue wake probe**,
`01a0faab-a4c9-7c70-9b88-05b23c25161f`, created through the native chat tool,
projectless output directory
`/Users/wjmao/Documents/Codex/2026-10-01/plotloom-wake-desktop-probe/outputs`.

Initial harmless turn `01a0faab-a5bc-7962-859d-b0d4c4142522` completed with
`INITIAL_ACK`; native wait reported idle. Exactly one existing CLI `queue` call
then submitted a no-tools acknowledgement and exited 0. Without opening or
navigating to the chat, desktop turn `01a0faac-0c44-7512-9950-f22619b74daa`
completed with `QUEUED_ACK`. Native queue/list returned zero items. Therefore
loaded-idle desktop consumption works on this installed version; inability to
explicitly start its writer is not itself an idle-state product blocker.

The desktop busy/concurrent-start case was not exercised, nor was a desktop
unload/reload transition forced. Production specialists were not used as probes.
Manager owns disposable chat cleanup; no task was self-archived.

## Unloaded execution blocker

[Official app-server documentation](https://learn.chatgpt.com/docs/app-server)
states that dynamic tool definitions persist and are restored on resume, while
dynamic calls emit `item/tool/call` requests to the connected client. Restoring
definitions does not prove that another client can execute desktop ImageGen.
`ThreadResumeResponse` provides no tool-executor binding/inventory. Standalone
`mcpServerStatus/list` returned seven MCP servers and no imagegen-named MCP
tools; this is only an MCP inventory, not proof that built-in/dynamic ImageGen
is absent. No supported ImageGen executor binding for standalone execution was
established. The specialist skill requires built-in ImageGen and explicitly
blocks when it is unavailable.

The available proxy has no desktop control socket. Standalone resume/start can
acquire an unowned thread, but requires owning its turn lifetime and servicing
its tool requests. Shipping that route now would replace an established native
execution surface with an unqualified one. Status checks, private IPC/database
writes, global restart, alternate image provider and a client that discards tool
requests were rejected. No claim is made that every future supported transport
is impossible; this installed/configured path is not established.

Stop at this boundary. Next action is a supported desktop wake operation or
qualified shared transport preserving ImageGen/tool execution and lifetime,
then isolated unloaded, busy, concurrent-start and acknowledgement-loss tests.
Full exactly-once startup and end-to-end product acceptance remain unverified.

## Verification and retained state

- `uv run --locked pytest -q services/creator_workbench/test_bridge.py services/creator_workbench/test_manage.py`: **13 passed**.
- No runtime source changed; broader product tests, real-image generation and
  deployment/restart checks were not run for this documentation-only receipt.
- Probe helpers are ignored workflow-local scratch in
  `.local/creator-workbench-wake-probe/`; raw subprocess message/output and
  token contents were not persisted in evidence or logs. Only IDs/status/errors
  and harmless test acknowledgements are recorded here.
- Docker service, launchd bridge, bindings, data mounts and real generation
  completion path were not reloaded or modified. No cost/usage delta available.
- Implementation: none. Local verification: admission/desktop-idle observations
  and existing focused tests above. Product/creative acceptance: none.
