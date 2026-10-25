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

The first cleanup scope is the five explicitly revoked absent QA projects:
`12f15ed8-fe6b-489e-adc4-77c1f517f669`,
`765ce4d9-12e3-4d96-8944-b49ba381fdf2`,
`e03aca22-d335-47c9-ac06-5d92af0ce9a9`,
`eee1ddaa-b047-460a-9987-703d678a295c`, and
`f03a5e3d-6a75-4f5c-b29a-21420ce9a7b6`. The preflight contains 59 of 144 attempts;
the other 85, including 66 on missing but unrevoked projects, are outside scope.
The source implementation does not itself apply that live cleanup.

The same cleanup retires the completed shared-runtime migration's historical
coverage-mapping verifier/inventory and the unused `runtime.recover_runtime_jobs`
helper with its exclusive protocols/tests. Current behavior, extraction and
shared-runtime safety tests remain; production startup still uses
`ProjectRunDispatcher._reconcile_project` → `generation.reconcile_startup_jobs`.
Old local CI evidence and superseded package deletion is a separate operator
step: the manager removed only the approved old run/CI and 938 recovery/wheel
artifacts (2,472 files, 1,553,317,147 logical bytes); the b63 fallback package and
modified copied source checkout were preserved.
