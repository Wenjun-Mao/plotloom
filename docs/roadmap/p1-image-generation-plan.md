# P1 — Codex image jobs with a manual handoff

Status: **Implemented locally — revision 2**, 2026-09-11. The user approved
this revision and authorized implementation with “Looks good, go.” The bounded
candidate has a real original and reference-based built-in-imagegen refinement
through the manual exchange; see the [verification receipt](../verification/2026-09-11-p1-codex-image-jobs.md).
This is not a production release or external-provider qualification. Supersedes
the unapproved external-endpoint-first revision 1.

## Outcome and stopping point

**Prepare → Copy assignment → Generate → Refresh → Select.**

Open an approved shot, review its visual brief, and prepare a frozen image job.
Copy the assignment to the reusable Codex image specialist. The specialist uses
built-in imagegen and delivers images into the designated job inbox. Refresh
Plotloom to validate/ingest them, explicitly select a candidate, and reopen it
in the existing still preview after backend restart. Repeat once as a targeted
reference-based refinement, preserving the original image and request.

Manual handoff is the intended P1 mechanism, not a fake API test. Real job-linked
specialist results have generation provenance; ad-hoc images remain P0 imports.
Automatic bridging, external image-provider qualification, Q and P2 are not gates
for this slice. No specialist success message automatically approves an image.

## Baseline and prerequisites

- P0/creator-review checkpoint: `4563636`, `codex/p0-imported-still-preview`.
- Primary checkout at planning: `e19692d`, `codex/m1b-alpha`. Histories diverge
  through three primary-side Flow documentation commits; do not assume fast-forward.
- Before implementation, inspect current remote/local state, preserve both
  histories on a local integration branch and verify the resulting baseline.
  Unexpected source divergence needs director review. No main-branch changes.
- Old Flow envelope failures remain historical workflow limitations; no metadata
  deletion, rewritten envelope or force-close is authorized.

Governing records: [roadmap](story-to-playable-alpha.md),
[ADR 0012](../adr/0012-approved-storyboards-and-production-units.md),
[ADR 0016](../adr/0016-versioned-authoring-quality-gates-and-approval.md),
[ADR 0027](../adr/0027-managed-imported-still-preview-contract.md), and
[ADR 0028](../adr/0028-agent-operated-image-jobs.md).

## Scope and consequential decisions

### Frozen request and copyable ID

- Implement minimal one-shot ProductionUnit/Snapshot admission, not a raw-Shot
  shortcut or renamed P0 preview. Freeze canonical hashes/revisions, current
  Approval/gates, selected intent, references/roles/verified bytes, compiler version
  and the versioned `codex_specialist` execution contract. Retain cue/audio context
  without claiming still-image output produces audio.
- Derive an editable visual proposal from authored fields; no new LLM service.
  Narrative changes use canonical editing and reapproval. Zero-reference jobs are
  valid when none are required. Required references/edit targets cannot be dropped.
- Persist immutable inputs and a collision-resistant opaque job ID before Copy
  assignment becomes available. Repeated copying returns the same job, not a new
  generation. Refinement creates a new job referencing its parent output/hash.
- The copied assignment includes the ID, a configured locator and a short reading/
  delivery instruction. An ID is a lookup key, not a credential or success receipt.

### Exchange boundary

- Initial scope: one explicitly configured same-host exchange root accessible to
  Plotloom and the specialist, with database-frozen input projections and delivery inboxes.
  No hard-coded developer home path. Package all required reference bytes.
- Resolve registered jobs only under that root. Refuse path traversal, symlink
  escapes, cross-project mismatches and arbitrary browser-supplied URLs/paths.
  Specialist writes only its assigned inbox, never SQLite or canonical records.
- Different-machine use needs deliberate package transfer or shared-path mapping.
  Report unavailable locations honestly; do not assume paths are shared or expose
  a local server. Packaging/sync automation is not part of initial P1.

### Specialist execution and Refresh

- The on-demand specialist reads the brief/references, generates with built-in
  imagegen, then returns originals and a versioned delivery manifest: job/request
  hash, actual prompt passed to the tool, reference/output roles, filenames/hashes,
  available tool/task evidence and limitations. Never invent model/seed/cost fields.
  Prompt changes are disclosed; the specialist cannot silently change narrative facts.
- Write temporary outputs first; publish a final completion manifest only once
  all output files are complete. Refresh invokes server reconciliation. No daemon,
  file watcher, automatic Codex trigger or continuous model polling is required.
- Treat delivery metadata/files as untrusted. Verify identity, confined paths,
  exact declared file set, bytes/hashes, observed MIME/dimensions and bounded raster
  decoding before atomic publication of managed candidate records.
- A copied package is readable by the local specialist, not magically immutable.
  Refresh must rederive and recheck its complete request/instruction/reference
  projection against the frozen database request before it accepts any delivery.
- Refresh is idempotent across concurrency/restart. Same delivery identity with
  different content is a conflict, not overwrite. Partial/invalid deliveries remain
  diagnosable without partially published candidates. Ingestion retry never generates.
- Distinguish prepared/awaiting delivery, incomplete/rejected delivery, imported,
  cancelled and stale applicability. Copying is not evidence of running; silence
  or timeout is not definite failure. Never silently resend an uncertain job.
- Export is the manual authorization cutoff; repeat copying rechecks currentness.
  Revocation/cancellation cannot recall a previously copied package. Preserve late
  results/history, mark them inapplicable and block automatic selection.
- Reuse P0 comparison, revision-checked explicit selection and stale-preview rules.
  Preserve originals, refinements and job lineage independently of current choice.
- Terra coordinates; built-in imagegen renders. No API key, silent API/CLI fallback
  or promise of unlimited generation. Durable briefs/visual decisions live in files,
  not solely in one growing task history. Another task may take over the same role.
- Manifest hashes establish consistency, not model authenticity. Live acceptance
  requires observed actual tool execution, not only a task's prose success claim.

## Checkpoints

1. **Prepare/copy.** Bind integrated P0 baseline; implement/document production and
   job contracts, admission, frozen export and Copy assignment. Focused tests reject
   stale/forged inputs. Verify the specialist can read the complete job package.
   This is the only supporting-contract checkpoint.
2. **One real return.** Implement delivery validation, Refresh ingestion, candidate
   display and explicit selection. Immediately attempt a real specialist job through
   that path. If access/tool availability blocks it, resolve that boundary or replan;
   do not expand into an automatic bridge or general provider framework.
3. **Refine and accept.** One targeted refinement, candidate comparison, selection,
   preview and same-data backend restart. Finish safety regressions and one independent
   review, retain evidence and update the capability matrix. Stop at P1.

Initial pilot: two requested outputs, one original and one refinement. Failed or
uncertain calls are reported, not invisibly retried. Extra iterations require a
specific reason and bounded instruction; no unsolicited batch.

## Acceptance evidence

- Tests: stale/forged Approval, zero/required references, cross-job/project identity,
  path escapes/symlinks, malformed/oversized images, tampered hashes, partial writes,
  duplicate/concurrent Refresh, conflicting manifests, cancel/revoke/edit before
  and after handoff, late delivery, crash/restart and ingestion-only retry.
- Migrations preserve P0 data, originals, historical hashes/approvals and previews.
  Legacy direct-provider/video paths remain blocked. Packages contain no API keys,
  credentials or unrelated files. No raw-Shot production bypass.
- Real FastAPI/file-SQLite browser journey: prepare/copy → specialist generation
  → Refresh → compare/select → preview → stop/start same backend/data → reopen.
  Duplicate Refresh creates no duplicates; stale deliveries retain clear lineage.
- One original and one actual imagegen refinement bound to job and artifact hashes.
  Director/reviewer checks narrative/identity/composition constraints and usefulness
  of refinement. Disclose deficiencies; storage success is not creative acceptance.
- Stable candidate: `uv run --locked pytest -q`, frontend unit/type/build/static
  freshness, real-browser E2E, wheel/install smoke and scoped secret checks. Focused
  checks while editing, broad gates on the stable candidate, affected repeats only.
  Retain secret-free receipts/screenshots in existing verification docs.

## Non-goals

Automatic bridge, external provider qualification/billing, general media-profile
platform, sync service, asset library, batch/ranking, video/audio, multi-shot
production, Q completion, authentication/reverse proxy, remote administration,
user data deletion/reset or V1 reuse. Future transports can reuse this protocol.

## Execution authority and escalation

This approved technical revision authorizes one coordinator delivery. Prepare
one fixed assignment and fresh supported Flow
run with the complete source/test/migration/static/config/ADR/roadmap/verification
write scope admitted. Do not reuse the blocked run. Coordinator owns breakdown;
director owns intent/acceptance. Routine tests/fixes do not require user confirmation.

Escalate material scope changes, public exposure/new accounts, rights/likeness
uncertainty, paid API use, consequential creative choices, unsafe integration
conflicts or repeated failure after a targeted correction. Record local checkpoints,
evidence gaps and available usage deltas. Main merge/push, release and unsupported
Flow workarounds need separate authority.
