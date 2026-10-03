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
without queueing a task. This deployment retains the walkthrough's disabled
video backend and existing explicit review/acceptance behavior (ADRs 0095/0096).

To remove only the host bridge, use `launchctl bootout gui/$(id -u)/com.plotloom.creator-codex-bridge`
and remove its exact plist from `~/Library/LaunchAgents/`. Stopping or removing
the container leaves the bound project directories in place.

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

## Verification

With no specialist work in flight, the bounded check deliberately terminates
only this workbench's server process, waits for Docker's automatic restart,
then recreates its container and compares accepted art, reference requests and
specialist state. It does not queue assignments:

```sh
uv run --locked pytest services/creator_workbench/test_bridge.py services/creator_workbench/test_manage.py tests/test_codex_image_dispatch.py tests/test_specialist_settings.py tests/test_specialist_routes.py -q
uv run --locked python services/creator_workbench/verify_restart.py --project ee271b49-f384-414c-9711-452ee6333b84
```
