# ADR 0174: Bounded fair Codex Exec scheduling

Status: accepted for the approved bounded implementation, 2026-10-14.
Native concurrency and final release qualification remain required.

## Problem and evidence

The accepted `8ee80e9b` serial proof adopted eight real text deliveries and two
native images, then paused. The host ledger still has `CHECK (slot_id = 1)`;
its busy exception becomes a generic unknown acknowledgement at the bridge.
The controller advances the first unfinished operation. These contracts cannot
represent safe independent work, finite waiting capacity or actual validation
activity. Increasing a process count alone would preserve those defects.

## Decision

- Freeze pool limits in the current executor profile: at most four Codex jobs,
  two text and two image jobs, with at most four enabled waiting jobs. Suspended
  identities retain inactive project work; resuming must reacquire bounded queue
  authorization before dispatch. Trusted
  qualification configurations may reduce these limits; their exact profile
  is frozen before dispatch. A job remains one immutable package and one
  attempt. Model/effort, sandbox, one-call image authority and native evidence
  rules remain unchanged.
- Persist an ordered private queue and capacity reservations atomically in the
  installation ledger. Select the oldest eligible job, skipping a full domain
  or suspended job. Helper creation follows the committed grant outside that
  transaction. Preserve ADR 0165's short native spawn/cancel/identity fence.
  Grant at most one new helper per bridge operation, preserving its bounded
  acknowledgement window. Existing status/admission/terminal events drive
  continuation; there is no reservation timeout or replacement attempt.
- Add honest `queued` and `validating` attempt states. A queued job has no CLI
  process/session or terminal facts. Validation starts after supported native
  completion evidence is available and before trusted validation succeeds.
  A full waiting queue returns typed known capacity deferral; it neither
  acknowledges host admission nor implies an uncertain provider dispatch.
- Unknown work retains its exact domain and global reservation until supported
  terminal settlement. Other eligible work may use remaining capacity. Cancel
  uses exact immutable identity and owned processes; killing a local child does
  not establish absence of an ImageGen operation.
  When a stopped image job is proven not started, cancel its unstarted owning
  proposal in the same project evidence transaction as terminal checkpoint,
  attempt and budget settlement. This cannot strand an exported proposal after
  host capacity is released, and cannot revoke an existing delivered asset.
- Pause suspends unstarted queue authorization and retains its order/budget.
  An unregistered worker can be fenced before registration. A registered worker
  may park the original attempt only through its own proven pre-spawn branch;
  missing PID/acknowledgement never supplies that proof. Running work may finish
  with retained delivery. Resume reenables the original job after frozen
  execution/currentness checks; takeover/cancel revoke automatic adoption.
- Extend the current project state constraint for the new states. Convert only
  the private capacity-table shape when necessary, transactionally preserving
  every exact held attempt/domain and unchanged attempt/receipt bytes. Do not
  reset an unknown ledger or bypass it with a new namespace. Retained profile
  metadata remains readable; retired executor contracts are not executable.
- Project folders use exact schema admission and do not run Alembic on open.
  Freeze the immediately preceding serial layout from `1368dbd7` under hash
  `a6e41b2a3ab1745521886f8db4b2a16e57bc2562835f2af4689be8d424a1a0e6`.
  Extend the established explicit preserving operator transition to that exact
  layout: idle paused/stopped work only, no unsettled attempts, unchanged row
  projections, asset/package bytes, foreign keys and identity. Ordinary open
  remains strict. Snapshot destination upgrade records the actual source-layout
  hash and retains existing restored-run dispatch quarantine. Alembic 0029 is
  engine-schema support; it is not project-folder upgrade evidence. No live
  operator activation or source/attempt rebinding is authorized by this change.
- Keep project adoption serial under existing claim/currentness/CAS authority.
  Current Cast → Art → Script → Storyboard and Bridge bindings stay intact.
  Two text slots require genuinely independent frozen jobs, initially from
  different projects.

## Rejected alternatives and consequences

Reject unbounded executors, a generic exception for capacity, timeout release,
automatic retries, and independent private pools that evade installation caps.
Reject rollback from registered spawn intent based only on absent process facts.
Queue state and pause authorization become explicit owning contracts; callers
must preserve them through restart and manual control.

## Qualification

Cover FIFO/domain fairness, finite deferral, cross-process claims/caps, queued
pause/resume/cancel, pre-spawn parking and crash ambiguity, validation/cancel,
unknown holds and recovery. Qualify one text plus one image, then two images,
then two independent text jobs before publication. Stable review and one
combined full gate remain required; matched performance needs the manager's
quiet allocation. No hosted CI, live activation or old-run replay is allocated.
