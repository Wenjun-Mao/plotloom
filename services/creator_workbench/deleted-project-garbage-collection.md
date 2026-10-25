# Deleted-project host garbage collection

Use `exec-project-gc-preview` and `exec-project-gc` through the existing native
bridge for one permanently revoked, deleted project at a time. This erases its
host attempt/status/budget/history rows, disabled queues and confined private
attempt evidence. The project revocation remains permanently, denying late
publication, cancellation resurrection and admission. Other project rows,
application grants, selected media and supported snapshot/restore stay untouched.
There is no queue drain, resend, remote-outcome decision or accounting refund.

The original revoked home must be absent; a replacement directory, symlink or
current manifest elsewhere refuses. An unrevoked project, enabled queue, slot,
validator or active execution refuses. UNKNOWN needs an existing exact immutable
local-capacity retirement receipt; collection reads that historical proof without
probing numeric PIDs again. It erases that history without declaring success,
failure or no dispatch. It cannot retire capacity implicitly.

Activate the reviewed source/package at quiescence. The host bridge imports its
handler and supervisor persistently, so restart it under the normal controlled
activation procedure before using new commands. Use the running workbench's
`codex` shim with its existing protected bridge configuration; do not copy tokens
or edit SQLite directly. Find the single running container read-only:

```sh
docker ps --filter label=com.docker.compose.project=plotloom-creator --filter label=com.docker.compose.service=workbench --format '{{.ID}} {{.Names}}'
docker exec -i <container-id> codex exec-project-gc-preview --packet-json '{"projectId":"<exact-project-uuid>"}'
```

Inspect `eligible`, `blockers`, exact `attemptIds`, `privateFileCount`, `privateSymlinkCount` and
`previewHash`. The hash binds installation filesystem identity, permanent
revocation, every selected ledger/child row and private file identity/content.
Apply only that exact current preview:

```sh
docker exec -i <container-id> codex exec-project-gc --packet-json '{"projectId":"<exact-project-uuid>","expectedPreviewHash":"<fresh-preview-hash>"}'
```

This operator operation requires local quiescence throughout preview/apply; it
does not promise protection against concurrent same-user filesystem rewrites.
Apply holds the existing publication fence and SQLite write transaction. It
checks row ownership before filesystem erasure, removes evidence before database
commit and leaves revocation intact. Attempt-root/ancestor symlinks, hardlinks,
special files, foreign private paths and changed previews refuse. Child symlinks
are bound by their own identity/link text and unlinked without following or
reading their targets (including native Codex sandbox helper links). There is no archive or retained copy of erased logs.

If interrupted while erasing files, SQLite rolls the rows back and the already
erased files remain erased. Read a new preview to bind the remaining evidence,
then explicitly apply it. A lost acknowledgement is never retried automatically:
read the preview again. An empty `attemptIds` list after success permits a fresh
explicit no-op apply; old preview consent never authorizes a changed target.

The initial cleanup completed on October 25, 2026 using implementation
`44dc00893a7a3171710283f28a66127929b8f711`, after reviewed package qualification and
a controlled bridge/workbench reload. All five exact previews were applied:
59 attempts, 15 disabled queues, 17 process-exit rows, two retirement receipts,
one recovery row, 299 private files and 60 inert child links were removed.
Both old UNKNOWN attempts now return `not_found`; reserved image units are zero.
The five revocations and all other 85 attempt rows match their preflight hashes.
Those 85 include 66 on missing but unrevoked projects, which were outside scope.

All eight current project databases, 672 project tables, 263 persistent project
files, application tables and 15 protected settings/configuration fingerprints
were unchanged. The service is healthy and its HTTPS player and qualified
JavaScript still respond correctly. Focused GC/recovery/tooling checks, an
independent 126-case review and isolated installed-wheel smoke passed. The two
pre-existing startup-isolation failures were stale metadata-GET expectations;
the tests now follow ADR 0218's inspection contract while checking strict
authority/mutation refusal, healthy recovery, index exclusion and query purity
for open and Frozen corrupt projects. This correction changes tests/docs only.

The same cleanup retires the completed shared-runtime migration's historical
coverage-mapping verifier/inventory and the unused `runtime.recover_runtime_jobs`
helper with its exclusive protocols/tests. Current behavior, extraction and
shared-runtime safety tests remain; production startup still uses
`ProjectRunDispatcher._reconcile_project` → `generation.reconcile_startup_jobs`.
The manager removed the approved old CI run and superseded recovery/wheel
artifacts. A single current source/wheel recovery bundle is kept in
`.local/current-qualified-recovery/`; its `manifest.json` is authoritative for
the current revision and hashes. The obsolete copied CI checkout was then
reviewed against retained main: all 26 changed/untracked paths were already
integrated or superseded, with no unique missing changes. It was removed without
archive: 9,349 regular files, 18 inert links and 390,940 allocated KiB (about
382 MiB). Git independence and absence of open handles/container mounts were
checked before removal.

The obsolete autosave/Freeze QA capture directory `.local/autosave-evidence/`
was also removed without archive: 434 files, 432,182,520 logical bytes and
422,928 allocated KiB (77 Markdown, 191 PNG, 78 WEBM, 76 ZIP and 12 JSON files).
It contained no database, project manifest, working code or Git data; no open
handles or active container mounts remained. Historical qualification outcomes
remain in the verification receipt, while capture files were not retained.

Separately, the October 25 compatibility review classified all 28 database
copies and 19 project IDs in five legacy QA workspaces as unsupported.
All five workspaces were removed without archive: 4,712 regular files, 77 inert
links and 1,292,800 allocated KiB (about 1.23 GiB); no mounts, open descriptors
or process references remained. Current projects (eight, 672 tables, 263 files),
application/host state (85 attempts), 15 settings fingerprints, container/bridge
identities and service health were unchanged.
