# Media-service ownership, verification and releases

Plotloom and its media services live in one repository, with independent build
environments and deployments. This is the maintenance entrypoint, not an API
specification or permission to restart services. The
[service decision](../adr/0216-media-services-monorepo-boundaries.md) records why.

## Owners and durable boundaries

| Component | Source / build environment | Runtime / state owner |
| --- | --- | --- |
| Plotloom | `src/plotloom/`, `frontend/`, root `pyproject.toml`/`uv.lock` | Authoring, review, selected media and durable project folders; client adapters consume service HTTP |
| Gateway | `services/minimax_h3_gateway/`, service `pyproject.toml`/`uv.lock`, `gateway` extra | `plotloom-h3-gateway` container; gateway SQLite/media and sole managed generation lane |
| Dashboard | Same service package/lock, without `gateway` extra; `dashboard.Dockerfile` | Independent `plotloom-h3-dashboard` CPU container; no database or generation worker of its own |
| Voice Lab | `services/qwen3_tts_voice_lab/`, its own `pyproject.toml`/`uv.lock` | `plotloom-voice-lab.service`; own SQLite, candidates, published identities and takes; supervised engine processes |
| H3 engine | Gateway's `comfy_nodes/`, pinned installation manifests and H3 setup guide | `spark-comfyui` container; separately qualified ComfyUI/model environment |
| Qwen image engine | Gateway's `deploy/qwen-image-sglang.service` and Qwen setup guide | Separately qualified SGLang systemd service; no inference dependencies in gateway |

Gateway and Lab communicate through authenticated HTTP, not Python imports or
cross-service database writes. [ADR 0212](../adr/0212-published-voice-performance-takes-and-shared-admission.md)
owns the shared FIFO: all managed H3, Qwen and voice inference uses one lane.
Model-direct callers are outside that guarantee. A quiet-looking GPU, expired
lease or healthy process does not resolve an uncertain dispatch.

The dashboard deliberately reads gateway SQLite and media **read-only**. It checks
required columns and fails closed on unavailable/incompatible schema; it does not
initialize, migrate, clean up or dispatch. Its only write operation forwards a
validated same-origin H3 creation request to the fixed gateway target. Missing
dedicated key leaves viewer mode available. This is a private schema coupling:
independent deployment does not imply arbitrary cross-version compatibility.

Gateway deliveries expire after 72 hours; transient gateway records/inputs follow
their existing 30-day policy. Published Lab voices and takes have separate durable
lifetimes and explicit deletion; they do not inherit gateway TTL. Plotloom retains
its selected copies under its own policy. Model files stay under `/home/wjmao/models`.

## Documentation and commands

- [Gateway package/build/test commands](../../services/minimax_h3_gateway/README.md#independent-package-checks-and-images).
- [Dashboard use and deployment](../../services/minimax_h3_gateway/docs/gateway-dashboard.md).
- [H3 API/operations](minimax-h3-gateway-manual.md) and [reproducible engine installation](../../services/minimax_h3_gateway/docs/h3-reproducible-setup.md).
- [Qwen API/operations](qwen-image-gateway-manual.md) and [reproducible engine installation](../../services/minimax_h3_gateway/docs/qwen-image-spark-setup.md).
- [Voice Lab package/verification](../../services/qwen3_tts_voice_lab/README.md#runtime-and-verification),
  [reproduction/engine locks](../../services/qwen3_tts_voice_lab/docs/reproduction-and-operations.md)
  and [take contract](../../services/qwen3_tts_voice_lab/docs/voice-takes-client-guide.md).

Run Lab commands **inside its directory**; `uv --project` selects an environment
but does not change pytest's working directory. From the repository root, these
are the focused Plotloom-facing boundary checks:

```sh
uv run --locked pytest -q tests/test_extraction_contract.py tests/test_service_source_contract.py tests/test_media_service_boundaries.py tests/video_backends/minimax_h3
```

The extraction check requires service source to be tracked; stage intended new
files before running it. Do not weaken admission to allow arbitrary untracked
runtime/model files. Test/build caches remain the existing explicit exceptions.

## Change-impact matrix

| Change | Checks | Deploy only |
| --- | --- | --- |
| Dashboard presentation | Dashboard Python/JS tests, artifact assets and affected real-browser journeys | Dashboard image |
| Shared package, dependencies or resources | Gateway/dashboard tests and both installed/image smokes | Changed serving artifacts; no model restarts |
| Gateway API, SQLite or lane | Gateway tests, dashboard schema tests, affected Plotloom and Lab contract tests | Gateway and only contract-affected consumers, in coordinated order |
| Voice Lab control service | Its locked tests/build, gateway take/admission tests | Lab control service; do not rebuild engine environments without an engine change |
| Model/runtime configuration | Separate qualification and approval | Specifically qualified runtime; not ordinary packaging maintenance |

Tests can use fake transports and temporary SQLite/media without inference.
Artifact smokes prove CPU startup/resources, not model quality or creative
acceptance. Use original retained media for browser preview/seek/download checks.
Never turn an HTTP response loss into an automatic generation retry.

## Release and rollback procedure

1. Use the retained source owner/checkout. Coordinate overlapping paths and any
   director-reserved live generation window before writes or serving replacement.
   A service revision does not require a Plotloom release or GitHub CI run.
2. Build and verify from the service lock. Record source revision, lockfile hash,
   image ID/digest, Python/dependency changes and Compose/systemd paths in a single
   verification receipt. Keep secret values out of those records. Image tags are
   convenient names; the recorded digest identifies the actual artifact.
   Label the digest type: an OCI index/manifest digest is not the image config
   digest reported by a classic Docker engine. For `docker save`/`load` transfers,
   verify the exported `manifest.json` config mapping and the image's rootfs
   layer identities; do not compare unlike digest types or silently trust a tag.
3. Exercise the ARM64 image with temporary data in an isolated, network-disabled
   container, with no production mount, GPU or Docker socket. This must pass before
   promotion. Preserve the preceding serving artifact/configuration for rollback.
4. Obtain the agreed quiet window. Verify gateway/Lab nonterminal work, unresolved
   grants, the durable lane and native ComfyUI queue. Block on active, queued or
   uncertain work; do not cancel colleagues' work or clear state. Recheck at cutover
   so work arriving after an earlier idle observation is not interrupted.
5. Replace only the selected component using its established settings/mounts. Never
   run a second gateway worker against live data. Dashboard changes do not restart
   the gateway, Lab or model runtimes. Gateway packaging changes do not restart
   ComfyUI/SGLang or change inference environments. Preserve the existing private
   `/dashboard/` Tailscale handler, dedicated key and loopback listener.
6. Check actual artifact identity, health, retained records/media and relevant
   HTTP consumers after replacement. For dashboard, check real private HTTPS,
   preview/seek and original-byte download. Readiness alone is not generation proof.
7. If verification fails, stop admission to the candidate only when safely idle,
   and restore that component's exact previous image/configuration. Do not roll
   back data, copy a live SQLite file, initialize a fresh store, or erase uncertain
   work. If work has entered an unknown state, preserve evidence and reconcile
   before attempting rollback. No automatic backup or state reset is introduced.

For Compose-managed dashboard releases, `up -d --no-deps dashboard` replaces only
that service; rollback uses its preceding release Compose file and image. The
currently serving gateway may be a directly created container, so inspect its
actual launch configuration instead of assuming Compose owns it. Preserve its
environment privately and recreate from the tested package entrypoint; never
copy environment values into a public command, log or receipt.

The [October 22 packaging receipt](../verification/2026-10-22-media-service-boundaries.md)
records the earlier service packaging release. The current
[B7 Gateway-only activation](../roadmap/2026-10-26-b3-b7-backend-and-services-ownership.md#gateway-only-activation-and-manager-verification)
records the serving artifact, preserved state and selected rollback. A retained
stopped gateway rollback container must have restart disabled to prevent a second
dispatcher after a reboot. Restore its original restart policy only when it
becomes the sole active gateway again, after fresh idle/uncertainty checks.

The owner authorized consolidation of the specialist source into main on
2026-10-22. The [integration record](../verification/2026-10-22-specialist-main-integration.md)
owns the merged source identity, ADR-number mapping, checks and evidence-preserving
branch cleanup. The deployed artifacts retain their exact recorded identities.
CI and push remain off.
