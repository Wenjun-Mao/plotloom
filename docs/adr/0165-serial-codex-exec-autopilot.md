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

The first isolated actual-path text attempt exposed an auth-boundary defect:
the supervisor launched with a new per-attempt `CODEX_HOME` and forced the
`keyring` store, while the existing signed-in CLI context used its ordinary
home/default store. That attempt received repeated 401s and remains
`outcome_unknown`; it was not resent. Separately, the invocation used legacy
`--sandbox workspace-write` despite the profile's narrower label, so the
label did not prove frozen-input-only confinement. A no-provider permission
probe confirmed the CLI permission-profile semantics for sandboxed commands,
but the exact `codex exec` invocation still requires local qualification.

Source review also exposed two evidence-contract gaps. The telemetry adapter
scanned JavaScript for a literal ImageGen call but did not establish that the
call was the executed statement; a completion event could be assigned to a dead
branch's arguments when an actual call was hidden in template interpolation.
Separately, creative packages named checkout-owned skills and validators while
the CLI profile denied the checkout and started in `delivery`, so its emitted
repository-root commands could not reach those resources. The bounded repair
is to accept only one direct awaited ImageGen statement and grant
stage-specific read access to exact pinned source resources while keeping all
generated files in `delivery`.

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

   The pinned CLI also emits typed `item.completed` diagnostics before
   `turn.started` when it ignores an invocation setting, followed by
   `item.started` and `item.completed` `file_change` events for built-in
   patches. The JSONL reader accepts only the observed bounded shapes, keeps
   diagnostic message hashes and byte sizes rather than raw messages, and
   requires each file-change completion to match its start. A diagnostic
   makes a zero-exit `turn.completed` attempt a failure; malformed or
   out-of-delivery file-change evidence leaves the attempt unknown. The host
   verifies every reported changed path is canonical and confined to the
   assigned delivery before adopting outputs.

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

9. **Bind authentication and model-command permissions to the invocation.**
   Fresh profiles use the CLI's `file` credential store in the existing
   installation `CODEX_HOME`; the host never creates a per-attempt auth home
   or copies credentials. The selected store is non-secret and part of the
   profile hash. A separate host readiness check runs `codex login status`
   with that same home and store before launch policy freeze, project attempt
   reservation, and CLI `exec` spawn. Readiness means only that local
   credentials are present; it does not prove service entitlement or prevent
   a later 401, which remains an unresolved remote outcome.

   Model-generated commands use an invocation-local permission profile, not
   legacy `--sandbox`: deny the filesystem root, allow minimal runtime reads,
   the exact frozen package and delivery, and an attempt-scoped temporary area;
   deny the auth home and system temp; disable command networking. Text stages
   receive a stage-specific read allowlist for their pinned upstream skill and
   validator entrypoints. Python validators additionally receive the
   source-owned `src/plotloom`, `pyproject.toml`, `uv.lock`, and existing
   `.venv` as read-only resources. The source root itself and unrelated stages
   remain denied. The host verifies the package's stage/path/hash/revision pin,
   requires the vendored stage tree to be clean, and hashes the complete local
   Python source tree plus resolved validator toolchain identities into the
   executor profile. Each stage receives only its pinned `uv`/Python or Node
   executable and runtime directory. The CLI keeps its working directory in
   `delivery`; source commands use `PLOTLOOM_SOURCE_ROOT` and Python validators
   run the pinned `PLOTLOOM_UV` with `--locked --no-sync` so validation cannot
   update the source environment. Fresh profiles use tool contract v4. They
   disable apps, browser, web-search and multi-agent features. Text attempts
   also disable both `image_generation` and `view_image`; image attempts enable
   both with the exact pinned CLI feature flags, without a conflicting disable
   for either feature. The documented `tools.view_image=false` setting was
   ignored by the exact pinned binary and produced diagnostic items. Its local
   `codex-cli 0.162.0-alpha.17.2 features list` reports the selected features
   under command-line flags, which qualifies feature selection but does not by
   itself establish actual filesystem/tool boundary enforcement. Deprecated
   `features.web_search_cached` and `features.web_search_request` toggles also
   produced diagnostics, so the invocation uses top-level
   `web_search="disabled"`. The documented setting is listed in the
   [Codex CLI config reference](https://learn.chatgpt.com/docs/config-file/config-reference);
   the [JSONL event reference](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
   describes `codex exec --json` event output. User configuration is ignored,
   and image tools are enabled only for an image attempt. The Codex client's own authentication
   and service traffic remains outside the local-command sandbox. The exact
   `exec` command flags and filesystem profile are frozen by the source-bound
   profile and must pass allow/deny probes before provider dispatch. Shell
   sandbox tests do not establish confinement for the built-in patch tool or
   ImageGen reference pre-reads.
   Those exact tools require allowed controls and denied absolute-path plus
   symlink/traversal sentinels before any provider dispatch; post-delivery
   package rejection is not pre-read protection.

   Frozen visual-style authority also selects the deterministic stage
   validator. A `saved_brief` authority in the exact frozen Cast, Art, or
   Storyboard input contract routes to its neutral Brief adapter and the
   source-owned upstream structural gate; a preset Cast or Art contract keeps
   the existing preset adapter. The host verifies a saved-Brief contract
   against its source-owned policy before granting the adapter. It permits
   only that adapter, its exact policy file, and the pinned stage resources.
   In particular, the F5A adapter reads `src/plotloom/storyboard_brief_style.py`
   to verify the contract's validator hash, so that exact file belongs in the
   Storyboard read allowlist. Codex remains in `delivery`: Plotloom validator
   commands use the absolute `$PLOTLOOM_SOURCE_ROOT` path, while candidate,
   report, and package-input paths resolve from `delivery`. This changes only
   the shell path base from legacy repository-root instructions; it does not
   change saved-Brief authority or any stage validation rule.

   Upstream skill commands bind `{baseDir}` to the directory containing the
   exact pinned `upstreamSkillPath` in `request.json`.
   `$PLOTLOOM_SOURCE_ROOT` remains the checkout root for Plotloom-owned
   validators. Keeping these roots distinct preserves each Shuohao skill's
   relative command paths without expanding the stage-specific read allowlist.

   Session identity comes only from this process's first `thread.started`
   event. The host then opens the uniquely named file for that UUID, verifies
   its `session_meta` identity, and hashes the exact bounded file; it does not
   inspect the contents of other sessions. The telemetry adapter dispatches
   on the typed CLI tool name before interpreting tool input, and ImageGen
   arguments still require one direct top-level awaited built-in call with
   literal arguments and a supported extension event. This is intentionally
   narrower than parsing arbitrary JavaScript because the tested CLI event has
   no call-ID link to the source expression; templates, branches, helpers,
   multiple statements and multiple ImageGen calls fail closed.

10. **Prove frozen reference viewing separately from ImageGen attachment.** The
    source mismatch was concrete: the image package and pinned skill require
    references to be viewed before generation, the current image tool profile
    disabled `view_image`, and the host derived `viewedReferenceHashes` from
    paths attached to ImageGen. The installed child declaration uses
    `referenced_image_paths`, while the source prompt and telemetry parser used
    `images`. A diagnostic path-loader probe established an allowed package
    `ImageView` event and three explicit outside-path denials, but its paired
    tool output was truncated text with no `input_image` content block. It
    therefore did not qualify model-visible pixels or production behavior.

    New Codex Exec image packages use package version 8 and manifest schema 5.
    Every entry in the frozen package reference inventory must be viewed once,
    in package order, before the ImageGen call. The current input roles are
    `character_identity:<characterId>`, `parent_output`, and `source_keyframe`;
    the latter occurs only for a keyframe adaptation. `art_reference` is an
    output role for an exploratory art proposal, not an input-reference role.
    Unknown future package-reference roles remain subject to the same required
    view; they are not silently omitted. A package with no references needs no
    view call and has no reference-use evidence.

    Each view uses exactly one awaited expression per `exec` call:
    `image((await tools.view_image({path: "<literal frozen package path>"})).image_url);`.
    The host accepts a view only when that exact source is paired in the same
    exact session with a native `ImageView` event for the decoded file URL and
    the matching successful `exec` result contains one valid inline image
    content block whose raster pixels fully decode under the byte and pixel
    bounds, even when Pillow is configured to reject truncated images. A valid
    container header or chunk checksum alone is insufficient. Calls, event,
    and result must appear in that order. The path must identify the exact
    frozen package file and SHA-256. Before
    ImageGen, the host requires one successful view for every frozen reference,
    in package order, with no duplicate, foreign, late, missing, failed,
    malformed, or truncated evidence. Text claims, a native loader event alone,
    and attached paths alone never create `viewedReferenceHashes`.

    The trusted receipt records per-reference role, content hash, source call,
    native event, and ordered transcript positions. It keeps these fields
    separate from `referenceHashes`, which describe files supplied to
    ImageGen's `referenced_image_paths` argument. Only validated receipt view
    evidence can populate manifest `viewedReferenceHashes`; any note states
    that the evidence proves image-content delivery, not model cognition,
    identity recognition, adherence, or creator acceptance. The pinned
    ImageGen declaration is followed exactly; unknown argument shapes fail
    closed. The earlier Codex Exec package-v7/manifest-v4 contract is retired
    for new validation and is not silently replayed under this contract.

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
- Giving each attempt a new empty `CODEX_HOME` and forcing keyring: this
  severed the already authenticated CLI context and was the observed cause of
  the 401 canary. Copying or recreating credentials per attempt would add a
  second credential owner and widen exposure.
- Keeping `--sandbox workspace-write` under a narrower profile label: the
  command-line legacy sandbox selects its own policy and cannot establish the
  advertised read boundary. The profile must be applied in the actual `exec`
  invocation.
- Scanning arbitrary JavaScript for ImageGen call-shaped text: source syntax
  alone does not prove a call executed, and the tested extension event has no
  exact source call ID. Rejecting anything outside one direct awaited
  statement prevents dead or ambiguous code from supplying event arguments.

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

## Frozen source revision and validator runtime repair

The first isolated actual-path text canary exposed two separate contract
failures. Its trusted completion publisher labeled the Shuohao
`executionPin.upstreamRevision` as the executor's `codeRevision`, while
adoption compares that field with the Plotloom checkout revision frozen by the
launch. The validator also used shell heredocs whose zsh temporary files follow
`TMPPREFIX`, even though the supervisor had isolated only `TMPDIR`; Node's
default OpenSSL initialization additionally needed its exact system config
file readable in the sandbox. The observed failure therefore belongs in the
frozen source and runtime contracts, not in adoption tolerances or delivery
repair.

Fresh creative Codex packages use version 3 and carry `plotloomCodeRevision`
beside the unchanged upstream skill pin. The immutable attempt and its receipt
repeat that Plotloom revision; supervisor admission, terminal manifest
publication, persistence validation, and owner adoption require it to match the
launch. Terminal code never derives a replacement revision from the current
checkout or from the upstream pin. This preserves the distinct owners and
makes missing, forged, or mismatched source identity fail closed.
The attempt lifecycle model imports shared identifiers from a constants-only
leaf so either public contract module can be imported first. Cold-start imports
in both orders remain a regression guard for this dependency boundary.

Fresh Codex profiles use contract v5 and permission profile v3. Text attempts
set `TMPPREFIX` beneath their private attempt directory, discard inherited
`OPENSSL_CONF`, then bind it to the qualified system OpenSSL config. Only text
attempts receive read access to that exact config; image attempts do not. The
existing `/tmp` denial remains in force. This profile records the runtime
contract so later probes can identify what was actually authorized. A native
sandbox probe qualifies that exact shell/runtime boundary but does not prove
the environment of the model's internal tool implementation; that remains a
separate actual-path qualification gap.

Retained v4 evidence remains inspectable through a read-only inventory branch:
v4 owns package version 2 and its historical `codeRevision` label was the
upstream skill revision. That projection is limited to storage validation and
snapshot inventory; it does not populate new attempts, rewrite packages, or
satisfy current adoption. Fresh execution and adoption use only v5's frozen
Plotloom revision. Absent optional revision fields stay absent when old attempt
and receipt snapshots are parsed and reserialized, so ordinary-open canonical
checks do not rewrite historical state.
