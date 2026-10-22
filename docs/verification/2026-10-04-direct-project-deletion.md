# Direct project deletion

Status: independently reviewed, locally qualified, published and activated on
normal 8841. Full remote CI is running. Creator usability acceptance is separate.

Runtime source: `359f0256e3e39b32d737a5a9e7eea3bb21d0e14a` on published `main`.

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
| Remote CI | [37242579117](https://github.com/Wenjun-Mao/plotloom/actions/runs/37242579117), running on the exact runtime source with unfiltered `browser_grep=.*`; not yet a passed gate |
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
Initial, intermediate, fresh preflight, before-activation, after-activation and
after-browser captures compare equal. Each project capture includes 74 tables;
the captures retain 2 owned files for 风里的纸飞机 and 67 for 雨停以后, excluding
SQLite transport files and the operation lock. The application capture includes
12 tables. Common capture SHA-256:
`27753689c9efd011fc52d0cdd282f2604384217478eb545dd834bd1f91da4574`.

Fresh read-only `close_blockers` scans returned no blockers for either project;
specialists reported `busy=false` and no active tasks immediately before the
supported manager activation. The manager recreated only normal 8841 and
confirmed the native bridge. Container
`332d33f1f9109999afdf4fb9d1d3193973f4105fa20635a1c6e566a169d9117f`
started at `2026-10-04T23:07:27.723137248Z`, healthy, on image
`sha256:4e85a92abe387053f78ff665d2bb7a75a032973cdc8508ea3c5f7ec387227f69`.
The served `/v2/workbench.js` hash matches the checked bundle above; live OpenAPI
requires title and both revision fields. `/healthz` returns `ok`.

A fresh, background in-app-browser tab verified direct deletion controls on
both existing rows. Opening the closed project's consent did not reopen it;
the empty title challenge kept confirmation disabled. Cancel returned to the
unchanged two-row directory. No delete, open, close, archive, duplicate,
generation or cancellation action was submitted. The temporary tab was closed;
the user's original tab was not reloaded or changed. Saved screenshots:
`live-directory.png` (SHA-256
`ef8c7abff40a4f390d03cb4f38cf3c80f4873c60f058acdaae11b75588533514`)
and `live-delete-consent.png` (SHA-256
`91e77ab2cbd9305a2fd4e8e813df20d4945c8bdfb5ac6bfdc10ccf0fb60978cc`).

Specialist settings remain at SHA-256
`eb97bd1b9ca9779ffeb4b2f6c011c315f9d7b0ca9e7d4abe13a6510d56e7352c`;
the existing bridge token hash remains
`3e1745d3bdd35bef62342a0486365cfb5319dfee443d2b1472394a7c13bb956a`.
The manual hash remains
`c44adfddba45a4db4a3e5e5d0a9fcc376278a3baeaed502f9b8259c934e30db8`.

The Chinese manual is unchanged and deferred until same-day changes settle.
No generation, cancellation, V1 edits, H3 activation, credential changes,
snapshot deletion or retained 8851 mutation belongs to this slice. A broader
read-only audit of older contracts is proposed, not executed or authorized here.
