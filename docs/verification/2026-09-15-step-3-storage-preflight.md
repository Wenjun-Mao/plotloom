# Step 3 storage-transition preflight

Captured 2026-09-15 at `889d19f`. This is the approved Step 3 **read-only
preflight**, not the storage transition. It neither started a runtime nor
changed data, configuration, permissions, services, SQLite state, credentials,
or provider state.

## Result

The current runtime contract is ready for a fresh project-folder destination:
the repo `.env` does not set either current storage-root variable, so the source
checkout defaults resolve to `outputs/` and `data/`; `outputs/` is currently
absent. The existing `data/` root instead holds legacy shared-runtime material
that must be archived before it can be treated as fresh application storage.

| Logical target | Count / format | Required preservation |
| --- | --- | --- |
| Root legacy store | One SQLite database, WAL/SHM sidecars, four SQLite backup files | Two enabled public text-profile identities and one active selection; archive the complete raw set unchanged. |
| Retained pilot | One legacy SQLite database with WAL/SHM, 8 immutable media assets (6 PNG, 2 MP4), 7 exchange files, 2 review files, snapshot/log | One active project; 1 delivered image job; four video jobs (2 ingested, 1 cancelled, 1 `outcome_unknown`); one historical ledger and eight events. |
| Current-format destination | `outputs/` absent; `data/legacy-archives/` absent | Create only after a verified archive and approved, secret-free application export. |

Both active SQLite files returned `PRAGMA integrity_check = ok` through
read-only/query-only inspection. No process held a file descriptor in `data/`
at the observation point. Neither fact establishes a quiescent, consistent
cutover boundary.

The retained pilot has managed `file:` URI references and historical narrow
old-root relocation evidence. The preflight does not follow, rewrite, import,
or validate those references against external locations. Archive the retained
pilot unchanged and retain its historical context; no current runtime may use a
legacy URI relocation layer.

## Credential and ownership boundaries

The available repo-dotenv credential sources are `TEXT_MODEL_API_KEY`,
`IMAGE_MODEL_API_KEY`, `VIDEO_MODEL_API_KEY`, and `ATLASCLOUD_API_KEY`; only
source names and availability were checked. Their values, hashes, endpoints,
and any private configuration were neither read nor recorded.

ADR 0046's project-folder composition owns current writes: per-project
`project.sqlite3` and owned media sit under `outputs/`, while the new
`data/application.sqlite3` owns only secret-free public profiles, active
selection, run routing, and accounting. `RunSecretBroker` keeps credentials
process-local. H3 remains fail-closed when unavailable and must not fall back to
a paid provider.

## Cutover blockers requiring director resolution

1. There are two legacy public-profile/selection sources: the root store has
   two enabled profiles and one selection, while the retained pilot has one
   enabled selected profile. The authoritative export and collision behavior
   cannot be inferred safely.
2. The retained pilot's ledger/event identities and `outcome_unknown` video job
   need an approved archival/export representation. Do not reset, replenish,
   replay, or reconcile historical paid/Wan accounting; H3 receives no paid
   fallback.
3. No open file descriptor is not writer quiescence. The cutover owner must
   stop/confirm all local runtime, specialist, and other project writers before
   a source copy or SQLite backup is trusted.

## Smallest safe transition proposed

1. Quiesce and identify all writers; recheck nonterminal/unknown state without
   starting or reconciling work.
2. Allocate an exclusive UTC directory under `data/legacy-archives/`, then
   hash-inventory and copy exactly the root legacy set and retained-pilot tree
   unchanged. Compare source/archive inventories and verify SQLite backups,
   integrity, and foreign keys after quiescence.
3. Export only director-approved secret-free profile/selection and accounting
   identities/events to a fresh `data/application.sqlite3`. Do not export
   project content, credentials, endpoint settings, URI relocation rules, or
   media bytes.
4. Leave the default separate roots in place unless the director selects new
   explicit roots: create fresh `outputs/`, retain the verified archive beneath
   `data/legacy-archives/`, and ensure obsolete storage variables remain
   rejected.
5. With providers disabled, prove fresh project creation plus profile/accounting
   preservation and provider-free archive inspection/restore. Confirm no legacy
   import/discovery and no dispatch/replay. Keep archive manifests for rollback;
   removal of any redundant old copy is a later explicit decision.

## Evidence and limits

The ignored detailed inventory is `.local/relay/0281c35d-45c8-4cf6-80bb-bb23629e3a0e/inventory.md`.
It records logical paths, sizes, schema/status counts, source categories, exact
read-only command classes, and rollback checks without secrets or private
endpoint values. This docs-only assignment did not run product suites.
