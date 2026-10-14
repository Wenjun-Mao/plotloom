# 0165 Serial Codex Exec for pre-video autopilot

Status: accepted for the owner-approved serial executor checkpoint, 2026-10-13.

## Context

Pre-video autopilot currently freezes two native specialist chat UUIDs in its
launch policy. Those IDs are checked again by the specialist queue, creative
delivery manifests, image package pins and ordinary-open validation. They are
not generic worker identifiers. The Mac creator bridge submits one bounded
`codex queue` request, but it does not own a process, a CLI session, or the
evidence needed to reconcile a CLI run after a restart.

The CLI transport evaluation established that `codex exec` can run the tested
text and ImageGen flows. It did not establish full-package correctness,
reference identity, process recovery, cancellation, or production delivery.
Its stdout also omitted ImageGen extension events. Treating process exit or a
model assertion as ImageGen proof would therefore weaken the current delivery
contract.

## Decision

1. **Freeze a distinct executor contract for future runs.** A launch policy
   identifies either the existing `specialist_chat` backend or `codex_exec`.
   A CLI profile pins executable identity and version, model and effort,
   supported event capabilities, instruction and validator revisions, finite
   runtime/output limits, and a fixed sandbox/tool profile. A CLI session,
   process ID, or attempt UUID must never be encoded as a specialist chat ID.
   Existing launch policies and manual specialist packages remain evidence
   of the contract under which they were created; they are not rewritten.
   Each prepared image owner writes its top-level `executionContract` from the
   same frozen `specialistPreflight` value. Image attempt keys retain the full
   per-subject checkpoint identity (for example `character-reference:keeper`);
   receipt validation compares against that exact key, not the broader owner
   label.

2. **Keep one immutable job and one durable initial attempt.** Each attempt
   has a unique ID and binds the run, project, operation, frozen request/package
   hashes and executor profile. The project store reserves the job/image
   budget and records the attempt before any host dispatch. A dispatched
   attempt is never resent or replaced automatically. The project transaction
   and the Mac installation reservation are separate owners; neither claims
   atomicity over the other. A terminal attempt records an explicit success,
   failure, or not-started result, the exact process outcome where one exists,
   and the remote-operation outcome. A not-started result has no process,
   session or output identity. Attempt state is stored as immutable validated
   snapshots; each transition reconstructs and validates the whole record.
   Confirmed remote outcomes require the exact Codex session. Successful host
   receipts repeat the PID, process group, birth identity and session so the
   project attempt can cross-bind them. Success requires a zero exit, exact
   process and session identity, output hash, and the domain's expected
   remote-operation outcome. Confirmed remote output retains its byte hash
   even if the CLI later fails; `remoteOutputHash` records the exact generated
   image bytes while the raw image remains in the private attempt directory.
   Unresolved facts keep the attempt unknown.

3. **Make the Mac host supervisor the process owner.** The existing creator
   workbench bridge accepts typed attempt identities and frozen profiles; it
   does not accept executable paths, shell text, arbitrary commands, or caller
   selected writable roots. The supervisor persists its reservation and
   spawn intent before starting work outside the HTTP request lifetime. The
   bridge starts one source-owned, attempt-scoped worker process, which owns
   the Codex CLI child and terminal publication. The worker records its own
   PID, process group and birth identity before it can start the CLI, so a
   bridge restart can reconnect to the same live worker. If that worker dies
   before terminal settlement, the attempt remains unknown and keeps its host
   slot. The supervisor owns a private attempt directory, session ID, terminal
   receipt, and descendant reconciliation. The host ledger enforces one
   initial attempt for each immutable project/job identity. Admission of the
   same attempt ID is idempotent; another attempt for the same immutable job
   is refused. The first serial checkpoint admits one host process at a time.
   Before persisting spawn intent, the project marks the
   exact prepared image proposal exported under the same image authority.
   Reconciliation from a still-reserved attempt may repeat that local
   transition only when the same job remains current and is already exported;
   once spawn intent is recorded, host admission resumes with that same
   attempt ID. The host SQLite transaction is also the cross-process spawn
   fence: it holds the write reservation across the final cancellation read,
   Codex `Popen`, and exact PID/group/birth-identity persistence. A bridge
   cancellation therefore sees either a worker that has not claimed the
   attempt, which may be settled as not-started, or the exact running process,
   which it can cancel. A process-local lock alone is insufficient because
   the bridge and attempt worker are separate processes. Lifecycle snapshot
   merges preserve recorded process/session facts and reject conflicting
   identities, so stale snapshots cannot erase ownership evidence.

4. **Keep raw evidence private and typed.** The supervisor stores the exact
   attempt's event stream beneath installation-local application state with
   owner-only directory/file permissions. It parses only versioned event
   shapes and typed tool arguments from that attempt's session. The worker
   cannot write image outputs or completion markers into the delivery tree;
   the host copies exact ImageGen event bytes there after validation. It never scans
   unrelated Codex sessions or treats string/regex matches, exit status, or a
   model claim as proof. ImageGen completion requires the supported native
   completion event, exact assigned tool/session identity, validated arguments,
   and a hash match to the declared output bytes. Missing or unsupported
   telemetry fails preflight or leaves the attempt unknown. Project records
   retain only typed, hash-bound proof required for validation; raw transcripts
   do not become creative package inventory. Settled receipts and nested image
   events are immutable values. Image paths use one canonical POSIX spelling
   beneath `delivery/outputs/`, include a filename, and bind each reference by
   SHA-256 identity. The receipt output hash is the SHA-256 of the canonical,
   path-sorted output manifest containing each relative path, byte hash and
   size. Each image event must match one manifest entry. Its argument hash binds
   the normalized prompt hash, reference hashes, transparency setting and
   prior-image allowance.

5. **Reconcile the original attempt after restart or stop.** A missing host
   acknowledgement, PID, session, event stream, or output does not authorize a
   retry. Unknown provider outcomes retain their budget and host reservation
   until exact terminal settlement. PID reuse and orphan descendants are
   fenced before signaling; lack of permission is not proof that a process is
   gone. After the CLI leader exits, the host waits briefly for its process
   group to become empty before trusting outputs. A remaining group becomes
   `outcome_unknown` and keeps the serial host slot; the host does not signal a
   group whose original leader identity can no longer be verified. Pause stops
   new scheduling. Cancel and takeover revoke automatic
   adoption while preserving late bytes and requiring truthful process and
   remote-operation settlement. Cancellation sends the full frozen attempt
   identity to the Mac supervisor and serializes with admission. If cancellation
   wins before the host creates its durable attempt row, the supervisor records
   a terminal `not_started` result in that row; a later duplicate admission
   returns that result without launching. If an unrecorded snapshot already
   contains process facts, it is retained as `outcome_unknown` and holds the
   host slot. Killing the CLI cannot establish that a remote ImageGen operation
   did not occur. A broken assignment write after spawn is retained as unknown
   even if the CLI exits cleanly, since a partial prompt cannot prove that no
   remote operation ran. Broken-pipe handling still applies the frozen runtime,
   cancellation and output watchdog, including termination escalation; it never
   waits indefinitely for the child. If a text-stage session contains observed
   ImageGen calls or events, the text attempt remains unknown and retains the
   host slot. Its domain contract cannot truthfully settle a remote operation
   that text work forbids.

6. **Validate before existing adoption.** The current stage owners continue to
   validate complete packages and exact output inventories. CLI evidence is
   admitted as a separate typed receipt before the existing currentness and
   compare-and-swap adoption transaction. Receipts, source currentness,
   canonical adoption, material inventory and final human handoff retain their
   current owners. Portable snapshot inventory derives the creative package
   shape from its v4 checkpoint and requires the exact project attempt receipt
   for a completed CLI delivery. Recovery can inspect settled evidence but
   cannot reacquire authority to resume a host attempt.

7. **Keep source-only native capabilities explicit.** Native execution pins
   currently depend on checkout-owned skills, validators and host composition.
   The executor may run only when those resources are resolved from a validated
   source installation and match the frozen pins. Installed-wheel startup is
   not evidence that CLI worker capabilities or those resources are available.
   No arbitrary current-directory fallback is permitted.

8. **Keep author, model and trusted-executor fields separate.** The author and
   canonical project state own the frozen request, accepted revisions,
   reference identities and stage authority. The model owns only the candidate,
   report, declared output roles, and its literal ImageGen arguments. It cannot
   declare a process, CLI session, native task, successful ImageGen event,
   actual output hash, or executor provenance. The Mac host derives process and
   session identity from its persisted launch and the exact session file; it
   parses the literal tool arguments and supported terminal ImageGen event and
   hashes the resulting bytes. The project binds that private receipt before
   invoking existing package, currentness and adoption owners. Existing
   specialist-chat schemas remain unchanged; CLI delivery gets its own typed
   identity fields and cannot satisfy a native-task UUID slot with a session,
   process, event, or fabricated chat ID.
   V4 preserves the frozen local geometry recipe and target dimensions, so
   existing geometry lineage validation applies to v4 under the same policy
   hash and output-byte checks.

## Alternatives rejected

- Replacing `codex queue` with `codex exec` inside the current one-shot
  dispatcher: this would still leave process ownership, durable attempts,
  recovery, and typed native evidence undefined.
- Reusing specialist chat UUID fields for session or process identity: that
  would make package pins and ordinary-open checks assert a false identity.
- Launching `codex exec` in the Linux web-request process: that boundary does
  not own Mac authentication or native execution and cannot reconcile the
  process independently of a request/container lifetime.
- Accepting exit zero, stdout text, or model-reported tool use as ImageGen
  proof: the tested CLI omitted the required ImageGen extension event from
  stdout.
- Searching the Codex session tree for a likely matching event: this could
  admit evidence from an unrelated run and would not bind it to the attempt.
- Switching to app-server now: the observed blocker concerns absent typed
  ImageGen evidence in the tested CLI surface; qualify an explicit capability
  adapter first and revisit only if the supported CLI cannot expose it.

## Consequences and guardrails

The serial executor is a new launch and package contract, not a migration of
retained runs. Fresh autopilot runs require v4; retained v1–v3 runs may be
inspected, reconciled as evidence, or handed off, but cannot resume automatic
specialist dispatch. Existing manual specialist and creative-handoff workflows
remain available under their own contracts. Its first checkpoint preserves
existing stage order and admits one process at a time. Pool scheduling,
early-reference dispatch, provisional inventory discovery, progress UI and
parallel capacity policy are later
roadmap checkpoints. Early reference work must disclose its bounded inventory
consequence and use a separately frozen allowance before it is enabled.

Focused regressions must cover duplicate attempts, crash boundaries, missing
and foreign evidence, omitted ImageGen stdout events, PID reuse/descendants,
late delivery after stop, exact output hashes and adoption races. Full release
qualification, disposable native actual-path proof and activation remain
separate gates.

## Field ownership reviewed before implementation

The creative request and image request are frozen by trusted authoring
operations; their request hashes and canonical subject/reference bindings are
authoritative. In current creative and image packages, the worker writes the
candidate or image completion declaration. Existing `executorProvenance`,
`taskId`, `nativeTaskId`, and ImageGen claims are validated according to their
current specialist-chat schemas. The CLI path must use a separate manifest
identity shape: no `taskId` or `nativeTaskId`; the trusted attempt receipt owns
CLI/process/session/event provenance and observed bytes. The model's literal
ImageGen prompt, reference arguments, and transparency setting are recorded as
observed arguments, then checked against the frozen package references. This
ownership mapping is the contract for the next CLI-specific package and binder
changes; it does not rewrite retained specialist receipts or relax their
validators.
