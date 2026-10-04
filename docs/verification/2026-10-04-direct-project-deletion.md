# Direct project deletion

Status: independently reviewed and locally qualified; publication and normal
activation in progress. Creator usability acceptance is separate.

Scope: the owner's request to make project deletion available from 项目目录.
Contract: [ADR 0114](../adr/0114-direct-project-deletion.md).
Plan: [bounded delivery](../roadmap/2026-10-04-direct-project-deletion.md).

## Delivered boundary

Every active, archived or closed row exposes **永久删除**. There is no implicit
Archive or reopen step. A DOM confirmation explains irreversible project-owned
text, drafts, media and run-history removal, then requires the full saved title.
The frozen project identity, Brief revision, lifecycle revision and title are
checked under the exclusive lease. Brief revision is not a global media/draft
revision. Existing prepared, nonterminal and uncertain-job guards remain.

The folder layer owns removal of its manifest-bound direct outputs-root child.
It withdraws the manifest before recursive removal can unlink the operation
lock; late openers cannot admit a half-erased home. Link-safe recursive removal
does not traverse external originals or another project. Project-side bytes and
records are erased together; disposable application indexes are cleaned in one
application transaction. Provider settings, financial accounting and exported
snapshots are not deletion targets. Filesystem erasure is irreversible, not a
cross-resource rollback promise. Unknown failures remain unconfirmed outcomes.

Client draft writers suspend new dispatch and join admitted writes before
deletion. Refused admission keeps unsent edits and resumes those queues. Only
confirmed erasure discards local buffers, including caches never registered in
this session. Erasure notifies mounted media consumers so another project's
editor cannot resurrect removed entries from a stale cache snapshot. Deleting
another project does not leave or clear the current workspace.

## Root causes and independent review

Archive-first presentation hid deletion, especially on closed rows. The old
folder guard also prohibited managed media despite current whole-home ownership;
the row-only persistence primitive remains separately protected and is not used
by production deletion. This is a storage-boundary contract update, not shared
asset garbage collection or a caller-specific bypass.

GPT-6.1 Sol / High independently reviewed the stable candidate, read-only. Its
P2 cache-ownership finding was reproduced: unmount A, mount/edit B, erase A's
retained writer, then edit B; B's whole-cache snapshot could recreate A. A
project-scoped cache erasure contract now covers unregistered buffers and all
live consumers. Final scoped re-review found no remaining findings and ran 29
cache/media/review unit checks. The reviewer did not independently run browser
tests or failure-injected filesystem/application erasure.

Initial new-test failures were fixture/interaction errors: non-ASCII idempotency
headers, a nonexistent edit button, asserting a background label before consent
closed, and opening consent before initial workspace ownership settled. Current
checks use ASCII keys and explicit loaded/closed DOM conditions. The broad Python
run also caught three intentionally changed test fingerprints in the assertion
inventory; their assertions were reviewed unchanged, request bodies now bind the
Brief revision, and the historical archive-first clause is explicitly superseded.
Historical baseline evidence was not rewritten.

## Executed verification

Evidence is under `.local/project-delete-2026-10-04/`.

| Check | Result |
| --- | --- |
| New production-boundary deletion checks | 10 passed |
| Focused browser deletion/lifecycle checks | 12 passed; imported-still media erasure also passed |
| Frontend unit suite | 474 passed across 63 files |
| Frontend and browser type contracts | Passed |
| Production build and checked static | Passed; existing large-chunk warning |
| API/new storage module F401 | Passed |
| Archived prompt reader | Passed |
| Wheel build and installed-wheel smoke | Passed |
| Assertion inventory follow-up | Passed |
| Full Python suite | 1,098 passed in 412.31 seconds; existing Starlette/httpx warning |
| Full unfiltered browser suite | 159 passed in 9.0 minutes, two workers |
| Remote CI | Not dispatched yet |
| Whitespace | Passed |

Checked bundle SHA-256:
`b8bd84660165bc0a60ca651a5a594647bd945096519c4c297a7147e3acc36aad`.
Installed-smoke wheel SHA-256:
`15c3904c7e4fbb68e9f7195510985d6bdc9e537c982f256f9403a1cb2f09add5`.

## Preservation and acceptance

No real project deletion is authorized by this implementation request. Both
normal projects are captured through directory metadata, project table rows,
API projections and owned-file hashes, together with application rows and
specialist settings. The owner's already closed 风里的纸飞机 is recorded with
its expected `project_closed` API responses; it is not reopened for inspection.
Initial and intermediate captures compare equal. Activation and cancelled live
consent inspection remain to be recorded.

The Chinese manual is unchanged and deferred until same-day changes settle.
No generation, cancellation, V1 edits, H3 activation, credential changes,
snapshot deletion or retained 8851 mutation belongs to this slice. A broader
read-only audit of older contracts is proposed, not executed or authorized here.
