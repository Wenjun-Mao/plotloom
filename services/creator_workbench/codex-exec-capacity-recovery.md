# Explicit local image-capacity recovery

UNKNOWN means Plotloom lacks supported terminal evidence for the exact attempt.
It does not mean the process is still alive, that ImageGen ran, or that it did
not run. A local concurrency slot and a remote outcome/spending reservation are
different facts. Never resend an UNKNOWN task or infer success/no-dispatch from
process death, cancellation, exit 0 alone, a transcript fragment or bridge health.

Current readiness reports login/runtime state separately from `localCapacity`.
That read-only snapshot shows actual persisted limits, held text/image slots,
publication-revoked UNKNOWN image holds and the count of previously retired local
UNKNOWN holds. When every occupied image slot is such a revoked UNKNOWN hold and
the actual image limit is exhausted, fresh automatic material launch refuses
before sending text and points to `exec-capacity-retirement-preview`. Ordinary
busy/running/unrevoked-UNKNOWN/queued scheduling is unchanged. Readiness is not a
provider or creative E2E claim; it never retires, retries or dispatches work.

## Eligibility and guarantees

This is an explicit administrator operation for one exact UNKNOWN image attempt
on an already permanently revoked and deleted project. The source owner checks
the original home is positively absent (not replaced, symlinked or inaccessible),
and every recorded worker, CLI and separate validator PID and whole process group
is positively absent. Missing identities, present/reused PIDs, permission failure
or unresolved spawn ownership refuse. A rejected preview explains its blockers.
No user-entered process-proof claim can grant authority.

The commit rechecks exact installation, project, attempt/status, revocation, slot,
queue and process/home facts under the existing publication fence and SQLite
transaction. It atomically appends an immutable hashed receipt and removes only
that attempt's local slot. It does not change UNKNOWN/status bytes, reserved image
outputs, image budget/spending holds, original process/session/terminal evidence,
receipts/manifests, permanent revocation or disabled queue. It does not drain a
queue, publish an output or raise the 4-total/2-image default limits. Reduced
persisted installations keep their own exact limits.

## Supported operator commands

Activate the reviewed build only at a quiet checkpoint. Use the existing running
workbench container's `codex` shim; it already has the protected authenticated
bridge configuration. Do not copy or print the token or run alternate SQLite
scripts. Find the exact container read-only:

```sh
docker ps --filter label=com.docker.compose.project=plotloom-creator --filter label=com.docker.compose.service=workbench --format '{{.ID}} {{.Names}}'
```

Replace `<container-id>` with that single verified running container. For the
first retained historical attempt, inspect:

```sh
docker exec -i <container-id> codex exec-capacity-retirement-preview --packet-json '{"projectId":"765ce4d9-12e3-4d96-8944-b49ba381fdf2","attemptId":"06e80972-9dde-41ff-be71-b477c1477465"}'
```

Inspect `eligible`, `blockers`, `localCapacityState`, `remoteOutcome`,
`imageBudgetState`, `reservedImageOutputs` and `previewHash`. If eligible, replace
`<fresh-preview-hash>` with that exact returned 64-hex hash and explicitly commit:

```sh
docker exec -i <container-id> codex exec-capacity-retire --packet-json '{"projectId":"765ce4d9-12e3-4d96-8944-b49ba381fdf2","attemptId":"06e80972-9dde-41ff-be71-b477c1477465","expectedPreviewHash":"<fresh-preview-hash>","reason":"Explicitly retire positively absent local processes on this revoked deleted QA project; preserve UNKNOWN and spending reservations."}'
```

The second separate preview/consent uses project
`f03a5e3d-6a75-4f5c-b29a-21420ce9a7b6`, attempt
`3405616d-55a3-4f81-9dee-01e79550f25b`; never reuse the first preview hash.
Each success returns `localCapacityState=retired`, `alreadyRetired=true`, an exact
receipt, `remoteOutcome=preserved_unknown` and unchanged reserved-image facts.
The private ledger retains the complete pre-retirement attempt/slot/revocation
facts, fresh absence observations, maintenance source/hash and commit time.

The CLI sends once and does not retry a lost acknowledgement. Re-run the same
read-only preview first: an exact committed retirement returns the original
receipt. An explicit exact repeat of the same consent also returns that receipt;
changed facts/reason or a restored slot refuse. Historical proof is not a claim
that its numeric PIDs remain unused forever. Readback grants no new release.

## Continuing the current project after a source change

Source installation changes the frozen executor profile. Under the original
source, finish/adopt in-flight text first; then explicitly cancel the current
automatic run. Queued never-spawned image attempts must obtain native
`not_started` evidence and reconcile their owning proposal/checkpoint. Require
the existing continuation preview to be eligible; UNKNOWN or delivered/unadopted
predecessor work still blocks. Do not rewrite old execution pins or policies.

After quiet activation and reviewed local retirement, use the visible same-project
Continue action. It freezes fresh authority, inherits adopted text and other
material through exact origins, retains lifetime budgets, and creates only
remaining work. The new material QA grant must bind the actual successor run and
bundle. No new project or repeated completed text is needed when those native
continuation prerequisites hold.

The historical instruction-access and content-ownership faults have separate
[evidence](../../docs/verification/2026-10-18-image-instruction-recovery.md) and
[repairs](../../docs/verification/2026-10-19-automatic-image-content-ownership.md).
Their fixes are already installed. This recovery does not certify the historical
remote outcomes or broaden the no-dispatch telemetry parser.
