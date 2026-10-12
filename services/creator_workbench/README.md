# Persistent creator workbench (Mac + Docker)

Run from the Plotloom checkout:

```sh
uv run --locked python services/creator_workbench/manage.py start --data-root .local/creator-walkthrough
```

This starts a detached container at **http://127.0.0.1:8841/v2/** using the
existing walkthrough project and installation data. Port 8841 must be free;
stop the old foreground walkthrough process before starting. The image installs
locked Python dependencies, Node, Git and FFmpeg/ffprobe for exact playback
segment derivation. Installing these tools does not enable a video provider.
The current checkout is mounted
read-only so Git/submodule pins, adapters and frozen package paths remain valid.
Only the existing `outputs` and `application` subdirectories are writable.
No project copy, reset, request rewrite or task dispatch occurs during startup.

Docker restarts the container after an unexpected exit or an engine restart.
Leave the Docker runtime configured to start when you log in (OrbStack on the
current host; Docker Desktop also supports this setup). The Mac must be
awake; this is a local service, not an always-on remote deployment. An explicit
`stop` remains stopped until the next `start`.

```sh
uv run --locked python services/creator_workbench/manage.py status
uv run --locked python services/creator_workbench/manage.py logs
uv run --locked python services/creator_workbench/manage.py check-bridge
uv run --locked python services/creator_workbench/manage.py stop
```

After dependency, service-file or Python source changes, rerun `start` to rebuild
and recreate the container. The checkout mount exposes source changes, but an
already-running Python process keeps imported code cached. Rebuild generated
frontend assets when changing the frontend; these static bytes are served from
the mount without a backend restart. Coordinate any schema admission and wait
for a quiet dispatch checkpoint before activating a changed backend.

## Private colleague access over Tailscale

For the requested app-specific name `plotloom.tail6040ad.ts.net`, use the
[dedicated private node](tailnet/README.md). It has a separate identity and
does not rename this Mac or change either existing Mac Serve endpoint. The
port-based endpoint below remains an independently configured fallback.

On the owner's Mac, the separately configured workbench URL is
**https://wenjuns-macbook-pro.tail6040ad.ts.net:8443/v2/**.
Colleagues must be connected to Tailscale and allowed by the tailnet's policy
to reach this Mac on TCP 8443. No policy changes or public Funnel access were
enabled. The existing HTTPS 443 proxy to localhost:8000 remains separate.

This is the same installation, not a copy or a read-only player. Plotloom has
no per-user login or roles: permitted clients share full project editing,
deletion, settings and production controls, including the owner's configured
native specialist queue. Grant access only to trusted co-admins; do not assume
separate projects or credentials are isolated between colleagues.

Keep the managed Docker host publication on `127.0.0.1:8841`. With the existing
Tailscale HTTPS capability enabled, the endpoint was added without restarting
Plotloom or exposing its native bridge on port 8842:

```sh
tailscale serve --bg --https=8443 http://127.0.0.1:8841
tailscale serve status --json
```

Tailscale manages HTTPS and the background Serve configuration persists across
restarts. The Mac must remain awake, connected to Tailscale, with Docker and
Plotloom running. See the [official Serve reference](https://tailscale.com/kb/1242/tailscale-serve).
To remove only this endpoint, preserving the existing 443 service:

```sh
tailscale serve --bg --https=8443 off
```

Do not use `serve reset` or `funnel` for this operation. Tailnet policy is the
access boundary; allowing colleagues onto this endpoint does not install
application-level authentication. Before enabling an API text provider on a
shared instance, reassess credential authority: a co-admin can change a text
profile's API destination and trigger a probe with its server-side key.

Configuration was verified on 2026-10-11: Serve retained 443 -> 8000 and added
8443 -> 8841, with no `AllowFunnel` entries; the Docker publication remained
loopback-only. Requests from this Mac through the HTTPS URL passed certificate
verification and returned 200 for `/healthz`, `/v2/` and the same-origin
`/api/v2/runtime-capabilities` API. The active instance reported
`apiTextPipeline: false`; its text-profile/probe routes are not registered.
No project or provider action was performed. A colleague-device connection
and that device's tailnet-policy permission still require real peer validation.
See [ADR 0095](../../docs/adr/0095-persistent-creator-workbench.md).

## Native specialist bridge

The text/image send buttons use the Mac Codex app's supported queue CLI. Linux
cannot run that executable. `start` installs the separate user LaunchAgent
`com.plotloom.creator-codex-bridge`, which starts at login and restarts if it
exits. It listens only on localhost:8842; the container connects through
`host.docker.internal`. Only the current configured specialist chats can be
queued. The token is created with mode 0600 in
`~/Library/Application Support/Plotloom/creator-workbench/bridge-token` and
mounted as a Compose secret, never baked into the image or project state.
Deployment paths/logs live in ignored `.local/creator-workbench/`.

After queue acknowledgement, the bridge requests desktop opening with
`/usr/bin/open codex://threads/<configured-specialist-id>`. This documented
deep link **switches the visible chat**; the desktop retains its own executor
and schedules queued work without steering or interrupting an active turn.
The open acknowledgement is not evidence that generation has started. If it
fails or times out, Plotloom retains the queued receipt/reservation and tells
the creator to open the existing assistant manually, not resend.

The browser can stay available while Codex is closed. Desktop cold-start and
sign-in recovery are not qualified by the local wake probe. The bridge makes
one queue and one post-acknowledgement open attempt and never retries; the
existing Plotloom reservations still protect unknown queue outcomes. Never
delete leases to get around a failed send. `check-bridge` checks connectivity
without queueing a task. Video generation is disabled by default and retains
the existing explicit review/acceptance behavior (ADRs 0095/0096).

To remove only the host bridge, use `launchctl bootout gui/$(id -u)/com.plotloom.creator-codex-bridge`
and remove its exact plist from `~/Library/LaunchAgents/`. Stopping or removing
the container leaves the bound project directories in place.

## Explicit private H3 gateway opt-in

An operator can enable the existing reviewed H3 gateway at a quiet dispatch
checkpoint. Supply a regular, non-symlink configuration file owned by the
current user with no group/other permissions (0600), outside creator data and
the service source directory. The file must contain `VIDEO_PROVIDER`,
`VIDEO_MODEL` (the current reviewed H3 catalog/profile), `VIDEO_BASE_URL`
(a credential-free private IP host root), `VIDEO_AUTH_MODE=bearer` and
`VIDEO_MODEL_API_KEY`. An existing protected checkout `.env` is supported;
unrelated storage/settings keys are ignored. Never put credentials in a command.

```sh
uv run --locked python services/creator_workbench/manage.py start --h3-config /absolute/private/owner.env
uv run --locked python services/creator_workbench/manage.py start --disable-h3
```

The enabled deployment remembers only the absolute configuration path and
mounts the file as a read-only Compose secret. It does not export parsed values
into the environment or pass them to specialist tasks. Ambient provider flags
cannot enable a default installation. Subsequent `start` retains and validates
the explicit configuration before Docker or bridge changes; invalid settings
fail closed without printing credential-bearing validation details.

Startup validates local configuration, not gateway availability. The existing
generation preflight checks the gateway before freezing/submitting a job.
Enabling or disabling does not dispatch jobs, select media, change approvals,
delete credentials or remove job evidence. Disabling preserves project data
and native specialist leases. Tests use fake credentials and no gateway calls:

```sh
uv run --locked pytest tests/services/creator_workbench/test_h3_runtime.py services/creator_workbench/test_manage.py -q
```

## Isolated test installation

Use `isolated.py` for an already restored, verified test installation. It owns
one loopback server and native bridge in the same process, with an ephemeral
outbound shim and one shared installation-local specialist registry. Do not
copy/edit launcher scripts or point the copy at the normal LaunchAgent.

```sh
uv run --locked python services/creator_workbench/isolated.py \
  --data-root .local/unattended-2026-10-02/final-installation \
  --static-dir .local/unattended-2026-10-02/static \
  --codex /absolute/path/to/native/codex \
  --token-file /absolute/private/directory/bridge-token \
  --port 8851 --bridge-port 8852
```

Supply an existing owner-only credential outside installation state: directory
0700, regular token file 0600, owned by the current user. Startup rejects
foreign dispatch roots, symlinked application state, unavailable executables and
port collisions. Both specialist roles, including UI rebindings, use the exact
derived shim URL/credential environment. Parent PATH/bridge/proxy settings do
not route this installation elsewhere. Stopping the process releases its ports,
bridge and shim; it does not change leases, receipts or other services.

Qualify the complete HTTP → shim subprocess → authenticated bridge → fake
native executable path before a real package dispatch. This test uses generated
fixture UUIDs and stubs desktop navigation; it cannot send an actual user task:

```sh
uv run --locked python -m pytest services/creator_workbench/test_isolated.py -q
```

An isolated health check is a no-queue readiness probe, never dispatch evidence.
The existing outcome-unknown policy still forbids blind retry or lease clearing.
See [ADR 0098](../../docs/adr/0098-isolated-workbench-native-transport.md).

## Native dramatic intent

Both creator launchers compose native intent through the same installation-local
text specialist registry; no API credentials or text-admission service are needed.
With a configured text assistant, open 分镜评审 → 投产提案, prepare the proposal,
then select “准备 Codex 戏剧意图任务” and “发送给 Codex 文字助手”. These are separate
actions. Preparation requires committed execution source and freezes the exact
proposal, source inputs and replacement target. The assignment names the runtime's
absolute checkout, local skill, contract and validator, even when the assistant's
chat was created in another checkout. Do not switch or reset that chat's repository.

“检查原任务交付” validates the same package and delivery after a restart, including
an unknown send. It never sends again. Read the original report and disclosed
limitations, then explicitly save the whole intent package, review presentation
and confirm production. An unchanged complete suggestion can be saved to record
that review. Delivery alone cannot install production. Cancellation does not
stop the assistant or release a reservation; complete validated late delivery
settles it without adopting suggestions. An unconfigured assistant remains an
explicit unavailable capability; API inference, when configured independently,
is a separate generation choice. See [ADR 0140](../../docs/adr/0140-native-bridge-intent-candidates.md).

## Verification

With no specialist work in flight, the bounded check deliberately terminates
only this workbench's server process, waits for Docker's automatic restart,
then recreates its container and compares accepted art, reference requests and
specialist state. It does not queue assignments:

```sh
uv run --locked pytest services/creator_workbench/test_bridge.py services/creator_workbench/test_manage.py tests/test_codex_image_dispatch.py tests/test_specialist_settings.py tests/test_specialist_routes.py -q
uv run --locked python services/creator_workbench/verify_restart.py --project ee271b49-f384-414c-9711-452ee6333b84
```
