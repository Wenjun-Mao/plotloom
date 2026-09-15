# Step 3 storage transition

Executed 2026-09-15 from the accepted `d54360a` preflight on local `main`.
This receipt records a preservation-first local transition, not a legacy
project import or a release/creative acceptance claim.

## Result

- Archived the exact 29-file legacy source set to the ignored local directory
  `data/legacy-archives/20260915T180623436377Z` without deleting or relocating
  any source files.
- Preserved the root legacy store's two public text-profile records and active
  selection in fresh `data/application.sqlite3`. The local records retain the
  supported public endpoint, model, adapter, capability, and policy values;
  no endpoint values, credentials, or profile payloads are tracked here.
- Preserved the retained Wan pilot exclusively as raw archived material. Its
  ledger, eight events, all video-job identities/states (including
  `outcome_unknown`), and historical media/exchange/review tree were neither
  imported, reconciled, replayed, nor translated into H3 or paid accounting.
- Created fresh `outputs/` and completed a provider-free current-format
  create/save/close/reopen/snapshot/restore proof. The restored copy used a
  separate ignored destination and a new application store, not an old
  application database or any legacy path.

## Boundary and preservation evidence

Before mutation, the cutover owner checked Codex tasks, local listener state,
and open descriptors for both active SQLite databases and their sidecars. No
active Plotloom writer, listener, or source-file handle was found. The only
repo-cwd Python process was idle with no relevant handle or listener, so it was
not treated as a service to stop.

The archive contains byte-hashed raw copies of the root database, its WAL/SHM
sidecars, the four historical backups, and the entire retained-pilot tree. It
also contains separate committed SQLite backups for the root control store and
retained pilot. Raw-source/archive inventories matched; both source databases
and both committed backups passed `integrity_check` and `foreign_key_check`.
The source inventory was rechecked after the transition and remained unchanged.

The ignored private manifest at
`data/legacy-archives/20260915T180623436377Z/private-manifest.json` records the
full hashes/inventory, local profile export, archive-only Wan identities/events,
proof project locations, and rollback boundary. It is intentionally not tracked
because it contains local-sensitive public configuration values.

## Configuration and accounting boundary

The repository `.env` was not copied, exported, or edited; its credential values
and host-variable precedence remain unchanged. Neither current storage-root
variable needed an explicit dotenv entry because the approved repository defaults
already resolve unambiguously to `outputs/` and `data/`. Obsolete storage
variables remained absent.

The fresh application store has zero global accounting entries and no initialized
paid allowance. H3 remains fail-closed with no paid-provider fallback. The proof
created no dispatch, provider call, paid budget, or accounting claim.

## Direct recovery proof

The ignored operator proof created the project labelled **Step 3 provider-free
recovery proof**, durably saved a Brief draft, closed and reopened it, captured a
current-format snapshot while open, then closed it. The existing operator restore
command restored that snapshot into an ignored `.local/relay/` destination. A
fresh provider-disabled runtime opened the restored project and its saved draft.
No legacy source, original application database, or provider configuration was
passed to restore.

The initial import attempt stopped before publishing `application.sqlite3` or
creating `outputs/`: a serializer reformatted an otherwise byte-identical
selection timestamp during validation. The exact raw archive and isolated
staging database were retained. The resumed transition compared the persisted
profile/selection records directly before atomic publication; source files still
matched their original inventory.

## Rollback boundary

Do not restore over current paths. To investigate or recover, copy the verified
raw archive to a separate operator-selected location, validate its inventory and
committed SQLite backups there, then choose a separate recovery action. No source
copy was deleted as part of this transition.

## Verification

| Check | Result |
| --- | --- |
| One-off operator preflight, archive, source hash comparison, SQLite integrity/foreign keys | Passed |
| Exact root profile/selection preservation and fresh zero-accounting store | Passed |
| Provider-disabled create/save/close/reopen/snapshot/isolated restore | Passed; no dispatch or provider call |
| Legacy raw archive integrity | Passed separately; no legacy import attempted |
| Independent attended read-only safety review | Passed; no P0–P2 findings |

This was direct operational recovery/integrity evidence. It intentionally did
not run broad product suites or call a live provider.

## Independent safety review

An independent attended read-only review of the archive, application store,
operator evidence, and current source found no blocking issue. It independently
confirmed all 29 approved legacy files remain byte-identical to their raw archive
copies; the current application store contains exactly the root profile records
and selection with no routes, paid-accounting, or dispatch state; and the Wan
pilot remains archive-only. No files, product state, or provider were changed by
the review.
