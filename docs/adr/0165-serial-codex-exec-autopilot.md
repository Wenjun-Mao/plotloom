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
   even if the CLI later fails; unresolved facts keep the attempt unknown.

3. **Make the Mac host supervisor the process owner.** The existing creator
   workbench bridge accepts typed attempt identities and frozen profiles; it
   does not accept executable paths, shell text, arbitrary commands, or caller
   selected writable roots. The supervisor persists its reservation and
   spawn intent before starting one process outside the HTTP request lifetime.
   It owns a private attempt directory, process-group identity, PID birth
   evidence, session ID, terminal receipt, and descendant reconciliation.
   Admission of the same attempt ID is idempotent; another attempt for the same
   immutable job is refused. The first serial checkpoint admits one host
   process at a time.

4. **Keep raw evidence private and typed.** The supervisor stores the exact
   attempt's event stream beneath installation-local application state with
   owner-only directory/file permissions. It parses only versioned event
   shapes and typed tool arguments from that attempt's session. It never scans
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
   gone. Pause stops new scheduling. Cancel and takeover revoke automatic
   adoption while preserving late bytes and requiring truthful process and
   remote-operation settlement. Killing the CLI cannot establish that a
   remote ImageGen operation did not occur.

6. **Validate before existing adoption.** The current stage owners continue to
   validate complete packages and exact output inventories. CLI evidence is
   admitted as a separate typed receipt before the existing currentness and
   compare-and-swap adoption transaction. Receipts, source currentness,
   canonical adoption, material inventory and final human handoff retain their
   current owners. Portable recovery can inspect settled evidence but cannot
   reacquire authority to resume a host attempt.

7. **Keep source-only native capabilities explicit.** Native execution pins
   currently depend on checkout-owned skills and validators. The executor may
   run only when those resources are resolved from a validated source
   installation and match the frozen pins. Installed-wheel startup is not
   evidence that CLI worker capabilities or those resources are available.
   No arbitrary current-directory fallback is permitted.

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
retained runs. Its first checkpoint preserves existing stage order and admits
one process at a time. Pool scheduling, early-reference dispatch, provisional
inventory discovery, progress UI and parallel capacity policy are later
roadmap checkpoints. Early reference work must disclose its bounded inventory
consequence and use a separately frozen allowance before it is enabled.

Focused regressions must cover duplicate attempts, crash boundaries, missing
and foreign evidence, omitted ImageGen stdout events, PID reuse/descendants,
late delivery after stop, exact output hashes and adoption races. Full release
qualification, disposable native actual-path proof and activation remain
separate gates.
