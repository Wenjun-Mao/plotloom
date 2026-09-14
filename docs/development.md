# Plotloom developer guide

## Product flow

```text
ProjectBrief
  -> StoryBible
  -> StoryGraph (DAG + joins)
  -> SceneBeatPlan
  -> Storyboard (Shot + ShotBeatLink)
  -> package-owned, versioned media prompt compiler
  -> one-shot image/video tasks
```

A valid first run may advance through all four canonical stages. Editing a stage creates a new revision and marks downstream stages stale; it never spends provider credits until the user explicitly starts a rebuild.

## Repository shape

```text
src/plotloom/       Python domain, API, persistence, prompts, migrations, built UI
frontend/           React/TypeScript source, unit tests, and Playwright tests
tests/              Python contracts, integration tests, and release boundary gates
docs/adr/           durable architecture decisions
docs/roadmap/       capability-based progress tracking
```

The frontend build writes directly to `src/plotloom/static/`, so an installed wheel is a complete single-process local application.

## Development commands

```sh
uv sync --all-groups
npm --prefix frontend ci

# terminal 1
uv run plotloom

# terminal 2
npm --prefix frontend run dev
```

The production server defaults to `127.0.0.1:8775`; the Vite server defaults to `127.0.0.1:5173`. Open `/v2/` on either origin. `PLOTLOOM_API_ORIGIN` changes the Vite proxy target.

### Direct project-folder recovery

The direct project-folder composition can create a verified local snapshot from
its workbench. Restore is intentionally an operator command, not an HTTP path
or a browser file picker:

```sh
uv run plotloom restore --source /absolute/path/to/snapshot-or-closed-project --outputs-dir /absolute/path/to/outputs
```

It restores only a format-6 closed project folder or a verified format-1
snapshot, preserves the project ID, and refuses an existing identity. The
operator supplies no provider credentials or application database; restore
never dispatches or replays remote work.

## Data and secrets

- A source checkout defaults to `data/plotloom.sqlite3` and `data/artifacts/`.
- An installed wheel uses the OS user-data location: `~/Library/Application Support/Plotloom` on macOS, `%LOCALAPPDATA%\\Plotloom` on Windows, and `$XDG_DATA_HOME/plotloom` or `~/.local/share/plotloom` on Linux.
- Only a source checkout loads its trusted repository-root `.env`; host environment values override it.
- Named text-provider profiles persist complete public configuration and an
  optimistic revision. API keys are never part of a profile.
- The compatibility `PUT /api/v2/provider-settings` request must include the
  active text profile ID and its expected revision. A stale projection receives
  `409` rather than overwriting a newer named-profile change.
- A browser key is scoped by profile ID, lives only in the current tab's
  `sessionStorage`, and is sent as `X-Plotloom-Session-API-Key` only for that
  profile's bearer-authenticated probe or text-run start, rebuild, repair, and
  resume request.
- A run freezes the exact profile ID, revision, resolved preset, capabilities,
  extraction/correction policy, and public hash when queued. Updating or
  activating a profile changes only future runs.
- A safely recoverable run that depended solely on a browser key remains
  queued after a server restart. Reopening it from the same browser tab (or
  clicking **继续排队运行**) explicitly re-supplies that ephemeral key; the
  server never persists it to make restart recovery convenient.
- Named profiles apply only to text generation. Image and video tasks freeze
  their own global public settings and cannot inherit a text profile.
- Provider response envelopes are sanitized before persistence: exact outbound
  credentials and secret-shaped fields are redacted, while numeric token usage
  remains available for audit. Cancelling a queued run before worker start still
  releases its ephemeral key lease, and deleting a profile clears that
  profile's browser-session key.
- Remote instances must remain private or use an external authentication layer.

### Managed imported stills (P0)

- The non-generative import endpoint accepts only JPEG/PNG bytes for an active,
  saved project. It preserves the original and a separately hashed display
  derivative in the configured artifact root; it never invokes a provider.
- `PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_BYTES` defaults to `8388608` and accepts
  values from `1` through `67108864`. `PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_PIXELS`
  defaults to `24000000` and accepts values from `1` through `100000000`.
  Restart the server after changing either setting.
- A reviewed keyframe freezes an explicit visual-intent revision and a current
  storyboard Approval. A still preview can cover any nonempty contiguous subset
  of one scene; the authored frame duration is played unchanged. The four-image/
  three-shot P0 scenario is test evidence, not a runtime limit.
- Media-bearing projects cannot be permanently deleted yet: the API refuses
  with `project_managed_assets_present` before mutation. Do not attempt manual
  blob cleanup; media-aware erasure is a follow-up.

### Manual Codex image jobs (P1)

- P1 has no provider key or automatic bridge. Set one explicit
  `PLOTLOOM_IMAGE_EXCHANGE_ROOT` on the same host as Plotloom and the assigned
  Codex specialist. For a source checkout, use the ignored local root
  `data/image-exchange`; `data/plotloom.sqlite3`, `data/artifacts/`, local
  `data/review-packs/`, and that exchange are the active project-local storage
  entrypoints. Do not use a source path outside `data/`, a database directory,
  artifact root, or a broad home directory as this exchange root.
- A verified retained-data relocation may set
  `PLOTLOOM_LEGACY_ARTIFACT_ROOTS` to the exact former artifact root (multiple
  roots use the platform path separator). This is a read-only compatibility
  allowlist: immutable `file://` records under that root resolve to the same
  relative bytes below the configured current artifact root. It does not permit
  arbitrary file URIs and does not rewrite database history.
- The UI requires a nonblank creator-reviewed presentation/refinement change
  before it prepares an approved single-shot job. It freezes that change with
  canonical facts; use the normal storyboard editor and reapproval for narrative
  changes. A reference refinement is available only for the current reviewed
  keyframe of that Shot.
- A mismatched reviewed keyframe can instead enter a `keyframe_adaptation` job.
  Its package names the frozen `source_keyframe`, target H3 profile and exact
  required pixel geometry. The specialist must fill that complete canvas
  without padding; delivery remains an unselected managed candidate until the
  author reviews and selects it.
- **Copy assignment** exposes one database-frozen `package/` projection and a
  separate `delivery/` inbox. For v2 jobs the specialist reads both
  `package/request.json` and `package/completion-manifest.example.json`; the
  request includes the resolved narrow entity/cue/state context and, for a
  refinement, the exact reviewed VisualIntent revision. It writes only complete
  JPEG/PNG files under `delivery/outputs/`, then publishes
  `delivery/completion.json` last. It must report the actual built-in-imagegen
  prompt, hashes, tool/task evidence, and limitations without credentials.
- **Refresh deliveries** revalidates the confined package against its frozen
  database request, then validates the delivery server-side. It never generates,
  approves, selects, resends, or follows a browser-supplied path.
  Invalid/partial/tampered delivery remains diagnosable; a late result is kept
  as inapplicable history. Editing the selected role-specific VisualIntent after
  Copy also makes a refinement inapplicable. Explicit P0 selection remains
  required before preview.

### Character references and cross-shot review (P1.5)

- See [ADR 0030](adr/0030-character-reference-decisions-and-cross-shot-review.md).
  Create a project-scoped reference decision from managed assets before preparing
  a v3 job for a Shot whose `characterIds` are nonempty. One primary and up to
  two complementary assets are frozen by asset hash, canonical character context
  and explicit reviewer decision; rename alone does not transfer identity.
- A v3 package maps every visible character to distinct `character_identity`
  references. The specialist must view them and attest exact viewed hashes plus
  code/skill provenance in the version-2 completion manifest. `parent_output`
  remains a refinement reference, never a replacement identity contract.
- Character-reference proposals are exploratory and Story-Bible scoped. They
  never create a Shot, Approval, selected reference or reviewed keyframe. Use
  the repository skill at `.agents/skills/plotloom-image-specialist` only with
  the frozen package and write completion data only in its delivery directory.
- Built-in ImageGen may stage files under user-level Codex storage. After a
  complete package delivery, the specialist skill copies each exact returned
  path into `delivery/outputs/`, validates the full manifest and hashes, and
  removes only that exact direct staging file. It never glob-deletes staging
  directories; unsafe, ambiguous, incomplete, or mismatched files remain and
  are reported.
- A selected v3 generated keyframe with visible characters needs an explicit
  human same-person review before a still animatic can be created. Replacing or
  revoking a reference makes dependent jobs, reviews and previews stale while
  retaining their historical evidence. V2/P0 history remains readable and does
  not claim identity review retroactively.

### Private MiniMax-H3 video gateway (P2-H3)

The operator and maintainer entry point is the
[MiniMax-H3 gateway manual](operations/minimax-h3-gateway-manual.md).

- The Spark deployment is a private, bearer-authenticated gateway in front of
  loopback-only ComfyUI. Plotloom never sends it a ComfyUI graph, model path,
  or browser-provided endpoint. See [ADR 0033](adr/0033-private-minimax-h3-gateway.md)
  and [ADR 0034](adr/0034-provider-neutral-video-adapters-and-local-h3.md).
- Enable exactly one reviewed video backend at a time. For H3, set
  `PLOTLOOM_ENABLE_H3_GATEWAY=true`, `VIDEO_PROVIDER=minimax_h3_gateway`,
  `VIDEO_MODEL=minimax_h3_fp8_turbo4_480p`, the private Tailnet
  `VIDEO_BASE_URL`, and a server-only `VIDEO_MODEL_API_KEY`; restart Plotloom.
  The browser never sees or stores that key.
- H3 uses the reviewed catalog in [ADR 0036](adr/0036-minimax-h3-profile-catalog.md):
  832x480, 960x544 and 1280x704 landscape; 576x1024 (the default), 608x1088
  and 704x1280 portrait. Every profile is 124 frames / 24 fps (about 5.17
  seconds) with native audio. A new job defaults to an aspect-matched reviewed
  keyframe and rejects a mismatch before reservation or provider contact.
  The author can prepare a matching crop/adapted still, or explicitly choose
  **allow letterbox** for a deliberately padded input canvas. That narrow
  choice freezes `contain_pad`; it does not skip provenance, selected-keyframe,
  profile, output-geometry, identity or review checks. Plotloom probes received
  media and rejects a browser-playable output that misses the frozen H.264/AAC
  profile as `h3_output_profile_mismatch`.
- H3 is local capacity-bound by its gateway queue and does not reserve or
  reset the historical paid Wan 100-second ledger. It still freezes an
  adapter/version/request/seed/identity/approval snapshot and never retries an
  uncertain submission.
- A native AAC track does not make dialogue accepted. Review the resulting
  candidate for intelligibility, lip sync, performance, and cross-shot
  continuity before explicit selection. The one-line Mandarin probe is bounded
  evidence only; it is not a general voice-consistency claim.

## M1.5 generation contracts

- A Story Graph run freezes topology before dispatch. For Scene Beats and
  Storyboard, model-facing fragment aliases are local to one response; the
  trusted binder converts them into deterministic UUIDv5 canonical IDs from
  the frozen selector and validated local order. Selector-owned
  `storyNodeId`/`sceneId` values are omitted from the model schema and injected
  by the binder; attempts to send them are rejected as extra fields.
- Storyboard fragments use a closed `primaryShotLocalIdByBeat` map whose exact
  Beat-ID keys are frozen by the schema. The binder creates PRIMARY links,
  while optional supporting links remain explicitly SUPPORTING; one shot may
  cover a continuous multi-beat span without weakening exact primary coverage.
- Join continuity keys are explicit in the frozen join contracts. Incoming
  fragments must provide them in exit state and join fragments in entry state;
  aggregate validation remains the cross-shard authority.
- Planner input estimates are UTF-8 byte bounds, despite the legacy field name
  `estimated_input_tokens`. They protect declared byte budgets only. The
  selected provider/model owns exact tokenization and context-window rejection.
- A profile's `textContextWindowTokens` must match the provider's effective
  capacity for one request. Some multi-slot runtimes divide a configured total
  context pool across parallel slots; verify their runtime properties or probe
  output after changing slot/concurrency settings. A response ending at that
  smaller physical limit is a deployment/profile mismatch, not a reason to
  relax extraction or add model-specific retry behavior.
- Migration `0006` safely terminated old non-terminal runs whose plans predate
  the frozen profile/topology contract; operators must submit a fresh run.
  Migration `0007` persists stable run `failureCode` and `failedStage` for
  pre-attempt, provider, recovery, and aggregate failures, and backfills the
  exact 0006 terminalization reason without parsing arbitrary historical prose.
- A work unit is `quarantined` only after a persisted model response exhausts
  its explicit content corrections. Known provider, contract, storage, or
  local failures are `failed`; uncertain post-dispatch outcomes remain
  `outcome_unknown`.
- Correction 1 repairs the previous final response. Correction 2 uses a
  distinct frozen strategy that rebuilds from the closed schema, so a
  deterministic model is not sent the same failed packet twice. Extraction
  correction requires ASCII JSON delimiters and escaping; the extractor does
  not silently rewrite full-width punctuation.
- Current corrections use the issue-selected, versioned
  directive/evidence/schema contract in
  [ADR 0022](adr/0022-executable-correction-contracts.md). Primary attempts
  freeze its compiler versions; each correction also freezes hashes of the
  selected directives, compact evidence projection, and narrowed response
  schema. Unknown semantic issue codes fail closed.
- The durable validation artifact always retains the complete issue list. A
  correction may defer a derived continuity sequence issue only while a named
  invalid-state or non-finite-value blocker prevents an exact boundary fact;
  only the hashed executable subset enters that correction prompt/schema, and
  the next attempt is validated from scratch.
- All structured prompts are presence-strict: every property named by a
  schema `required` array must be emitted, including explicit empty/null state
  fields. Native JSON Schema is a probed profile capability, not a replacement
  for local presence/schema/semantic validation; some compatible servers only
  partially enforce nested `$defs`. Provider-facing schemas deterministically
  inline non-recursive local references; ambiguous or recursive shapes fail
  before dispatch. Generation schemas also remove `default` annotations:
  domain defaults remain available for hand-authored edits, while model output
  must explicitly carry every required field.
- `textMaxConcurrency` is an execution ceiling. The current runner is
  deliberately serial and may use less concurrency without changing the
  frozen profile or plan.
- For array-shaped assistant content, only typed `text` and `output_text`
  parts are eligible final output. Reasoning and unknown part types remain raw
  evidence and cannot enter correction or canonical content.
- Exact work-unit repair is an immutable child execution defined by
  [ADR 0015](adr/0015-exact-work-unit-repair.md). The server alone decides
  eligibility, freezes the failed unit and reusable fragments, and re-plans
  every downstream stage. The legacy stage-level repair endpoint remains only
  for compatibility and must not be presented as exact repair.

## Verification order

```sh
uv run pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --exit-code -- src/plotloom/static
npm --prefix frontend run test:e2e
uv build --wheel
uv run python scripts/smoke_installed_wheel.py dist
```

The E2E fixture uses temporary SQLite and artifact storage, empties provider keys, and never contacts a live provider. Install Chromium once with `cd frontend && npx playwright install chromium`.

The distribution contract builds and probes a wheel in isolation. It verifies
that all eleven prompt templates, the production UI, the current migration
head, LICENSE, and NOTICE are packaged, and that an installed release ignores
an unrelated working-directory `.env`.

## Live profile conformance

The checked-in fixture suite never contacts a model. After saving one or more
real profiles, run the production four-stage pipeline against the locked
Chinese baseline with:

```sh
uv run python scripts/conformance.py --qualify-m15 \
  --profile <first-profile-id> --profile <second-profile-id> --runs 3
```

Without `--qualify-m15`, the command is an explicitly labelled diagnostic
probe and cannot complete M1.5. The JSONL receipts omit endpoints, model names, prompts, responses, IPs and
keys, while carrying a fixed `workloadHash` and one-based `sampleOrdinal` for
repeatable qualification. The command fails unless each profile completes all
samples atomically, keeps every unit within one primary plus two correction
attempts, and reaches at least 10/12 first-pass stages. The initial real 3×2
gate passed on 2026-09-03 with 12/12 first-pass stages for both profiles; see
the [secret-free receipts](verification/2026-09-03-m15-conformance.jsonl) and
[conformance.md](conformance.md). Any changed `workloadHash` requires a fresh
qualification run.

Strict mode evaluates the two profiles concurrently while preserving serial
sample and work-unit execution inside each profile. This reduces wall time
without changing profile-local concurrency or deterministic receipt order.
