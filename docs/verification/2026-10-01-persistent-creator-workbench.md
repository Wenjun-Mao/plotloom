# Persistent creator workbench — 2026-10-01

Scope: creator-approved local Docker deployment and outage diagnosis (ADR 0095).
The retained project is `ee271b49-f384-414c-9711-452ee6333b84`, 雨停以后.

## Cause and deployment

The last walkthrough ran as `uv run --locked python
.local/creator-walkthrough/serve.py`, a foreground process with no restart owner.
The creator's Safari screenshot records 2026-09-30 01:31:30 UTC (September 29
21:31:30 Toronto). `sysctl kern.boottime` and `last reboot` record the Mac reboot
at September 29 21:34:56 Toronto, about three minutes later. At diagnosis there
was no walkthrough process and no listener on port 8841. The older
`server.log` belongs to a previously stopped runner, so it is not evidence of
an exception in the last foreground process. The reboot plus absent automatic
startup explains this outage; earlier terminations are not independently
attributed here.

`plotloom-creator-workbench-1` now runs on the existing OrbStack Docker engine,
with `unless-stopped`, init/signal handling, health checks, bounded container
logs and localhost-only port 8841. The source mount is read-only; existing
outputs/application mounts are writable at identical host paths, using UID/GID
501:20. The image uses uv 0.12.19 and `uv.lock`, Python 3.12, Node 24 and Git.
Docker build context excludes project data and local credentials.

The native Mac CLI remains behind the separately supervised
`com.plotloom.creator-codex-bridge` LaunchAgent. The container CLI shim reaches
it through `host.docker.internal:8842`, authenticates using a read-only secret
mount and makes no retries. Only configured text/image task IDs are allowed.
The token lives outside project/application state. Existing dispatch roots,
receipts and leases remain authoritative and are never reset by deployment.

OrbStack's General → Start at login switch was off. It was enabled and the
native accessibility state verified `Value: on`. The Mac must remain awake;
native specialist execution still depends on the Codex app. No Mac reboot or
whole Docker-engine restart was performed, to avoid interrupting other work.

## Executed evidence

- 31 focused bridge/installer/native-dispatch/specialist tests passed, including
  authentication, both configured roles, malformed/unbound requests, ambiguous
  timeout without retry, unloaded-agent restart, reload after source changes,
  preservation/securing of existing tokens and rejection of symlink credentials.
  Ruff checks and formatting passed. The existing FastAPI TestClient deprecation
  warning is unrelated to this deployment.
- A real container process was deliberately terminated while no specialist
  work was in flight. Docker automatically restarted it. A subsequent forced
  container recreation also restored healthy service. The acceptance script
  compared full accepted-art, art-reference proposal and specialist state
  across both operations; all remained identical.
- Accepted art remains r1, content hash
  `6451a6cfb635722e6cfacd73cfb613921a9cffea89a3ce564a6f25b21cb30c18`.
  S01 image proposal `ij_a1778b3c84c84f01a7f19540747200f0` remains current/prepared,
  request hash `ce391b8906d1d96b991c1ca9cfd406cc2e7bec6557bd1a67ac39bf7a10212f7f`.
  Its Chinese image requirements remain exact.
- Health, project/art/reference reads, static workbench HTTP 200, authenticated
  bridge connectivity, source mount permissions and the exact upstream
  execution pin `4322897e6d2bdaf66365534fd40194360c75a85f` were verified inside the
  running container. Bridge health proves connectivity and CLI-path presence,
  not native queue acceptance or image completion.

Independent Luna Max review identified that existing credential paths needed
their private permissions enforced, rather than relying only on creation mode.
The installer now checks ownership/type, rejects symlinks, enforces 0700/0600
without replacing token bytes, and applies this on configured starts as well.
Focused tests and final container crash/recreation acceptance were rerun; the
reviewer confirmed the finding resolved with no remaining issue.

No live queue request, image/video generation, creative acceptance or reference
selection was issued. The creator can resume their prepared S01 task at the
same URL. Operational commands and repeatable checks live with the workflow in
`services/creator_workbench/README.md`.
