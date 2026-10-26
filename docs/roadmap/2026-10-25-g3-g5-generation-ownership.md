# G3–G5: Planning, correction and durable execution ownership

Status: **combined source implemented, independently reviewed and full-local qualified; manager operational closeout pending**.
Date: 2026-10-25. Planning source and installed baseline:
`a10a88592c25dfb4dad25aedffb1deb33136d8a7`.
Source R: `/Users/wjmao/.codex/worktrees/b30f/plotloom`, retained local main.
Installed P: `/Users/wjmao/projects/HU/plotloom`, planning-time detached baseline.

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

- [x] All G3/G4/G5 responsibilities have real cohesive owners; no forwarding
  barrels, new mixins/framework or return imports into coordinators.
- [x] Planning/topology/IDs/versions/hashes, directive text/selection/projection,
  schemas, errors, prompt/evidence bytes and source authority preserve baseline;
  any separately justified correction is explicit.
- [x] Early native project and real-adapter loopback/recovery journeys pass,
  with honest external-provider and creative-acceptance limits.
- [x] UNKNOWN/no-replay, dispatch order, secret/profile/lease/cancellation/release,
  exact-child/sibling/recovery and ordered seal/install guarantees pass.
- [x] Existing cases/assertions survive; native allocation and relevant consumers
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

## Source implementation checkpoint

Implementation began from clean retained `main` at
`c8ce6a80159d4bf2bcb64a0aadd1edbc68217c09`, using the checked R environment:
CPython 3.12.13, macOS arm64, imports from R and locked `uv` dependencies.
The source writer is native task `01a175a3-097e-77f1-a2ae-eda79c736cd8`,
registered through Relay to the manager before edits. The manager explicitly
selected GPT-6.1 Sol / High; effective host settings cannot be independently
confirmed from the worker context. No additional source writer was used.

G3 now has real `planning_contracts`, `enqueue_planning`, stage `planning` and
`planning_context` owners. Topology contracts/semantics, bounded search and
materialization, degree-bounded transition circulation, model-facing content
contracts/schema/manifest and trusted content binding/diagnostics are separate
cohesive owners. The small native four-stage project installed and reopened
before broad G4/G5 work; its planning/topology/journey selection passed 27 cases.

G4 keeps ordered static definitions/code uniqueness in `correction_registry`
and executable selection/projection in `correction_directives`. Existing G1
version constants remain in `correction_contract`. Graph/join, continuity/entity
state and cue/timing schema families collect authority one fact at a time in the
original traversal order; assembly applies them in the original family order.
This preserves first-conflict precedence across families. Schema fixture builders
now have one non-collected owner declared in module support allocation. Existing
assertions remain, with new mixed graph/cue null and conflict-order cases.

G5 gives runtime secrets/leasing and frozen provider resolution actual owners.
`work_unit_pipeline` retains stage order, exact-child local reuse, ordered seals
and `finally: release_run`; `work_unit_execution` owns the attempt/recovery/
rejection/correction/candidate loop. Complete durable exchange, evidence codec/
assertions, correction source verification and correction compilation have their
own implementations. Direct consumers and monkeypatch targets follow those
owners. Request construction remains after dispatch; response normalization stays
outside the provider catch block. Durable response reuse bypasses schema preflight,
leasing and generation. LifecycleJobRunner's separate cleanup remains unchanged.

The 589-line unit owner was reviewed after extraction. Its remaining large method
is one execution-local attempt loop whose allocation/recovery, validation outcome,
rejection/next-correction decision and candidate settlement share ordered control
flow. Provider exchange, persisted evidence and correction compilation/source
authority have already moved out. Another split would distribute that lifecycle
decision state without a new cohesive responsibility. Stage ownership is 390
lines; the other new source owners are at most 443 lines. No framework, callback
bag, mixin, compatibility barrel or repository facade was added.

### Evidence and limits at source review

Temporary review evidence is retained only in ignored `.local/g345/` until the
manager's integrated review. The pre-edit representative planning/topology/
directive/primary-request JSON and integrated result match SHA-256
`b0c146b44ea597b6c38b2a18154b9384988ca32878c5cf4885e3eb25f2cacfb1`.
Only typed `PromptTrace.rendered_at` is omitted; IDs, authority fields, order, nulls,
contracts, versions and hashes are retained. That sample alone is not exhaustive
correction or error parity.

The retained `correction_parity.py` probe loads trusted `c8ce6a8` source directly
from Git into private in-memory `plotloom.generation._g345_baseline_*` and
`plotloom._g345_baseline_work_unit_pipeline` namespaces. It writes no old-source
checkout or archive. Baseline runner imports bind moved planning/topology types
to their unchanged contract owners. Its directive/schema functions and associated
error classes bind explicitly to the original in-memory G4 modules; remaining
dependencies keep their current unchanged G1/domain/prompt/persistence owners.
It compares 21 schema outputs/errors and 25
directive/selection/projection outputs/errors while executing current assertions,
including mixed-family null/conflict traversal cases. It also compares complete
ordinal-1 and ordinal-2 correction packets against the same durable rejected
attempts: rendered messages/output/trace, contract, schema, audit selection and
executable facts. Dataclasses/models become JSON; only the real `PromptTrace`'s
own observational `rendered_at` field is omitted.
Errors compare type name, code and exact text in call order. All 48 comparisons
pass; retained result SHA-256 is
`701ec4c4c51e50070c865a83e4f96dd8a0baf636fac96f1dd4f93df9dd5cba3c`.
This is representative exact baseline parity, complemented by current assertions,
not an exhaustive proof over all possible inputs.

The `planning_parity.py` probe additionally compares enqueue/stage planning
errors, topology limits/option-cap errors, schema/manifest, valid binding and
missing/unknown/duplicate/non-finite diagnostics against trusted in-memory
baseline owners. It retains the exact compared outputs and error text/code.
All 18 comparisons pass; optional error attributes retain their presence,
including stage and the complete ordered code/path/message issue arrays.
Retained result SHA-256 is
`b406dc1c5f085aaf40cd5ce62310462af27422a3da01361bfd370a844b0b56a2`.

The real-adapter HTTP proof uses production `SnapshotTextProviderResolver`,
`OpenAICompatibleAdapter`, native project/repository and LifecycleJobRunner
against a disposable loopback endpoint serving current V3 fixture data. The
endpoint observes a committed dispatch marker before each request. One Story
Bible rejection is corrected, the correction response commits, simulated process
loss propagates, and startup recovery installs that same attempt with exactly two
total wire requests. Single-stage authoring envelopes and exact run evidence
survive close/reopen. No adapter/session is mocked. This establishes local
production-owner/HTTP fidelity, not external-provider or creative acceptance.

Retained failures are not passes: initial capture-helper import/attribute mistakes;
one generated schema-assembly syntax error; a content-schema helper assigned to
the binding owner causing a cold-import cycle; two HTTP attempts using an
unsupported correction cap for `compatible_v1`; and a single-stage readback
attempt using the full-pipeline `canonical_stages` convenience. Repairs bind
helpers to their actual schema owner, use the existing compatible preset and
single-stage authoring reader. A comparison probe initially attempted to create
a plan after quarantine; it now reads the existing plan from its actual owner.
No product behavior, assertions or authority were weakened for these repairs.

Native discovery preserves all 4,020 original Python cases and adds six: one
real-HTTP recovery journey, one mixed null/schema case, two conflict-order cases
and two cold ownership import orders. Current allocation is 4,026 Python,
1,538 frontend and 358 browser cases. Native SHA-256 values are respectively
`23e9fc3d768aedb155c8605e23f5b37337b72baa36f396f85a0dc9b426d4d55c`,
`87dd1b66fd7434fabb51ef264589d8cd9b20528f1f4bb1bade96b0ddb0e47394` and
`8eafc782d980de4197ad0eb268a52cc4edc3a14ebfc961dba1748fb4ec4b8fae`.
Quick passed; focused G4 passed 36 cases, persisted G5/source authority passed
14 existing cases, and mixed-schema/cold-owner checks passed 21 cases.
The combined scoped module selection and its resulting failures are recorded
below. Final full-local qualification, installed activation,
preservation/readback and recovery refresh remain later combined-delivery steps.
The source worker has not touched P, live state, providers/settings or CI/push.
Product implementation, infrastructure/fixture work and coordination time were
not separately measured; exact verification command timings remain in the
temporary logs. No usage/cost delta or category percentage is inferred.

The scoped `module --depth contract` selection was `shared-generation`, `graph`,
`project-lifecycle` and `shared-provider-dispatch`: 2,035 Python cases and 447
Vitest cases, plus native ownership preflight and frontend type contracts. The
original module command **failed**: 17 failures, 51 setup errors, 1,967 passes
and six warnings; Python bodies took 626.87s, whole module command 652.328s.
Its real subprocess fixtures clone HEAD and overlay only `git ls-files` source
plus explicit instruction/validator paths. Newly extracted owners had not yet
been staged, so these clones omitted `runtime_secrets`, `planning_contracts` and
`story_graph_topology_contracts`. Tracebacks confirm the missing-module cause;
an independent read-only `python -B` import reproduced the same failure in the
existing fixture. No production source/fixture logic change was needed.

After staging the legitimate new owners, the exact 68 failed/error nodes passed
with fresh tracked-source fixtures: 68 passes, one warning, 287.03s bodies and
333.101s focused command. A selector diagnostic first truncated parameter IDs
containing spaces; its preflight refused with no test bodies run. The corrected
selector list retains complete native IDs. The previously unrun exact module
Vitest command passed all 62 files/447 cases in 2.87s. The unchanged 1,967 passes,
native/type evidence, affected rerun and downstream Vitest complete this scoped
selection by composite evidence; the original module command remains failed.
No full-local gate has run at this checkpoint.

The direct Conformance and Alpha acceptance consumers lie outside that module
selection. Their exact focused files passed 20 cases (13.61s bodies, 16.192s
focused command). These fixture-operated checks establish current code behavior,
not external review or creative acceptance. Final read-only source/profile checks
confirmed all 21 actual owners import from R under its 3.12.13 interpreter and
the unchanged V3 auth-none fixture resolves to production
`OpenAICompatibleAdapter` without a network call. Fresh tracked-source fixture
imports now pass. Diff whitespace/changed-Python parse checks and native module
allocation pass. Temporary baseline/parity probes and compact failure/result
evidence remain in `.local/g345/` for independent review; extraction scripts and
duplicate observations were consumed. The coherent clean-main candidate is ready
for the manager's independent integrated review. Full qualification, installation
and recovery remain the combined assignment's next steps.

### Integrated stable review and evidence correction

Independent integrated production review of product revision
`30b27aa4fe1eca9945c8b8f2f5797d5252fea219` found no blocking source issues and
accepted the cohesive 589-line ordered unit lifecycle. The reviewer returned an
actual final, released access, and was archived/unregistered by the manager.
The manager independently checked durable exchange, the 199-line production
HTTP proof, probe baseline bindings and corrected output hashes.

One evidence-only finding is closed: the first probe normalizer recursively
dropped dictionary keys named `rendered_at`, broader than the intended timestamp
exception. Current fixtures showed no lost authoritative same-name value, but
the old normalizer could not prove that. The corrected normalizer pairs typed
objects with serialized values and omits only a real
`plotloom.generation.contracts.PromptTrace.rendered_at`. In-memory assertions
preserve authored root/nested values and untyped trace-shaped dictionaries with
that same key. Each omission logs exact path, typed owner, observed timestamp
and comparison context. The representative probe excludes exactly one
`/compiled/prompt/trace/rendered_at`; planning excludes zero fields; correction
excludes exactly four `/rendered/trace/rendered_at` fields, one each for current
and baseline ordinals 1 and 2. A first paired-walker attempt exposed enum mapping
keys' Pydantic JSON spelling; resolving those keys by serialized value corrected
the probe without adding any exclusion. The representative and all 18/48 exact
planning/correction comparisons pass with trusted baseline bindings unchanged.
The representative and planning hashes above are unchanged; the corrected
correction hash above supersedes the earlier observation. No product/source or
contract change resulted. The manager verified these exact exclusion records
and closed the finding before authorizing the sole-owner full-local gate.

## Initial planning review and handoff

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

## Final source qualification receipt — 2026-10-25

The owner explicitly confirmed **“Continue through activation”** during the
manager's scope clarification. The same source worker remained the sole final
qualification owner. Product revision is
`30b27aa4fe1eca9945c8b8f2f5797d5252fea219`; the clean review-documentation
checkpoint actually qualified was
`5f28e473ce565cc370965449c700ec95171bea9f`. No product change followed stable
review. Later receipt-only commits preserve executable, dependency, prompt,
bundle and source/profile inputs and need no repeated full gate.

Preflight passed the actual R interpreter/imports, locked dependencies, checked
Python environment, prospective v8 profile, toolchain and ordinary login
readiness. The full command was exactly
`uv run --locked --no-sync python scripts/verify.py full`, unfiltered, first
started at observed `2026-10-26T01:20:17Z` (October 25 locally), uv PID 48540,
runner PID 48548, execution session 61932. Native discovery confirmed 4,026
Python cases/328 files, 1,538 frontend cases/172 files and 358 browser cases/99
files with the fingerprints recorded above. Counts were observed, not forced.

The first actual **full run passed all 14 ordered gates in 1,931.706s**.
There were no failed full gates or full retries. Development's earlier failed
module command and its assertion-preserving targeted closure remain failed/pass
as separately recorded above; they were not relabeled by this full result.

| Gate | Actual result | Elapsed seconds |
| --- | --- | ---: |
| Locked dependencies, ffmpeg/ffprobe, API F401 and archived prompt reader | Passed | Per-step values in compact receipt |
| Unfiltered frontend unit suite | 1,538 passed | 6.398 |
| Frontend type contracts | Passed | 4.232 |
| Full native Python | 4,026 passed | 1,261.445 step; 1,248.824 runner |
| Deterministic production bundle and checked static parity | Passed | 1.306 + 0.021 |
| Unfiltered browser allocation and suite | 358 passed, four workers | 1.884 + 651.387 |
| Full temporary wheel build and isolated installed smoke | Passed | 0.127 + 4.229 |

Python used two isolated whole-file workers, PIDs 48974/48975 under runner 48928:
2,055 passed/one warning in 1,097.35s and 1,971 passed/nine warnings in 1,234.58s.
Both completion reports passed exact assigned-case/native-fingerprint validation.
Browser last-run status is passed with no failed tests. All recorded qualification
process handles exited; no source worker verification process remains active.

The existing full runner removed its temporary wheel directory on successful
exit. To close only that retention gap, a same-input
`uv build --wheel --out-dir .local/g345/wheel` followed by the existing
`scripts/smoke_installed_wheel.py .local/g345/wheel` passed. No runner/framework
or product/dependency change was added and no second full run occurred. The
retained wheel itself passed isolated installed smoke; byte identity to the
deleted original full wheel is not asserted. The existing uv-build range warning
was nonfatal and is retained in metadata; no dependency workaround was made.

Exact retained artifact:
`.local/g345/wheel/plotloom-0.1.0-py3-none-any.whl`, **1,597,847 bytes**, SHA-256
`fa2bccc70d27cd5636f496a72d983ebedd284f4b0f090bb0de9ed63627a3dfa5`.
Its complete package inventory exactly matches all 516 tracked package-source
files, including 496 Python files and nine YAML prompts, with no bytecode or
extra/missing members. License/notice bytes also match source. All 522 wheel
member hashes/sizes and applicable source mappings are retained in the compact receipt. The
sorted package-name/SHA-256 inventory digest is
`d422e801b17c9a2852e30c27348e52fbb0a7040110d5eff654844b695348bfa0`.

The qualified platform is **macOS 27.0.1 arm64**, test Python **3.12.13**;
the checked interpreter is R's `.local/codex-exec/python-env/bin/python`.
Tools are uv 0.13.1, Node 24.18.0/npm 11.16.0 and ffmpeg/ffprobe 9.0.2.
Post-package read-only checks reconfirmed the unchanged checked-environment
receipt, dependency pins, source and prospective v8 profile with ordinary
readiness **ready**, CLI `0.164.0-alpha.11.1`:

- Source SHA-256: `d65b7c5189150784401021e812804dbf5629b9eefe2467f7bfc5c671edc59f1f`.
- Prospective R profile: `79f5d8afeddd6c658dde352167e612e45aca8f48d80828a5bc7feb0fda55a886`.
- Validator hash: `2320ece25b4761ab2a10a575740158b48d0051294f99f02d33e0c1c2bd86ccaa`.
- Toolchain hash: `67792a8ac24d0a84f353af646dd604328ce6ac6d2582dd15ecca7ae0212f2e32`.

P must derive its own environment-specific profile against the same qualified
source; old frozen job/profile pins remain immutable. This is Mac full-local
software qualification, not a Linux full-suite claim, external-provider output
qualification or creative acceptance. No opt-in native qualification pair, new
grant, external-provider generation, P/live/settings/recovery change, push or
GitHub CI was performed by the source worker.

Manager-consumed parity probes, development logs, successful full/browser
outputs and temporary extraction/build helpers are consumed after their relevant
reviews. Final ignored handoff contents are only `.local/g345/qualification.json`
(complete compact review/parity/normalization/failure/native/profile/gate/package
metadata) and the exact retained passing wheel. No new archive or source fork
is retained. The source owner releases coherent clean local main and task-owned
process access for the manager's final evidence review, quiet P activation,
preservation/readback and single recovery refresh. Those operational steps and
the combined assignment's final delivery remain pending with the manager.
