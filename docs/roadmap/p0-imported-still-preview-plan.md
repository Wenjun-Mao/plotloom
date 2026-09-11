# P0 — Imported assets and reviewed still preview

Revision: **2 / Approved correction candidate**, 2026-09-11. The original
frozen assignment delivered commits `4dabfc5` and `dce8614`; the acceptance
correction remains in the same Flow run and preserves those commits. The
four-image/three-shot scenario remains the bounded fixture, while the product
contract permits a creator-selected nonempty contiguous scene subset. No P1,
provider, merge/push, or broad cleanup authority is implied.

## Outcome and stopping point

In Plotloom, import four real images, compare two alternatives, select keyframes
for three consecutive shots in one scene of an existing reviewed storyboard,
and play a labelled still animatic. Refresh and restart the application: original
bytes, provenance, selections and the frozen preview remain available. Replace
one image or edit the board: old preview history is preserved and applicability
changes visibly, not silently.

Four images/three shots define the acceptance fixture, not a product-wide limit.
The cheapest safe direct attempt uses controlled imports and existing authoring/
Approval, without any provider integration. Stop after this journey and its
proportionate verification. P0 does not establish cinematic video quality,
branching playback, independent text qualification or media-provider readiness.

## Governing decisions

Follow [ADR 0026](../adr/0026-story-to-playable-product-direction.md) and its
explicit amendments to ADRs 0012/0016. Retain ADR 0023 bounded delivery and the
canonical, immutable-history and secret boundaries in repository `AGENTS.md`.

### Ownership

| Concern | Authority |
|---|---|
| Story facts, shot order/duration, dialogue, continuity | Existing canonical stages and validators; no ownership transfer |
| Proposed portrayal/details | Minimal versioned visual-intent record with exact available source references; narrative changes require canonical edits |
| Original bytes | Existing content-addressed ArtifactStore, verified before publication/use |
| Import origin/rights/derivation | Separate immutable managed-asset records; no fake generation run |
| Exploratory preference | Versioned candidate association, explicitly not approved production selection |
| Reviewed keyframe selection | Repository-owned revisioned binding with project/context/Approval checks |
| Still sequence | Immutable versioned preview projection captured from one coherent set of reviewed inputs |
| Current/stale/revoked applicability | Derived from current lifecycle, authority and dependency fingerprints; never rewrite historical manifest |
| Missing/corrupt media | Storage/serving observation, not a synonym for stale or failed generation |

## Scope

### Managed imports and storage

- Require a saved active project. Accept JPEG/PNG uploads through a controlled
  endpoint; validate actual format and decoding, with documented configurable
  byte/pixel limits and boundary tests. Reject unsupported/animated content for P0.
- Preserve originals exactly. Generate separately identified display derivatives
  as needed for orientation and safe metadata handling; never overwrite originals.
- Reuse the byte store. Verify the existing addressed blob on deduplicated import
  before publishing metadata. Fail explicitly on corruption; do not silently
  repair shared storage or fabricate a usable asset.
- Store project ownership, observed MIME/dimensions/size/hash, producer=import,
  origin declaration, known/unknown rights information and original/derivative
  relationships. Different import declarations may refer to the same bytes.
- No browser-supplied local path, arbitrary remote URL, path traversal or fake
  provider provenance. An image made in the development conversation is a declared
  import; unknown generator details remain unknown.
- Project-scoped asset IDs drive serving. Validate referenced content before
  presenting it as usable, serve correct types, and keep original metadata out of
  normal preview derivatives. Retain the existing private local/Tailscale model;
  project scoping is not a claim of authenticated multi-user security.

### Intent, selection and reviewed preview

- Use a minimal typed visual-intent record, not a fifth canonical stage or a
  full proposal generator. Allow import/candidate comparison before storyboard
  Approval; keep selected visual preferences distinct from reviewed shot bindings.
- Show what an alternative is intended to vary and declared additions. Offer
  keep/neither/refine without silently applying story changes. Narrative-bearing
  details must be resolved in canonical authoring before reviewed use; semantic
  compatibility is an explicit creator judgment, not proven by image hashing.
- Implement only roles exercised by the pilot: protagonist/location references
  and shot keyframes, with explicit identity/composition/style intent where used.
  Do not build a universal asset catalog or many mandatory reference sheets.
- Reviewed selection transactions check active project, exact READY board and
  upstream revisions, current Approval/gates, expected binding revision, valid
  asset ownership and explicit reviewed compatibility context. Selection races
  produce conflicts; preserve the candidate and UI draft. No automatic rebasing.
- Create a preview in a coherent repository transaction against expected source
  and selection identities. Freeze board/upstream revisions, Approval and gate
  identity, relevant visual-intent/selection revisions, artifact hashes, ordered
  shot IDs/authored milliseconds, projection version and hash. Authoritative
  values are server-derived, not accepted as client claims.
- A selection need not regenerate a preview. An existing preview remains pinned;
  its currentness is evaluated on load. Changes to relevant inputs or revocation
  block new reviewed preview admission; historical viewing remains clearly marked.
- The preview may cover a contiguous subset of one scene. A missing keyframe can
  be shown as a labelled gap, never counted as complete. Do not claim a finished
  video or use the preview as a complete ProductionSnapshot.

### Workbench experience

- Add a focused asset/selection/preview surface within the existing storyboard
  workbench, preserving its drafts, URLs, selected entity and conflict behavior.
- Compare candidates, select a shot keyframe explicitly, then create/open the
  frozen animatic. Basic play/pause, seeking and previous/next shot are enough.
  Still duration comes from authored timing. No audio recording, TTS or video.
- Show a compact continuity summary from existing facts/selected intent where
  available; do not generate missing geography or emotional facts in UI code.
- Refresh restores the selected preview identity. Missing/corrupt/stale/revoked
  states are distinct and actionable. Old history is accessible, not silently
  replaced by current selections. Archive remains readable and blocks mutations.

### Retention and project lifecycle — proposed P0 tradeoff

Reject individual deletion of assets referenced by any retained selection,
derivative or preview, including historical records. Avoid a general garbage
collector. Clean bounded abandoned import temporaries without touching shared
managed blobs. Unreferenced candidates may remain retained during P0.

Until media-aware whole-project erasure is implemented, **permanent-delete must
refuse projects with managed assets before any deletion**, with a stable
`project_managed_assets_present` reason and a clear UI explanation. Existing
asset-free deletion stays unchanged. Do not promise erasure or orphan media.
Track full media-aware deletion as a follow-up before calling lifecycle support
complete for media projects; it is not hidden behind a successful response.

Project duplication must not clone media/preview bindings implicitly. Keep its
existing canonical-prefix copy boundary and disclose that media stays in the
source project. Cross-project assets cannot be selected via copied identifiers.

## Non-goals

No image/video provider calls, remote downloads, media-worker activation,
ProductionUnit compiler, native audio, branch sessions, automatic visual-proposal
generation, full asset library, general invalidation/event system, dynamic plugins,
batching, text qualification runner changes, story-prompt fixes, V1 integration,
deployment authentication, production-data reset or user-level configuration edits.

Keep existing provider API/repository/worker hard stops closed and independently
tested. Do not make run IDs nullable throughout generation artifacts to fit
imports. Preserve V1/V2/V3 snapshots, seals, plans, hashes and historical tasks.

## Delivery checkpoints

One implementation owner; these are product checkpoints, not separate agents.

1. **Bounded foundation plus direct import:** add only required managed records,
   migration, import/serve and selection seams; exercise a real image round trip.
   After this support checkpoint, go directly to the workbench outcome, not a
   second infrastructure expansion. Focused negative cases run alongside changes.
2. **Visible P0 journey:** integrate candidate comparison, reviewed selection and
   frozen still preview; complete the four-image/three-shot refresh/restart
   journey, including replacement/staleness. Fix failures at the owning boundary.
3. **Stable candidate acceptance:** one independent review, required broader tests,
   retained safe screenshot/receipt and progress update. Reopen review only for
   specific findings or material changes. Stop without starting P1.

Likely seams: focused new managed-media domain/application modules under
`src/plotloom/`, existing `artifacts.py`, repository/API integration and the next
Alembic migration (head currently `0012`; recheck before assigning a number),
`frontend/src/pages/StoryboardPage.tsx` plus cohesive components/client contracts,
focused backend/frontend tests and one real FastAPI Playwright journey. Avoid
unrelated refactoring of large files. The coordinator may refine names/layout
and endpoint details, not the authority or acceptance contract.

## Acceptance evidence

Focused checks must establish:

- Byte/hash round trip, bounded real decode, malformed/unsupported/oversized
  inputs, derivative lineage, corrupt-existing-blob rejection, no fabricated run.
- Identical bytes can preserve independent provenance; project-scoped ownership
  prevents cross-project reads/bindings through the public application contract.
- Competing expected revisions cannot both win; selection/Approval/edit/archive
  races produce coherent admission or explicit conflict, never mixed snapshots.
- Deterministic manifest ordering/duration/hash, no false complete result with
  gaps, persistence through restart, immutable old selection/preview history.
- Revoked/stale Approval blocks reviewed admission but permits labelled historical
  viewing; exploratory imports remain independent of storyboard Approval.
- Missing/corrupt blobs are explicit; failed import publication creates no usable
  asset/selection. Referenced deletion and media-project permanent-delete refuse
  before destructive changes; asset-free deletion and duplicate remain correct.
- Provider hard-stop paths remain closed. No new media task, provider request,
  secret access or generation-evidence ownership weakening is introduced.

One browser journey against real FastAPI/file SQLite: use an existing valid
three-shot fixture, inspect it and create an explicit development Approval;
import four real images, compare alternatives, select three, play/pause/seek,
reload, stop/restart the isolated server and reopen the same preview. Replace
one selection; show old preview as historical/stale and explicitly create a new
one. Edit the board and verify current reviewed admission is blocked until
Approval is current again. Exercise the proposed deletion refusal. Preserve
assets and selected preview for inspection; stop the temporary server afterward.
The development Approval is an operator-labelled product action, not a claim of
independent human or formal cinematic review.

Use real JPEG/PNG fixtures. For the creative demonstration, use existing approved
images or images generated directly in the development session after execution
approval; apply the image-generation skill if generating. Do not build image
provider integration to obtain them. No visual result counts as video quality.

Run focused tests during edits. On the stable candidate run:

```sh
uv run --locked pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
uv build --wheel
uv run --locked python scripts/smoke_installed_wheel.py dist
git diff --check
```

Commit regenerated static assets with the candidate, rebuild, then verify
`git diff --exit-code -- src/plotloom/static`. Add no deselection waiver for new
failures; identify existing explicitly skipped pre-production specifications.
Retain a 1440×900 workbench screenshot and concise source-bound, secret-free
receipt under `docs/verification/` with assets in a supporting subfolder. Record
which checks were automatic versus visual and any retained-data location locally.
No credentials, private endpoints or sensitive original-image metadata in public
evidence. Update the capability matrix without promoting Q/P1–P4.

## Execution authority and escalation

After plan approval, the director uses `codex-orchestration:direct` to freeze the
plan into one assignment and dispatch one coordinator. The coordinator may
refine its technical breakdown; the director owns intent and acceptance. Default
delegates to GPT-5.6 Terra, with bounded minimal-context tasks only where helpful.
Do not create a second role-specific plan or continuous polling/monitoring loop.

Admit the actual source/test/frontend/static/dependency files needed by the
chosen breakdown and `docs/adr`, `docs/roadmap`, **`docs/verification` including
its screenshot subfolder** into the assignment's write fence before execution.
Do not repeat the previous omitted-evidence-path failure. Respect any active
plugin recovery constraint; no installed-plugin repair, lifecycle bypass or
retroactive compliance claim. If Flow refuses the correct boundary, report the
exact refusal and stop dispatch; ordinary-Git implementation needs explicit
authorization rather than being silently substituted.

Execution may add necessary package dependencies using existing locked tooling,
run isolated local services/tests and create local checkpoint commits. It may
not reset user data, edit `.env`, reconfigure hosts, run live LLM/media trials,
publish private images/reports, merge `main`, push or claim Alpha release under
this plan. Publication/release remains a separate direction from the user.

Escalate changes to canonical ownership, provider hard stops, permanent-delete
policy, approval meaning, acceptance scope, destructive data handling or external
authority. If the same failure class survives one targeted fix, retain evidence
and reassess the contract rather than expanding retries or infrastructure.

At each checkpoint report outcome, commit/worktree, checks/gaps, next action and
available usage deltas. Disclose missing measurements; no new meter or invented
cost ceiling. A safe pause preserves edits/evidence and stops owned test services.
