# G3–G5: Planning, correction and durable execution ownership

Status: **reviewed combined implementation plan; source implementation starts after this planning checkpoint**.
Date: 2026-10-25. Source and installed baseline:
`a10a88592c25dfb4dad25aedffb1deb33136d8a7`.
Source R: `/Users/wjmao/.codex/worktrees/b30f/plotloom`, clean local main.
Installed P: `/Users/wjmao/projects/HU/plotloom`, clean detached baseline.

## Outcome and scope

The owner asked to plan and then implement G3, G4 and G5 together after the
completed [G2 delivery](2026-10-25-g2-work-unit-ownership.md).
Use **one reviewed plan and one implementation authorization** for the combined
outcome, with serial internal checkpoints G3 → G4 → G5, an integrated final
review/qualification and preservation-checked activation. Intermediate checkpoints
are engineering evidence, not new human approval gates or full-suite milestones.

The [modularity audit](../verification/2026-10-25-modularity-audit.md) defines the
three batches. Deliver actual owners for planning/contracts/context/topology,
correction registry/selection/projection/schema families, and durable exchange/
evidence/correction compilation. Keep explicit stage and unit lifecycle owners.
Update real consumers directly and preserve all current supported behavior.

Stop when all three boundaries, consumer/test updates, early runtime proofs,
stable independent review, full-local qualification, installed preservation/
identity/readback, single recovery refresh and temporary-artifact cleanup are
complete. Do not stop at source extraction, a test total or a worker handoff.

The owner's current request, “Can we plan and then implement all 3 together?”,
authorizes planning followed by the combined implementation described here.
The manager presented serial checkpoints, integrated qualification/activation
and the real-adapter loopback proof during planning; independent technical and
execution-limits reviews found no blocking choices. This current request is the
implementation authority. Earlier standing authority remains specifically for
separate Codex tasks and native model/effort choices; it is not being repurposed
as approval of unrelated implementation. Covered per-batch, per-check and quiet
activation steps need no renewed approval. Material scope/behavior/authority
changes retain owner review. Planning itself made no product-code changes.

Excluded: G1/G2 redesign, retired R1–R3 revival, new generation features, changed
schemas/prompt text/policy versions, migrations/resets, API/domain/frontend
decomposition, supervisor/gateway changes, provider/model/settings changes,
new grants, UNKNOWN clearing, live-data deletion, push and GitHub CI.

## Source-grounded boundaries

Current physical sizes, independently checked at the baseline:

| Current owner | Lines | Required separation |
|---|---:|---|
| `generation/planning.py` | 1,110 | Immutable contracts/hash validation; enqueue plan construction; stage planning; selector-scoped context/input verification. |
| `generation/story_graph_topology.py` | 1,096 | Frozen topology contracts/semantics; complete bounded topology search/materialization; untrusted content-fill shape/schema/binding/diagnostics. |
| `generation/correction_directives.py` | 829 | Versioned static registry versus executable/deferred authority selection and lossless prompt projection. G1 already supplies exact closed fact types. |
| `generation/correction_schema.py` | 669 | Graph/join, continuity/entity-state and cue/timing projections, with one deterministic assembly/hash owner. |
| `work_unit_pipeline.py` | 1,817 | Stage/unit orchestration versus complete provider exchange, durable evidence codec/assertions and correction compilation/source verification. |
| `pipeline.py` | 313 | Actual composition/admission versus live secret broker and provider resolution. R1 already removed the historical 764-line legacy bridge. |

An integrated delivery lets G5 consume settled G3/G4 APIs and avoids three release
cycles. Separate independently deployable plans would reduce the size of each
release but repeat review, full qualification and activation work. The combined
approach fits this behavior-preserving dependency chain; internal checkpoints
keep failures attributable without introducing concurrent source writers.

### G3: Planning and topology

- **Planning contracts/hash authority:** frozen run/stage/unit/selectors/budgets,
  versions, model validators and exact existing hash derivation. Lower contracts
  must not import enqueue/stage orchestration or the runner. Existing pure timing/
  capacity contracts remain their real authorities.
- **Enqueue planning:** create the run-level plan from already-canonical inputs,
  provider limits and instructions. Do not invent future selectors.
- **Stage planning:** select units only after required upstream canonical objects
  exist; retain authored sibling order, route-only filtering, frozen timing/
  capacity/join/edge-entry contracts and exact deterministic IDs.
- **Scoped context/input verification:** reconstruct the exact selector-scoped
  dependency payload, check frozen hashes and unit identity, and share that
  projection with stage planning. It must not reconstruct newer planning context
  or depend on compilation/runner state.
- **Topology contracts/semantics:** frozen nodes/edges/joins, structural validation
  and hash agreement independently importable from search and content binding.
- **Topology planning:** keep bounded feasibility/search, tie-breaking, flow
  construction and materialization as one comprehensible algorithm authority.
  An isolated flow helper is an option only if it creates a real cohesive/testable
  dependency. Review a resulting owner above 500 lines explicitly; do not fragment
  the search/materialization contract merely to reach 400.
- **Content fill:** model-facing DTO/schema/manifest projection and trusted binding/
  diagnostics have actual owners independent of search. Preserve native non-finite
  checks, exact frozen IDs and diagnostic issue order. Diagnostics never accept,
  persist or silently repair an invalid graph.

Use real function/type inputs, not a shared mutable planning object. Keep the
current planning/topology/schema versions and exact omission/null rules. File names
and a sensible combination of small helpers remain implementer choices. Existing
files can retain a genuine operation; they must not become compatibility barrels.

### G4: Correction authority and schema projection

- A **static registry owner** owns ordered directive definitions/text, version,
  code uniqueness and code-to-fact requirements. Stable model-name strings remain
  evidence labels; exact current fact types remain the admission authority.
- A **selection/projection owner** keeps issue/fact code/path matching, executable/
  deferred membership and local indexes, blocker policy, projection and hashes.
  Extract projection separately only where cohesion warrants it. Preserve
  rejection-wide continuity blockers and cue-membership deferral.
- **Family schema owners** handle graph/join constraints, continuity/entity state,
  and cue/timing constraints using explicit owned inputs.
- One **schema assembler** owns the fresh base-schema copy, current conflict/merge
  semantics, exact family/branch ordering, applied-code ordering and canonical
  schema hash. Preserve the current fact traversal and conflict precedence;
  regrouping facts by family must not reorder failures or widen authority.
  Small shared schema operations may be a real lower-level owner, not a general
  schema engine or registry of callbacks.

Schema projection remains a constrained-decoding aid. Canonical validation and
source-bound postconditions remain the acceptance boundary. Preserve explicit
null versus missing value, base nonmutation, branch/cardinality constraints and
complete sibling assignments. Graph entity-state errors retain their named
fail-closed subtype/code; no correction gains authority to choose a new identity
or Bible state. Keep G1's lossless fact codec and G2's source assertions.

### G5: Durable execution

| Owner | Explicit responsibility and boundary |
|---|---|
| Stage runner | Stage dependency resolution/planning, child-local reuse, authorized unresolved selectors, unit sequence, ordered seal/install and visible `finally: release_run`. Keep sealing/repository authority here. |
| Unit executor | Entire attempt allocation/recovery → prompt → exchange/reused response → validation/correction → candidate/finish loop. Keep rejection persistence and the decision to allocate another correction together. State is local to this execution. |
| Durable provider exchange | Existing repository, secret leaser, adapter/profile, compiled request and exact attempt/unit identity → response only after evidence commits. Own complete preflight → dispatch marker → request/provider boundary → certainty classification/redaction → response persistence. No retry/allocation policy. |
| Correction compiler | Exact rejected source attempt plus prompt/response/validation evidence, typed facts, frozen plans/context and profile → compiled correction request. Own source/contract/fact verification and rendering. A cohesive source-authority verifier can be separate if needed. |
| Evidence codec/assertions | Exact current prompt/validation construction, persisted response decoding, audit presence/hash checks and final-content-only recovery. Repository methods retain write/transaction authority. |
| Runtime leaves/composition | Live secret broker/leaser and snapshot provider resolver have actual runtime owners. `PipelineEngine` retains composition, lineage admission and fail-closed exact-scope selection. Update runtime/executor/dispatch/bridge/conformance/acceptance imports directly. |

Never pass the entire old runner, callback bags or shared mutable execution state
into collaborators. Meaningful immutable source-evidence inputs are acceptable;
do not add a generic execution context framework, mixins, compatibility reexports
or a new repository facade.

Safety invariants requiring exact preservation:

1. A persisted reusable response bypasses new schema preflight, secret leasing and
   provider generation, preserving the original attempt identity. A dispatched
   attempt without a durable response remains non-resumable/UNKNOWN.
2. Keep current operation order and exception scopes. In particular,
   `GenerationRequest` construction currently follows the durable dispatch marker,
   and normalization follows the provider exception block. Extraction alone must
   not move them or change durable classification.
3. Known request-not-sent/response errors remain FAILED; outcome-unknown, historic
   base provider errors and unexpected provider exceptions remain UNKNOWN.
   Response persistence failure retains `storage.response_persist_failed`.
   Preserve subtype/code, redaction and failure disposition. No broad catch around
   the complete exchange and no new `BaseException` catch.
4. Repository-frozen exact-child scope owns target, reusable accepted siblings and
   explicitly frozen pending siblings. FAILED/CANCELLED/UNKNOWN siblings do not
   become replayable. Preserve candidate ordering and pre-seal recovery.
5. Keep cancellation/leases/locks and idempotent release at their actual owners.
   `LifecycleJobRunner`'s cleanup around start/admission and runner-level final
   release serve different failure paths; neither is redundant cleanup to remove.
6. No collaborator caches traces, facts, leases, schemas, candidates or sealed
   payloads across runs. Refresh evidence at the current correction-loop boundary.

## Ordered delivery and proof

1. **Baseline/preflight.** Recheck clean ownership, actual R interpreter/imports,
   checked dependencies and module allocations. Capture compact representative
   outputs before edits: planning/topology JSON/hashes/IDs/errors; registry/text/
   selection/projection/schema hashes; compiled primary/correction payloads;
   persisted evidence, call counts and durable outcomes. Exclude only observational
   timestamps, never authority fields. Derive the actual native case union
   (baseline currently 4,020 Python/1,538 frontend/358 browser); explain additions,
   moves and any scope-approved retirement rather than counting log/footer lines.
2. **G3 internal checkpoint.** Extract contracts/context first, then enqueue/stage
   planning and topology/content-fill ownership. Update consumers and ownership
   atomically. Run planning/graph/hash/aggregation focused checks and the small
   native project journey before broad G4/G5 work.
3. **G4 internal checkpoint.** Extract registry then selection/projection and schema
   families/assembly. Compare exact directive bytes, issue/fact indexes, branch
   order, errors and hashes for mixed-family accepted/refused/null/conflict cases.
   Run downstream correction postconditions and persisted source-authority cases.
4. **G5 internal checkpoint.** Establish runtime/evidence/source-verification/
   compiler owners, then exchange and unit/stage composition. Exercise the smallest
   real-adapter loopback journey as soon as the first useful cut is viable; do not
   postpone it until every extraction or unrelated infrastructure task is complete.
   Keep failed attempts and resume/reuse evidence distinct.
5. **Integrated stable review.** One independent read-only review checks the actual
   stable integrated diff, consumer ownership, parity and G5 delivery-certainty/
   source/release authority. Narrow checkpoint reviews are allowed when they resolve
   concrete risk; they do not require three full acceptance rounds. Reopen reviews
   only for concrete findings or material changes.
6. **Final qualification.** One execution owner uses existing focused/module tiers
   during development and runs `uv run --locked --no-sync python scripts/verify.py
   full` on the stable combined candidate. Preserve first failures. Diagnose and
   rerun failed/affected plus every unrun downstream gate; reuse unchanged evidence
   under repository policy. Repeat full when changed inputs invalidate it, not
   automatically for each batch or routine fix. Retain the exact smoke-passing
   wheel; narrowly repair a real retention gap using existing build/smoke tooling.
7. **Activate/close out.** Coherent local main checkpoint, quiet affected service/
   bridge activation, source/profile/readiness and data/media/settings/guard
   preservation/readback, single recovery refresh, then consume temporary evidence.
   Record actual results here and update the audit/roadmap/ADR. Stop after G3–G5.

### Small observable journeys and prerequisite limits

For G3, reuse `tests/test_generation_contract_integration.py` and current V3
`FixtureResolver`/`fixture_profile`: one choice/two endings, one scene/beat/shot per
footage node through actual `ProjectPipelineExecutor`/`LifecycleJobRunner`,
canonical installation, close/reopen and exact canonical/provenance readback.
Existing topology/join/route-only/option-cap and authored sibling-order cases
cover invariants absent from that minimum project.

For G5, drive a disposable project through the production
`OpenAICompatibleAdapter` and real HTTP against a deterministic loopback endpoint,
with current response fixtures from `tests/project_storage_fixtures.py`.
Use current native project/repository/runner owners and a disposable auth-none
profile; do not mock the adapter/session or change installed profiles/settings.
Prove one minimal Story Bible rejection → bounded correction → persisted valid
output/install/reopen, observing the dispatch marker before each wire request.
Reuse the existing fixture builders and error mutations instead of maintaining
another canned schema/response implementation.

At a crash/recovery point after durable response persistence, verify the same
attempt is recovered with zero additional HTTP requests. Existing exact-child
pending-sibling/pre-seal-loss, null/source-tamper, secret/profile and
UNKNOWN/known-failure/storage-failure tests remain required. Add only missing
coverage for actual new boundaries. Retarget monkeypatches to the actual new
compiler/verifier owners; do not retain accidental runner reexports for tests.

These are **provider-free production-owner/HTTP-adapter integrations**. They do
not establish external-provider availability/output quality or creative acceptance.
The installed creator's prior receipt reports `apiTextPipeline=false`; an
unrelated native Art task would not validate this durable text path. No external
provider generation is needed or proposed for this parity-preserving delivery.
If a future request requires live-provider E2E, establish a compatible composed
text runtime, disposable scope and actual provider authority separately; do not
silently invent that acceptance claim here. Loopback support is a small test
fixture, not another runner/provisioner or persistent QA installation.

Prerequisites are actual current V3 fixtures, compatible typed source evidence,
real local adapter/HTTP access and writable disposable roots outside P/live data.
Check them before broad implementation; resolve narrow in-scope blockers using
the smallest causal proof. A defect found in a required current-contract path
may receive a documented causal correction within this scope; distinguish its
intended delta from extraction parity. Material product/authority/risk changes
need owner review. Never weaken a guard or assertion to match a baseline.

### Existing focused coverage

Use current selectors/module expansion rather than treating this list as a
coverage ceiling: `test_planning_and_aggregation`, `test_story_graph_topology`,
`test_work_unit_prompts`, `test_correction_directives`, `test_correction_schema`,
`test_correction_postconditions`, `test_generation_contract_integration`,
`test_project_storage_generation_contracts`, `test_project_storage_direct_generation_regressions`,
`test_project_storage_exact_repair_pending_siblings`,
`test_project_storage_exact_repair_recovery`,
`test_generation_repair_authority_integration` and `test_stage_repair_retirement`.
Preserve snapshot/restore, provider, secret/profile and actual affected API/
acceptance/conformance consumers. Update `scripts/testing/module-ownership.json`,
support dependencies and ownership assertions with test moves. Cohesive
non-collected fixture owners replace collected-test imports/duplication only
where relevant; unrelated T1/T2 restructuring stays excluded.

## Operational authority for the combined implementation

The combined request covers scoped source/tests/docs in retained R, disposable local/loopback
fixtures and their cleanup, local verification/builds/main checkpoint, quiet
affected P backend and owned bridge reload, preservation/readback, planned code
rollback and refresh of the existing single functional recovery package.
No routine renewed approvals between G3, G4, G5, review, qualification and
activation. Standing task/model authority remains valid; native requirements and
genuine uncovered/material changes retain their real gates.

Use one source writer by default. Read-only review/checks may run in parallel.
Use Relay Direct for this implementation, choose and explicitly set models/
effort at native dispatch under the current skill/repository guide, keep agents
attended through actual finals and independent manager review, then archive and
remove exact reporting routes. Do not change active tasks/global defaults.

Before activation, recheck P ownership/status, actual writers/queue/slots/validator
and affected provider work. Fingerprint actual current projects/canonical/drafts/
media, application/host rows, reservations/revocations and protected settings/
credential/configuration/checked-environment files without exposing contents.
Counts from G2 are historical, not fixed acceptance targets. Wait for affected
healthy work and do not manufacture quietness by cancelling it or clearing holds.

Use existing `services/creator_workbench/manage.py` and supported launchd
lifecycle. Stop the quiet affected processes, compare stopped state before checkout,
activate exact qualified source, ensure fresh affected Python processes and check
actual imports/source SHA, health, ordinary project/read APIs and selected playback
availability. Derive P's own environment-specific profile using actual launchd
tool discovery and checked environment; preserve old pins. Ordinary readiness is
not generation. Recheck actual platforms; G2 qualified macOS arm64 Python 3.12.13
and observed Linux aarch64 3.12.15, not a full Linux suite.

On activation/identity/preservation failure, use the previous qualified source/
wheel and supported service lifecycle, then recheck readiness and preserved state.
No data migration/reset/rollback is authorized or needed for this contract-preserving
scope. If a narrow repair materially changes qualified inputs, requalify affected
evidence before another activation.

After successful readback refresh only `.local/current-qualified-recovery`.
Validate all new source/submodule members and the exact passing wheel before
replacing the previous working package; verify after replacement and remove the
superseded package. Keep no second archive or source fork. Temporary task evidence
belongs under supported ignored `.local/`, never an undeclared root. Retain compact
failure/parity/qualification facts in this plan/current manifest, then remove
consumed logs, traces, fixtures and package copies. Documentation-only final sync
needs no repeated full run/restart when executable inputs are demonstrably unchanged.

## Completion criteria and implementation discretion

- [ ] All G3/G4/G5 responsibilities have real cohesive owners; no forwarding
  barrels, new mixins/framework or return imports into coordinators.
- [ ] Planning/topology/IDs/versions/hashes, directive text/selection/projection,
  schemas, errors, prompt/evidence bytes and source authority preserve baseline;
  any separately justified correction is explicit.
- [ ] Early native project and real-adapter loopback/recovery journeys pass,
  with honest external-provider and creative-acceptance limits.
- [ ] UNKNOWN/no-replay, dispatch order, secret/profile/lease/cancellation/release,
  exact-child/sibling/recovery and ordered seal/install guarantees pass.
- [ ] Existing cases/assertions survive; native allocation and relevant consumers
  are updated; independent stable review and final full-local/package checks close.
- [ ] Quiet installed identity/readiness/readback/preservation, rollback availability,
  single recovery refresh and consumed-artifact cleanup close.
- [ ] Retained main/installed handoff is coherent and clean, workers are actually
  idle/archived and exact reporting routes removed; no push/CI/provider expansion.

Target roughly 400 handwritten source lines per file and review every resulting
owner at 500. Actual responsibilities, dependency direction and testability decide
cuts. State the concrete rationale for a retained oversized owner. File names,
small cohesive helper placement, typed source-evidence inputs, focused selectors
and necessary consumer/fixture fixes remain engineering decisions within these
invariants. No prewritten code or per-helper owner permission is required.

## Planning review and handoff

An attended independent GPT-6.1 Sol / High read-only technical review checked
actual G5 lifecycle, exception boundaries, consumers and current owner tests.
It identified the request-construction/dispatch ordering and layered cleanup
requirements now explicit above, and confirmed that R1 already removed the old
stage-level bridge. No source or installed-state operations were performed.

An attended independent GPT-6.1 Sol / Medium review checked this combined plan
for unnecessary gates, arbitrary budgets/attempt caps, excessive serialization,
constraints on delegated judgment and material proof gaps. It found no material
issues and confirmed loopback feasibility with current auth-none fixtures and
the stated external-provider/creative-acceptance limits. Both reviewers returned
actual finals, released access and were archived. Requested settings were explicit;
effective host settings remain unverified. The manager checked source boundaries,
current fixture/selector names and local documentation consistency. This checkpoint
changes documentation only; implementation follows under the combined request.
