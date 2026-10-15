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
