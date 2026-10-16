# ADR 0178: Capsule and plan handoff authority

## Context

The isolated CLI canary's copied filesystem helper lost regex bytes. Its identity
guard correctly refused before intent or native launch. Its shared paid command
also selected an entry inside a runtime required to contain only `phase.json`.
Both problems belong to the operator/source contract. The historical failure and
v1 evidence retain their original meaning.

The first no-work host capability passed, but a separately observed import of
the same sealed B01 returned a different evaluation UUID with unchanged origin,
export and all source identities. The observer's constant-ID assertion failed;
no multi-action handoff ran. Node REPL documents persistent bindings, not module
cache lifetime. The capsule added an instance-lifetime assumption that the
approved source assurance did not require. This is a source-versus-instance
model error in the capsule/regression, not demonstrated source drift or a host
cache defect. Preserve B01 and its failed criterion as immutable evidence.

## Decision

The owner approved capsule-and-plan verification while trusting a tiny outer
invocation, then implementation and provider-free capability/synthetic checks.
The outer invokes one named, self-inspecting capsule once/await and supplies
genuine tools, canonical plan text, actual anchor text and a separately accepted
anchor SHA-256. That expected pin comes from independent allocation/release
authority. Verify actual anchor bytes before using its fields; the anchor then
pins capsule, plan, source controls and phase descriptor without a hash cycle.

The capsule contains all dispatch-affecting orchestration and fixed bootstrap
text, uses its internal function identity and the trusted function-source
primitive, and reaches verification before intent/native dispatch. The narrow
import exception permits one fixed absolute file URI from a fresh versioned,
hash-pinned bundle. No caller URI, query, cache-busting, eval, text-file compiler,
generic loader, fallback or native tool bridge exists. No concurrent bundle
writer is allowed after sealing; source pre/post checks are not an atomic import.

Source authority is stateless per action: each action verifies the accepted
anchor/plan/capsule, controls, fixed URI/origin, exact export, full private source
closure and identities before import, after import and after action, plus the
descriptor, argv and current committed records. Helper state is local to the
action; cross-action authority resides in bound files. Validate and retain each
nonempty evaluation ID as diagnostic evidence. Equal IDs do not attest source
provenance, and different IDs alone do not invalidate identical approved source.
The no-work capability branch performs exactly two sequential capability actions
inside one awaited capsule, recording both results without intent or native work.

The repository capsule is an offline source template. The owned bundle builder
replaces exactly four fixed root tokens before hashing/sealing, never at runtime.
It copies the remaining current source closure exactly and refuses stale or
nonempty bundles. Repository tests create their own fresh fixture from those
current bytes; they do not depend on retained machine-private proof packets.

Immutable B owns all executable sources and a fixed both-kind entry registry.
Mutable F/L runtimes start with only their descriptor. JS/Python/shared receiver
bind the same checked interpreter, `-B`, registered B entry, runtime and descriptor
hash. A missing real paid entry refuses; its positive qualification stays open.

Preserve one awaited fail-stop critical section, distinct original/observation
handles, original monotonic 60-second receiver deadline, exclusive intent,
payload readback then durable empty commit, singleton-marker race checks,
possibly-committed UNKNOWN/no-retry/hold-only and genuine terminal reconciliation.

## Staged owner operations and one-attempt namespace

The owner approved the first core slice on 2026-10-15. The orchestration helper
previously combined reservation and dispatch, its non-admission mode could
suspend work, and supervisor status could start ambient queued work. Those are
valid ordinary recovery behaviors but cannot express an independently frozen,
single-use admission. Fix these boundaries in their existing owners:

- Share frozen package/profile/validation checks and expose reserve-only, strict
  consume-reserved-once, and observe-existing operations. Strict consumption
  checks the complete reserved snapshot and run/checkpoint revisions in the
  project transaction. Ordinary idempotent spawn-intent recovery stays explicit.
  A lost acknowledgment spends admission; observation never resends or resumes.
- Opt in to an immutable one-attempt supervisor namespace pinned by an external
  SHA-256, a private binding file and the ledger. Bind physical application,
  outputs, private, source, precreated empty ledger and executable identities, profile, limits and the
  exact attempt. Verify before ledger mutation, refresh, grants and worker starts;
  carry the pin into reconstructed workers. Missing/drifted binding or foreign
  attempts, queue entries, slots or validators refuse. Unbound ordinary pools
  retain their existing behavior. Fresh roots alone are insufficient isolation.
  The ledger inode is frozen before binding, so deletion/replacement cannot reset
  admission across restart. Only a current empty unbound ledger may be bound.
  Exact cancellation and suspend/resume controls also enforce scope before a
  write. Existing pre-admission cancellation tombstones remain valid for that
  identity; they do not authorize a start.
  Classify these using exactly the existing cancellation transition, evidence
  hash and budget state, empty delivery/worker/receipt fields, no queue/validator,
  and no capacity for not-started versus retained exact capacity for UNKNOWN.
- Stop this bounded path at typed receipt and validated delivery. Canonical
  adoption and later stages require a separate release. Product budgets and
  credential confinement remain owned by the existing contracts.

Paid allocation, launcher, receiver and capsule integration must bind
actual committed source/closure coherently with paused
run and checkpoint revisions, policy, package, profile and runtime through an
acyclic hash graph. The old `2a359171` canary literals are historical evidence,
not a reusable paid source model; do not update them for each launch or rewrite
retained proofs. Provider-free unit evidence grants no paid or native authority.

The core namespace constrains host ledger identities and physical roots. It does
not enumerate the application catalog or attest an exact project-home inode.
A future paid preparer must prove fresh disposable allocation-only project state;
an application/outputs root inode alone is not proof that no foreign projects exist.

## Paid Outline composition (source implementation release)

Root accepted the core checkpoint and released only source implementation and
provider-free correctness checks for one future paid Outline attempt. No actual
allocation, launch, paid qualification or creative acceptance follows.

The current transport contract binds an allocation hash in descriptor, plan,
anchor, intent, attendance and witness. Proof and paid kinds have fixed distinct
authorities and registered launcher/receiver pairs. Paid permission comes from
the independently released allocation and anchor; transport witness provider and
production authority remain false. The original monotonic 60-second attachment
deadline never becomes a generation deadline.

The paid preparer starts from empty owner-private disposable roots, creates one
project, prepares only source and Outline through existing owners, reserves the
actual attempt, then pauses. Its immutable allocation binds project-home and
manifest identity, exact catalog membership, paused run/checkpoint/claim, policy,
Brief and material closure, full reserved attempt, frozen package/profile and
checked validator runtime separately from QA. Receiver claim and resume are
known explicit revision edges under one existing owner transaction; never read
a newer foreign revision and reinterpret it as permission.

Reusable source identity records actual committed Git revision/tree plus the
independent owned workflow and profile closure. A real paid preparer requires
committed reviewed owner bytes; synthetic disposable source fixtures may make
their own local fixture commit, never modify the task checkout's Git state.
Bundle derivation is fixed offline copying/binding. Allocation does not contain
anchor/plan/phase hashes: allocation -> phase/plan -> independently pinned anchor
is an acyclic data dependency. Historical canary literals and sealed evidence
remain immutable and are not a source-identity service.

The in-process composition uses the existing QueueBridge/Mac supervisor, with
the persisted namespace pin passed by its constructor. It exposes no new HTTP
bridge or executor. Strict owner admission is spent before the sole external
call; polling is observe-only. Typed receipt and trusted validated delivery end
in a paused HOLD. UNKNOWN, lost acknowledgment or stopped observation retain
the original identity without resend, adoption, image permission or continuation.
New transport modules stay in the handoff workflow, not in product controllers.

### Shared pause fence after an uncertain admission

The provider-free `paid-negative-01` lost-ack regression demonstrated a real
pause-contract defect: the project retained its spent attempt as UNKNOWN and
acknowledged pause, while the exact host row remained `spawn_intent`, queue
enabled, no worker registered and one text slot held. Its immutable evidence is
in the paid-source packet; no status poll was used to diagnose it.

`suspend_pending_codex_exec` treated project state as proof of host dispatch state
and skipped UNKNOWN. Repair the existing shared pause/fence owner: pass the exact
retained UNKNOWN identity to the existing typed suspend operation, just as for
queued/intent identities. The host alone decides whether its current exact row
is provably unstarted and may be parked. Keep the project's UNKNOWN fact; never
project it into queued, poll/resume/admit, invent a replacement or release an
uncertain process's capacity. Running, validating and UNKNOWN host facts and
late receipts remain intact. Missing host identity, mismatched echo, enabled
unstarted dispatch or suspension failure must fail acknowledgment and roll back
the project pause transaction. Paid orchestration reports that failure truthfully.

This belongs to the shared pause invariant, not a paid-only workaround. Guard it
with actual project-owner transactions, actual supervisor parking/preservation
cases, the lost-ack composition regression and affected ordinary/late-receipt
owners. Prior core receipts keep their historical source pins and meaning.

Synthetic composition fixtures own independent disposable source commits and
metadata-only checked Python identities. Outline's actual validator and renderer
are the frozen Node stage; the fake external CLI must compare its complete
production sandbox argv, execute those real Node tails and retain real exit and
report streams. A fabricated zero exit or HTML is not validator evidence. This
does not qualify the Mac sandbox or provider. Fixture cleanup binds actual spawn
identities and trusted descendant records; missing identity or unresolved group
ownership is UNKNOWN, never proof of quiet or authority to signal a reused PID.
The direct-command guard establishes its actual identity before releasing target
execution. Its ready/go names publish complete JSON atomically; partial records
are not repaired through parsing retries.

## Finite paired qualification: migration checkpoint (2026-10-15)

### Diagnosis and approved boundary

The accepted `ed9c4941` handoff spends one exact reserved Outline identity. It
does not authorize the existing serial-first campaign's four projects or its
multiple dependent jobs. This is a missing finite authority contract, not a
failed provider, checked Python runtime or Capsule attachment. The previous
Outline allocation remains spent; its evidence and one-attempt namespace must
not be widened, converted or relaunched.

The selected future method is one serial arm followed by one parallel arm,
with a primary and an Outline-only sidecar in each. Ceilings are nine text
attempts and 32 image outputs per arm (18/64 total), with global/text/image/queue
caps `1/1/1/4` then `4/2/2/4`, and 90 minutes plus ten minutes of settlement
per arm. Primary authority covers the eight production text stages, required
adoption/installation, references and all-route frames. Sidecar authority covers
one original Outline and receipt reconciliation, without generated-content
adoption, images or later stages. These are ceilings, not known output counts,
creative acceptance, native qualification or a released generation allocation.

Keep a separate finite qualification namespace and registered entry. Preserve
the current exact-attempt namespace and ordinary unbound installations. Reuse
the existing production project and supervisor owners; add no executor,
scheduler, arbitrary-code loader or alternative recovery path. Source/work/arm
locations and import origins must be explicit physical bindings. An allocation
must not select Python modules, executable code, a fallback cwd or an old run.

### Why a transport-only extension is insufficient

Static inspection of retained `matched-pair-observed-2a359171-20261015-02`
establishes the following migration requirements. That historical failed run
remains evidence, never executable authority for a new run.

| Existing boundary | Evidence and required change |
| --- | --- |
| Campaign source ownership | Counting shared files and one arm, the retained set contains 2,620 Python lines: 2,061 runtime/preparation/analysis/helper lines and 559 test/fixture lines. This inventory is outside the tracked fixed handoff closure; its size is not itself a reason to change the method. Retained `run_pair.py:12–15` derives ROOT from `WORK.parents[2]`; `serial/run_arm.py:17–28` uses `WORK.parents[3]` and inserts arm, campaign and service directories into `sys.path`. Moving files into B does not preserve import ownership. |
| Sidecar control, distinct from host admission | Retained `serial/run_arm.py:210–225` excludes background controller ownership and takes its lease. Lines 264–275 inspect, pause on the retained native PID, then issue one step. Current `src/plotloom/autopilot_text_controller.py:44–60` returns after one stage action; lines 183–185 adopt only an already-delivered checkpoint, whereas lines 221–234 record delivery and return. Lines 34–36 and 339–383 route a paused sidecar into inactive receipt reconciliation. Preserve this ordering; a host Outline allowlist alone cannot guard local adoption. |
| Ordinary launch budgets | `src/plotloom/autopilot_contracts.py:45–59` requires at least one image and nine jobs in ordinary policy. Qualification ceilings belong to the finite allocation/admission restriction; this does not establish a need to change ordinary policy or add a product-specific sidecar policy. |
| Atomic admission | `services/creator_workbench/codex_exec_supervisor_admission.py:23,48–81` checks namespace before `BEGIN IMMEDIATE`, then inserts attempt and queue. Finite role/stage/count checks must also run inside that transaction, including disabled queue entries; a pre-call count or observer is insufficient. |
| Deferred execution | `services/creator_workbench/codex_exec_supervisor_pool.py:101–117` grants later; status can drain the queue (`codex_exec_supervisor_admission.py:92–100`). Worker/native start are further boundaries. A deadline/HALT must fence new grants/starts while leaving observation, late receipts, exact pause/cancel and owned settlement usable; it cannot release uncertain capacity or make every ledger connection fail. |

### Required design checkpoint before executable changes

The source/import migration and the sidecar authority question are separate.
No concrete race, restart path or owner action bypassing the existing exclusive
one-step/pause/no-advance driver has been demonstrated in this inspection.
The coarseness of TEXT scope does not prove that new product/project authority
is necessary. Do not promote that earlier inference into an approved contract.
At that checkpoint Root held wider migration for review; no finite-pair schema,
entry, role fence or allocation had been implemented or qualified. The reviewed slice was:

1. Promote the necessary campaign controls into one tracked workflow, preserving
   RPC/capture/error and cleanup outcomes. Separate immutable controls in B
   from mutable campaign/arm work roots; use explicit source/work/arm arguments
   and verified fixed import origins. Keep both arms on identical control bytes.
2. Define one persisted finite qualification allocation/admission restriction,
   independently pinned in the installation/ledger. Bind catalog,
   physical roots/databases, source/controls, profile, QA and checked validator
   separately, project/run/role/claim identities, one-shot arm activation and
   original deadlines. Freeze each actual project identity before its first dispatch;
   freeze each request/package/attempt before its original admission. Missing
   restriction after restart must refuse new work, not become ordinary unbound.
3. Resolve sidecar confinement by preserving the audited exclusive driver and
   persisted role/order, or reusing the existing prepare/reserve/strict-consume/
   observe/HOLD owner path. `src/plotloom/autopilot_exec_staged.py:33–81` provides
   one-shot consumption and observe-only reconciliation; the accepted
   `scripts/autopilot/handoff/paid_outline_run.py:85–148` never calls controller
   advance/adoption. Reuse those owners, not the spent allocation or its exact
   namespace. Prove no second adopting step after immediate or late delivery,
   failed pause, UNKNOWN, interruption or an attempted restart. Introduce new
   project authority only if a named counterexample defeats these existing
   boundaries. No qualification-only bypass or new public command fields follow
   merely from the shared TEXT scope. Preserve the exact saved-Brief projection
   and Outline preparation; neither grants generated-content adoption.
4. Exercise those real boundaries with test-owned fixtures: forbidden sidecar
   mutations, duplicate/foreign jobs, concurrent and disabled admissions,
   restart pin removal, deadline crossing between admission/grant/start,
   UNKNOWN/lost acknowledgment, late receipt settlement and serial failure
   preventing parallel activation. Preserve strict `complete_success`, current
   quiescence, complete all-route inventory/bundle and sidecar receipt checks.

Enforce per-role reservations before consume and host insertion, then fence
delayed grants and actual starts; passive observation cannot own these checks.
Do not duplicate policy in an observer, weaken the ordinary launch schema, or
load controls from retained `.local` evidence to avoid this migration. Reuse
the unchanged eleven-plan and later fourteen-command F5 native evidence where
its inputs remain unchanged; new fixture correctness is not native proof.

### Resolved implementation direction (2026-10-15)

Root resolved the checkpoint: migrate the necessary existing controls into a
tracked fixed workflow with explicit verified source/work/arm bindings and
immutable import origins. Preserve the authored method, RPC/error capture and
strict success semantics. Keep mutable inputs and outputs outside the sealed
code closure. Report mechanical migration separately from semantic changes.

Use a distinct finite qualification binding with durable actual project/run/role
registrations before dispatch; keep the one-attempt binding and ordinary pools
unchanged. Atomically account for every original authorization, including
disabled entries, and sum reserved image outputs rather than image row counts.
Exact duplicate observations do not spend again. Each arm admits at most nine
text attempts and 32 image outputs across its two designated projects.

No new product/project authority or public command fields are selected. Preserve
the exclusive one-step/pause/no-advance sidecar algorithm, its persisted role,
and existing receipt-only inactive reconciliation. Guard immediate/late/already-
delivered outcomes, failed pause, interruption and attempted restart directly.
A concrete counterexample requires a stop with evidence, not speculative policy.

New admission, delayed grants and native spawn must consult durable HALT,
failure/UNKNOWN and original time bounds in their existing owner transactions.
Worker terminal auto-drain is included. Persist activation/deadlines once;
never renew on restart. A new start must fit the actual CLI runtime, each frozen
validator-step ceiling and declared settlement allowance. Insufficient time is
held/incomplete, never proof of remote absence or released uncertain capacity.
Expiry blocks new work only; observation, receipts and owned settlement remain
available. Parallel activation requires serial complete-success and current
quiescence. No generation/native allocation, cleanup, publication or Python
optimization follows this source/check release.

### Implemented source candidate (2026-10-16)

The source candidate now implements the resolved direction; execution remains
held. The fixed registry adds `qualification_pair` with separate finite authority.
Its code-only controls manifest precedes namespace pins, allocation, full source
controls and transport hashes, avoiding a cycle. The Python registered entry owns
the complete typed allocation/namespace schema; JS owns transport verification
and its finite structural checks. A Python schema refusal may occur after a
transport intent but must precede project creation, admission and provider work.
Do not duplicate the full product schema in JS or claim an earlier refusal.

Setup registers actual project/run/role/claim identities before dispatch. Each
current-owner job is frozen before admission. Frozen originals count against the
ceilings even when disabled or not admitted. The existing host transaction checks
role, stage and output budgets; grants and final native spawn check sticky HALT
and the original activation clock. Activation loss, missing persisted binding or
identity drift refuses rather than restarting authority. Time expiry leaves
receipt reconciliation and owned settlement usable; UNKNOWN retains capacity.
No new project authority or public command fields were introduced.

The existing serial-first driver is now tracked with explicit verified locations
and source origins. The primary path retains adoption/install/reference/frame
operations. The exclusive sidecar driver pauses before its next step on a PID,
immediate delivery or an already-delivered receipt; paused steps use the existing
inactive reconciliation owner. Failed pause, interruption and attempted restart
cannot advance it. Historical controls remain read-only data/evidence, never an
executable import. Preservation paths resolve from the frozen historical root,
independently of the mutable work root.

Review found two acceptance defects in the migrated analysis contract: material
completion alone could set pair success, and a changed transcript could supply
self-consistent timing without matching its original receipt. Fix these in the
measurement and final acceptance owners. Before parsing time or usage, reconstruct
the receipt evidence hash from the original private stdout/stderr, current
transcript hash and exit code, plus the text-validation layer when applicable.
Retain bounded private-file identity and second-read consistency checks. Parallel
success additionally requires ordered cross/image/text owned-process gates and a
strictly positive intersection of ImageGen tool-call intervals from distinct
original attempts and sessions. Zero, touching, absent or unbound intervals fail.
Persist the exact overlap proof and remeasure it at the parent arm gate before
pair completion. This proves observed tool-call overlap only, not simultaneous
remote computation, content equivalence or a capacity-only speedup.

Test-owned fixtures exercise actual schema, host, receiver and telemetry owners.
The pair transport fixture substitutes external native IO, attends original
handle 42 and deliberately holds at a labelled callback before projects or
generation. It does not qualify an actual pair. Stable independent review and a
separate generation/native allocation remain required.

Final review also found that setting retained `activation_json` to NULL left the
arm row/table present and could allow host reactivation with fresh clocks after
frozen authorizations. The fixed arm entry still prevented automatic campaign
restart; that did not satisfy the host persistence contract. The host integrity
owner now requires a valid retained activation whenever frozen or host attempts
exist. Empty setup before activation remains valid. A regression first reproduced
successful reconstruction on the invalid NULL state, then guards reconstruction
and in-memory reactivation refusal with byte-identical database preservation.
No expiry/HALT condition is added to the general connection path, so valid
settlement remains available. Pre-fix qualification evidence stays separately
identified; the corrected candidate requires fresh affected checks.

## Limits and consequences

This replaces whole-body verification for the new contract. It attests neither
the outer caller/body nor the host/tools, and cannot independently prevent an
arbitrarily altered capsule bypassing verification. On-disk/export hashes do not
attest a cached module's origin or closure. Actual first-use/cache and host source
representation need bounded evidence. Fresh-path controlled first use and no
concurrent writer remain explicit trusted-host assumptions, not cache attestation
from a UUID or export hash. No generic action sequence or alternate loader follows.

Regressions exercise actual capsule/helper/binding/receiver code with honest
synthetic fakes, authority drift, strict canonical schemas, filesystem races and
UNKNOWN paths. Check receipts are exclusively pre-reserved owner 0600 and retain
identity. Capability and unit success are not real handoff, paid admission,
generation, product acceptance or matched serial/parallel qualification. Each
requires its later explicit release. See the scoped CLI capsule roadmap.
