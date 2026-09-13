# Project-folder storage: breaking cutover and portable recovery

Revision 1 — **Approved implementation plan** (2026-09-13). Approved by the user;
implementation has not started. Baseline inspected: clean `main`,
`162061d5ec0b735b40d34c94c6a66da5c52bc25c`.

## 1. Outcome and settled decisions

Each story project has one live, self-contained folder under Git-ignored
`outputs/`. Copying a safely closed folder, or restoring an application-created
snapshot, into a fresh compatible installation restores its saved state, drafts,
history and locally retained media without the former shared project database.
Credentials and running external services are supplied separately.

This is a breaking storage change: archive old projects unchanged and start fresh.
Do not build a legacy project importer, shared-project-database compatibility
mode, legacy URI relocation layer, or dual-write path. Preserve credentials,
public provider settings and existing paid-provider accounting at cutover.

MiniMax H3 becomes the default development video backend through its existing
typed adapter. No Spark gateway changes, remote retention changes, provider
fallback, new model behavior or paid trial is included. Preserve explicit profile
selection and author-owned aspect policy. No automatic seven-day deletion is
implemented; retention eligibility for selected assets remains future work.

## 2. Storage and ownership contract

```text
plotloom/
├── .env                              # server secrets; never in project copies
├── data/
│   ├── application.sqlite3           # small installation-wide control store
│   └── legacy-archives/<UTC-time>/    # unchanged old working sets + inventory
└── outputs/
    ├── <UTC-time>__<project-uuid>/
    │   ├── project.json               # immutable identity/format manifest
    │   ├── project.sqlite3            # authoritative project state
    │   ├── assets/<hash-prefix>/<hash> # owned immutable, content-addressed bytes
    │   ├── runs/<UTC-time>__<run-id>/  # text/image/video evidence and handoffs
    │   └── review/                    # named local review aids
    └── .snapshots/<project-uuid>/<UTC-time>__<snapshot-id>/
```

- Use UTC `YYYYMMDDTHHMMSSffffffZ` and UUID identifiers; allocate directories
  exclusively, never overwrite collisions. Project creation time and folder name
  remain stable when the user edits the title. Discover projects by validated
  manifest, not by parsing the directory name. Hidden operational directories
  are not projects.
- `project.sqlite3` owns Brief, canonical revisions/heads, lifecycle, drafts,
  runs/attempts/repair lineage/seals, image/video jobs, reference decisions,
  selections, reviews and approvals. One project per database; reject mismatches.
  `project.json` contains format version, project ID, creation timestamp and fixed
  relative database location—not duplicated mutable title/status/content.
- Retain SQL transactions and existing domain validation. Split persistence by
  project vs application responsibility, reusing domain/service logic rather than
  rebuilding it. Initialize a clean project schema and application schema; remove
  legacy project migration/compatibility branches from the new runtime. Preserve
  historical documentation as historical, not executable compatibility promises.
- Public backend configuration used by an operation is frozen in the project,
  including adapter/profile/compiler versions. Credentials remain server-side or
  session-only. Never copy `.env`, authorization headers, signed media URLs or
  provider credentials into project/snapshot files. Intentional private endpoint
  configuration is local sensitive configuration, not GitHub evidence.
- Application storage owns reusable provider profiles/selection, preferences,
  global accounting and installation-only dispatch/ownership leases. It contains
  no authoritative project content. A project directory/catalog index is rebuildable
  by scanning manifests; missing application storage cannot prevent offline project
  recovery. Missing accounting must disable paid dispatch rather than create a
  fresh allowance. Global profile changes affect only new requests.
- Every asset needed to restore a project is physically contained in its folder.
  No symlinks, cross-project hard links or external `file://` dependencies; dedup
  is within a project only. Persist artifact identity/hash and confined relative
  paths, not machine-specific absolute paths. Runs reference owned assets rather
  than repeatedly copying them. Evidence files are immutable; database state is
  authoritative for current status, never a competing mutable `status.json`.
- Import reference bytes into project ownership before admitting dependent work.
  Image handoff packages live beneath their project's run directory. Continue
  the specialist's exact-path copy/verify/delete staging workflow; update its
  package-location expectations and pins for the new format, with no legacy path
  support. Ambiguous/failed staging cleanup remains fail-closed and reportable.
- Prevent workers, polling results and delayed browser requests from crossing
  project ownership. Route all operations by project ID to a project handle/store;
  retain a rebuildable run-to-project lookup for existing run-ID routes. Retain
  current public project IDs and endpoint behavior where it remains meaningful;
  no project-wide search or mutation against every database on each request.

## 3. Drafts, close, snapshot and restore

### Drafts

Persist allowlisted editor payloads—not whole UI/session objects—per project,
editor scope and entity ID, with base canonical revision, draft revision and
updated timestamp. Include Brief/four-stage editors, visual-intent edits and
image-generation direction drafts. Exclude API-key fields.

Autosave after 750 ms idle; flush on blur, project/stage navigation and close.
Show `Saving`, `Draft saved`, `Save failed` and conflict states. Canonical Save
and Approval remain explicit actions; saving canon clears only the exact committed
draft revision. Server CAS rejects stale draft revisions with 409. Keep the losing
buffer available for explicit comparison/reapply; never silently overwrite or
discard it after a canonical revision changes. New projects obtain a durable
folder/ID before editable draft state is created.

Use browser session storage only as best-effort protection for unacknowledged
edits; server acknowledgement defines durable recovery. On reconnect/reload,
offer reconciliation of a differing local buffer. Snapshot/export flushes the
requesting client's edits first; it cannot include another client's unacknowledged
typing. State that boundary in the UI and keep before-unload warnings when needed.

### Close and consistent copy

Add explicit project Close, separate from lifecycle Archive. Close flushes drafts,
blocks new dispatch, quiesces local writers, checkpoints/closes SQLite handles,
and releases the project lock. If jobs remain nonterminal, refuse with a clear
busy reason and offer existing stop/cancel/reconcile controls; do not imply that
local cancellation stopped a remote request. Finder copying is supported only
after successful close and with no specialist writing into its run directory.

Provide a safe snapshot while a project is open. Under a project write/publication
barrier, use SQLite's backup API to capture a committed point-in-time database
and the exact referenced immutable file set. Include drafts and complete published
exchange/evidence files; exclude locks, SQLite sidecars and unfinished temporary
files. Pin referenced bytes against deletion until copying completes. Active
specialist package publication must quiesce or return a retryable busy result;
do not snapshot a half-written manifest.

Build into a private temporary directory under `.snapshots`, verify database
integrity/foreign keys and all file hashes, then atomically publish the finished
snapshot directory. Include a versioned manifest with project ID, snapshot ID,
database hash and complete relative-path/hash inventory. A failure leaves the
live project unchanged and no snapshot advertised as complete. The snapshot is
self-contained; do not embed other snapshots recursively.

### Restore and remote work

Restore copies a closed new-format project folder or verified snapshot into a
temporary directory beneath `outputs`, validates format, SQLite integrity,
project identity, file confinement and complete referenced bytes, then publishes
atomically. Reject symlinks, traversal, missing/corrupt data and unsupported
schema versions before registering the project. Never execute supplied SQL,
extensions, scripts or manifests as instructions. Unknown folders stay visible
as errors, not silently converted or substituted with demo projects.

Preserve project/run/job IDs on restore. If that project ID already exists,
return conflict without merging or overwriting. Opening the existing copy or
explicitly duplicating it are separate user actions; duplication follows current
canonical-content copy semantics and does not duplicate remote jobs or accounting.

Restore/startup never automatically submits or replays a generation. Installation
dispatch leases are not portable; imported jobs enter a recovery-required control
state without rewriting historical attempts. A known provider ID can be explicitly
reconciled or retrieved using the recorded backend identity plus separately
configured credentials. Unknown submission remains unknown. Expired/missing H3
remote output is an explicit availability error, not automatic regeneration.
Already downloaded project-owned video remains usable after gateway expiry.

Global paid accounting must survive the split without cross-database atomicity
claims: a globally unique attempt/dispatch identity reserves funds/seconds in the
application store before the project records dispatch. Failed intermediate steps
retain conservative reservations; reconciliation may release only proven
pre-dispatch claims. Restore cannot replenish budgets or duplicate a consumed
identity. H3 does not consume the Atlas allowance, and missing H3 configuration
must fail explicitly rather than fall back to Atlas.

### Interface additions

- Project-scoped draft list/read/update/discard endpoints carrying draft/base
  revisions; preserve canonical save APIs.
- Project close/open operations with `project_busy` and ownership errors.
- Snapshot create/status operations returning an operation ID and completion
  manifest, with an application-owned output location rather than an arbitrary
  destination supplied by the browser.
- Local restore operation from an explicitly selected folder, available through
  an operator CLI; UI imports only directories staged under a fixed local import
  inbox. Do not introduce unrestricted filesystem browsing or path-based writes
  through the HTTP API. UI exposes snapshot progress and a copyable local location.
- Add `PLOTLOOM_OUTPUTS_DIR` and `PLOTLOOM_APPLICATION_DATA_DIR`. Remove old
  shared-database/artifact/exchange/legacy-root settings from the new runtime;
  fail with a clear configuration error if explicitly supplied. Installed wheels
  use their configured application root, never infer another repository from cwd.

## 4. Delivery checkpoints and acceptance

1. **Contracts and isolated vertical slice:** record the breaking storage ADR;
   implement project/application stores, directory registry, relative artifacts
   and one end-to-end project creation/edit/run flow against temporary storage.
   Remove obsolete persistence paths as their callers are replaced; the delivered
   runtime must not expose old/new selectable storage modes.
2. **Complete project-owned workflow:** route all authoring, text repair, image
   handoff, video, review and lifecycle paths through project handles. Implement
   draft autosave/conflicts and close. Exercise two projects concurrently without
   cross-project results, assets or drafts; shared paid allowance remains enforced.
3. **Portable recovery:** implement snapshots and restore; prove a project can
   reopen from its folder/snapshot with the original application database and
   paths unavailable. Preserve full lineage/drafts/selections and play stored
   media. Test crash points, corrupt/missing assets, identity conflicts, running
   jobs, lost credentials and remote-output expiry. No implicit network dispatch.
4. **Breaking cutover and closeout:** stop all local project writers, including
   specialists and other director tasks; inventory exact configured old working
   sets. Copy unchanged legacy projects/media/exchange to ignored
   `data/legacy-archives/<UTC-time>` and verify hash inventories and SQLite
   backups. Export only installation settings/accounting to the new application
   store, preserving credential sources and immutable ledger identities/events.
   Switch local storage configuration to fresh outputs; no old project import.
   Remove exact redundant old working copies only after archive verification and
   report their recoverable archive paths. Do not touch unrelated files, global
   Codex storage, existing backups or Spark gateway data.

Verification is proportional: focused contract/draft/snapshot/specialist tests
during edits; one independent scoped safety/integration review on stable code;
then locked Python suite, frontend unit/typecheck/build/static freshness, real
FastAPI/file-SQLite Playwright journeys, wheel build and isolated installation
smoke. Update extraction-root tests narrowly for `outputs` and new modules;
do not weaken V1 exclusion. Test new-format recovery, not legacy compatibility.

Required browser journey: create project → edit/autosave → explicit save →
generate with offline providers → review/select fixture media → snapshot while
open → close → remove original registry access → restore → inspect drafts,
lineage and playable media. Also cover stale-tab conflicts and process restart.

Live-provider calls are not required or authorized for this storage milestone.
H3 default routing is proved with its typed fake transport and configuration
tests. Synthetic assets establish storage/playback only, never creative quality.

## 5. Authority, publication and remaining limits

After approval, the director may sequence these checkpoints through bounded Relay
assignments without confirmation for routine implementation/test decisions. Use
Terra-high by default, one source owner at a time, and no competing shared-main
merges; coordinate with the H3 specialist before integration. Do not alter gateway
source/deployment to solve a local-storage problem. Prepare assignments against
fresh exact baselines and include all intended write paths before dispatch.

Escalate only a required expansion in compatibility, destructive scope, security,
provider spending or user-visible semantics. Preserve work on plugin refusal;
use supported recovery rather than silently widening a ticket or rewriting history.

Commit each completed implementation checkpoint; after final acceptance merge/push
without force, record CI separately and retire workers. Publish a concise storage
entrypoint, cutover/archive inventory, versioned restore contract and secret-free
verification receipt. Reconcile ADR 0032, the capability matrix and development
docs; mark old pilot instructions historical rather than rewriting their evidence.

A project folder protects against loss of the old installation, not loss of its
own disk. Safe snapshots are local recovery copies, not off-machine backups.
Folder portability does not promise simultaneous writable copies or cloud sync.
Seven-day retention, archive deletion, legacy import and broader collaboration
remain explicitly outside this implementation.

## Checkpoint 1 record (2026-09-13)

Baseline `1141269772c2303deab4a860f5f402ce54fe7a18` was clean. The bounded
construction result is [ADR 0040](../adr/0040-project-folder-storage-boundary.md):
an unwired `project_storage` composition seam with a manifest-discovered project
directory registry, one project SQLite database plus confined owned assets per
project, and a separately rooted application store for public profile selection
and global accounting. Focused temporary-root tests prove two projects can edit,
run an offline deterministic fake, and reopen after the former shared project
database is unavailable. They also prove artifact confinement and reject
credential-shaped profile configuration.

This is not a cutover and introduces no shipped legacy/new selectable mode.
The retained runtime, pilot data, provider calls, gateway, and old storage paths
remain unchanged. Exact remaining work is recorded in the checkpoint receipt:
[project-folder-storage-checkpoint-1](../verification/2026-09-13-project-folder-storage-checkpoint-1.md).

## Checkpoint 2A correction record (2026-09-13)

Baseline `460ff5685e0f25168d30f20f38fbf060c99bb0c7` was retained as a rejected
construction result, not an accepted storage design. Its temporary mixed
`SQLiteRepository`, private project-ID rebinding, and success-only evidence
projection made the temporary harness the actual lifecycle authority. The
replacement runs the existing `PipelineEngine` and `LifecycleJobRunner`
directly against each project's `project.sqlite3` through a bound canonical-text
repository. The project schema is intentionally bounded: it keeps text run,
repair, canonical, and startup-recovery facts while provider profiles,
selection, global accounting, and unrelated media/review surfaces remain
application-owned or outside this checkpoint.

Focused fixtures now prove two independently reopened project homes, direct
four-stage success, durable failed/cancelled/quarantined/outcome-unknown
evidence with no partial canonical heads, stale exact-repair refusal,
foreign-project rejection, secret-free bearer/none broker operation, and no
automatic replay after an interrupted dispatch. The retained runtime and data
remain unwired; no migration, import, cutover, provider call, or live network
work is authorized by this correction. See [the 2A direct receipt](../verification/2026-09-13-project-folder-storage-checkpoint-2a-direct.md).

## Checkpoint 2B authoring-draft record (2026-09-13)

The direct project composition now owns an allowlisted Brief/four-stage draft
row in each format-4 `project.sqlite3`. The row is keyed by editor scope and
entity ID and carries base canonical revision, draft CAS revision, payload, and
timestamp. The project-folder authoring factory resolves every route through
the exact manifest-discovered handle; it does not store or return profile,
credential, session-key, or arbitrary UI/session objects. A canonical save is
still explicit and can consume only the exact server-acknowledged draft
revision. Stale draft saves receive 409 without overwriting either client
buffer.

The shared retained runtime remains unchanged. The test-only factory and the
existing workbench components prove 750 ms autosave, blur/navigation flushing,
two-tab conflict preservation, canonical non-mutation until explicit Save, and
server-draft recovery after a file-SQLite process restart. Visual-intent/media
drafts, close/quiescence, snapshots/restore, live routing, and all retained-data
cutover work remain deferred. See [the 2B receipt](../verification/2026-09-13-project-folder-storage-checkpoint-2b-authoring-drafts.md).
