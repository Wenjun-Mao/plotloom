# Independently maintainable media services in Plotloom

Status: implemented, verified and deployed, 2026-10-22, in the retained specialist
checkout. The director explicitly released the quiet window before replacement;
the completed serving checks were reported back before its next H3 batch.
Implementation source: `37828fd3`. Integration, merge, push and hosted CI remain held.
Evidence: [packaging verification](../verification/2026-10-22-media-service-boundaries.md).
Planning baseline: `5fd5128b`, `codex/h3-ref2va-gateway`.
Decision: [media-service boundaries](../adr/media-services-monorepo-boundaries.md).

## Outcome and scope

Keep one repository, with service-owned dependency locks, build artifacts,
verification and deployment instructions. A dashboard-only change must not
require installing Plotloom or restarting generation services. A gateway change
must not require rebuilding Plotloom or changing any model environment.

This is a packaging and maintenance slice, not a runtime redesign. Preserve all
current public/private HTTP contracts, job snapshots, FIFO/unknown-outcome safety,
voice identities/takes, generation settings, retention and Tailscale access.
Plotloom integration, merge and push remain held. The owner explicitly authorized
director coordination for repository writes and runtime cutover. No hosted CI
dispatch or CI-triggering push is authorized.

## Source-backed baseline

| Component | Current ownership | Gap addressed here |
| --- | --- | --- |
| Plotloom | `src/plotloom/video_backends/minimax_h3/` owns the HTTP client, not ComfyUI or gateway storage | Add focused regression guards for the existing separation; no client behavior changes |
| Gateway | `services/minimax_h3_gateway/`; own container and SQLite, gateway-owned shared generation lane | Dockerfile hand-pins dependencies without a service manifest/lock; build context is the repository root |
| Dashboard | Same service subtree; independent CPU container and entrypoint, read-only gateway storage, fixed-target H3 submission forwarding | Dockerfile installs root Plotloom dependencies and manually copies selected modules |
| Voice Lab | `services/qwen3_tts_voice_lab/`; own `pyproject.toml`, `uv.lock`, CPU API and isolated engine environments | Preserve the working package boundary; document and test its relationship to gateway admission |
| H3 / Qwen inference | Separately deployed ComfyUI and SGLang, with service-owned adapters/configuration | Keep runtime/model installations unchanged; do not bundle them into control-service environments |

The root cause is incomplete dependency/build ownership, not a missing repository.
Dashboard and gateway intentionally share a private database schema; Voice Lab
communicates through HTTP and owns its own database. Independent deployment does
not promise compatibility with arbitrary service versions.

## Ordered deliverables

### 1. Establish the ownership and change map

- Publish one media-services entrypoint at `docs/operations/media-services.md`.
  Link existing service READMEs and H3/Qwen/voice guides rather than moving or
  duplicating them. Do not rename the historical service/package directories.
- Identify source, data, dependency lock, build/test commands, runtime entrypoint,
  deployment configuration and rollback owner for each component.
- Record the existing integration boundaries: Plotloom to gateway HTTP; gateway
  to Voice Lab HTTP; gateway-owned shared lane; dashboard to gateway read-only
  SQLite plus protected submission forwarding. Direct backend use bypasses the
  managed lane and is not made safe by this work.
- Preserve durable Voice Lab voices/takes independently of the gateway's temporary
  media retention. Do not flatten their different data lifecycles.

Acceptance: every deployment has one discoverable entrypoint and an unambiguous
owner; the map distinguishes a shared package from a shared process or release.

### 2. Give the gateway/dashboard a service-owned package and lock

- Add `pyproject.toml` and `uv.lock` in `services/minimax_h3_gateway/`, using the
  existing `plotloom_h3_gateway` namespace and separate gateway/dashboard entrypoints.
  Use a small common dependency set with role extras where needed, plus test tools.
  Do not create a root-wide uv workspace or shared inference dependency environment.
- Inventory current versions before locking. Preserve serving versions where
  possible; document and verify any unavoidable reconciliation. No opportunistic
  dependency upgrades. If a conflict requires a material runtime change, stop and
  present it rather than silently expanding this slice.
- Package the workflow JSON and dashboard HTML/CSS/JS explicitly. Verify wheel
  contents and installed resource lookup from an unrelated working directory.
- Update both Dockerfiles and Compose build contexts to consume only the service
  subtree and its lock. Keep two independently buildable images and deployment
  entrypoints. Shared Python modules do not imply a shared running worker.
- Preserve the dashboard's non-root, CPU-only execution, read-only data and key
  mounts, bounded temporary storage, loopback binding and tailnet-only access.
  Import/startup must not initialize storage or start gateway dispatch.
- Leave Voice Lab's package and pinned per-engine environments intact; change them
  only if a demonstrated packaging-boundary defect blocks this scoped acceptance.

Acceptance: both images build without root `pyproject.toml`, root `uv.lock` or
`src/plotloom`; installed artifacts find their resources without source-tree
`PYTHONPATH` injection. Neither image installs model inference frameworks.

### 3. Protect the boundaries with focused, repeatable verification

- Retain the gateway tests at `tests/services/minimax_h3_gateway/` unless a small
  relocation is necessary. Run them using the new service lock, without installing
  Plotloom. Keep repository/tooling tests distinct from installed-package tests;
  relative checkout paths must not masquerade as independent artifact coverage.
- Add installed-wheel/container smoke checks using temporary data and fake
  backends. Prove API startup, workflow/static resource loading and dashboard
  viewer/submission modes without Spark, model files or new generation.
- Extend existing import/distribution guards to prevent Plotloom importing service
  runtime packages and services importing Plotloom. Allow dashboard's intentional
  internal gateway imports; do not introduce a shared cross-service Python SDK.
- Preserve existing dashboard schema checks (`mode=ro`, `query_only`, required
  columns and stable unavailable errors). Exercise the current schema and an
  incompatible fixture. No new schema negotiation, historical compatibility
  layer, database, or gateway read API is needed.
- Exercise gateway/Voice Lab registration, execution grants, restart reconciliation
  and unknown-result behavior through existing fake-transport tests. Independent
  packaging must not enable a second dispatcher or replay uncertain inference.
- Preserve browser preview/download/navigation and authenticated H3 forwarding,
  including missing-key viewer mode, same-origin checks and no automatic retry.

Acceptance: the existing gateway suite and dashboard JS tests pass with the
service environment; Voice Lab's own locked tests/build pass; isolated artifact
smokes and Plotloom extraction/client checks pass. A bounded browser journey
proves playback, seeking, original-byte download and fixture submission.

### 4. Make selective verification and releases explicit

- Put exact working build/test/run commands in each service README and connect
  them through the operations entrypoint. Use existing tooling; add at most small
  wrappers if needed, not a monorepo orchestrator.
- Document a change-impact matrix:

  | Change | Required verification / deployment scope |
  | --- | --- |
  | Dashboard presentation | Dashboard Python/JS tests, affected browser journey, dashboard image only |
  | Shared package/dependency/resource | Gateway and dashboard tests plus both artifact smokes; deploy only changed serving artifacts |
  | Gateway API/storage/lane | Gateway tests plus affected Plotloom/Lab contract tests and dashboard schema test; coordinate related releases only when their contract changes |
  | Voice Lab control service | Lab tests/build and gateway admission/take tests; no engine rebuild absent an engine change |
  | Model/runtime configuration | Separate qualification; excluded from this plan |

- Describe deployments by source revision, artifact identity, lockfile and
  configuration paths, using existing receipts. Avoid new version registries,
  runtime metadata endpoints or a promise that every component releases together.
- Preserve existing exact service-directory admission in
  `tests/test_extraction_contract.py`; update only demonstrably necessary checks.
  Do not weaken it to accept arbitrary service files or leak model/media/secrets.

Acceptance: an operator can identify the smallest affected checks and restart,
reproduce an artifact, and restore its predecessor without touching unrelated data.

### 5. Verify and deploy the packaging-only candidate safely

The owner approved this stage on 2026-10-22, subject to the director's quiet-window
coordination below. Keep one source owner and use one bounded independent
review after a stable candidate; no unattended delegation.

1. Run focused service checks first. On the stable candidate, run the full gateway
   suite, dashboard JS tests, Voice Lab tests, service artifact smokes and focused
   Plotloom extraction/transport regressions. Test the ARM64 images on Spark
   before promotion; use temporary storage/fake backends for non-serving smokes.
   Broader Plotloom/frontend suites are needed only if their source/build contract
   changes or the focused results reveal an integration risk. No hosted CI.
2. Obtain the director's quiet-window confirmation before any serving restart.
   Record serving image/config identities and check the live shared lane, both
   service job states and native backend queue. Active, queued or uncertain work
   blocks replacement; preserve it and wait rather than canceling or resetting it.
3. Replace the dashboard first and verify real private HTTPS health, job detail,
   preview/seek and download against retained bytes. Restart only that container.
4. At a fresh idle checkpoint, replace the gateway packaging artifact. Verify
   health/readiness, existing job/status/output access, lane reconciliation and
   Voice Lab connectivity. No live generation is expected for this packaging-only
   change; readiness is not a claim of renewed creative/model qualification.
5. Leave ComfyUI, SGLang, Voice Lab, inference environments, model assets, credentials,
   Tailscale routing and all persistent data in place. No schema migrations, state
   resets or automatic data backups are part of this slice. Existing retention
   continues normally.
6. If checks fail, restore only the affected preceding image/config at a safe idle
   point. Do not copy/reset databases or clear uncertain dispatch state to make
   rollback appear successful. Escalate if safe rollback would require those actions.
7. Record local verification, exact deployed artifacts, operational gaps and
   rollback references in one receipt. Commit scoped changes locally; stop before
   product integration, merge, push or any hosted CI. Keep the separate integration
   hold explicit for the eventual main-task handoff.

## Exclusions and stopping conditions

No repository extraction; service/package renaming; wholesale test/document move;
Plotloom authoring/UI changes; new generation modes; new scheduler; model upgrades;
quality tuning; retention changes; new compatibility machinery; Kubernetes or
general release framework. Do not rewrite historical evidence as current acceptance.

Completion means independent reproducible builds, enforced ownership, documented
selective verification, and safe deployment of unchanged behavior. Any requirement
for a public contract/schema change, inference-runtime restart or new product
integration returns to the owner as a scope decision rather than being absorbed.

## Write and runtime coordination

The owner explicitly requested coordination with `narrative-forge main`.
On 2026-10-22 the director confirmed separate specialist source ownership and no
overlap with its creator-completion work. Do not edit the director's retained
checkout, installed Plotloom, authoring source or root locks. Reconcile shared
documentation indexes and assign a unique ADR number at eventual integration.
The director's live native-image/H3 UI journey blocks dashboard/gateway cutover
until it confirms a quiet window; local packaging and offline tests may proceed.
That window was explicitly released after the director cancelled its new native
run without starting H3. Dashboard and gateway packaging were replaced serially;
the receipt records preservation, serving identities and the released window.
