# G2: Work-unit binding, validation and repair ownership

Status: **implemented, independently reviewed and locally qualified through composite evidence; manager activation/preservation/recovery pending**.
Date: 2026-10-25. Source baseline: clean `main` at
`f7da50ee503f38c0cb8a63f36c169b930445319c` in
`/Users/wjmao/.codex/worktrees/b30f/plotloom` (R).
Installed checkout: `/Users/wjmao/projects/HU/plotloom` (P).

## Outcome, scope and authority

The owner requested planning G2 after the completed
[G1/R1–R3 delivery](2026-10-25-generation-contracts-and-retirements.md).
This plan owns the remaining compiler/binder/validation/repair responsibilities
identified by the [audit](../verification/2026-10-25-modularity-audit.md);
it does not reopen the completed retirements.

Deliver independently navigable owners for canonical fragment binding,
response schema/validation and repair derivation/source revalidation. Leave
`compile_work_unit_request` as the actual compilation entry point in
`generation/work_units.py`, with direct imports and no compatibility barrel.
Preserve current accepted/rejected behavior, field authority, deterministic
IDs, timing, issue/fact order, schemas, hashes, prompt bytes and persistence.

The owner approved implementation on 2026-10-25 with “Go ahead with Relay direct”.
The retained implementation baseline is clean local `main` at
`be17c45bef5d31a899639d70612263cdbc7a847a`. Standing authority for separate
Codex tasks and model/reasoning selection continues. This approval covers
the entire scoped implementation, local verification, local main checkpoint,
quiet activation, preservation checks, rollback and single recovery refresh
below, without repeated human milestone approvals.

**Stop when G2's responsibilities have moved, relevant consumers/tests are
updated, local qualification and installed preservation/readback are complete,
and the single recovery package is current.** Report any actual blocker or
unfinished operation plainly; source changes alone are not complete delivery.

Excluded: G3 planning/topology algorithms, G4 correction registry/schema-overlay
decomposition, G5 durable runner/provider/evidence lifecycle, backend domain/API
modularization, frontend work, schema/version changes, migrations/resets and
new provider/media generation. No GitHub CI, workflow changes or push.

## Design choice and current evidence

Use a responsibility-first extraction with stage-specific semantics and
repair-family owners. A stage-first package containing each stage's compiler,
schema, binder and repairs is also feasible, but would divide shared canonical
identity/timing and cross-stage continuity authority. The recommended structure
preserves those common authorities while making stage rules independently
inspectable. It builds directly on G1's existing contract leaves.

Current `work_units.py` is 3,583 lines. Static call inspection shows:
- Canonical binding (:879–1162) owns bound scene/beat/cue/shot/audio IDs and
  trusted duration apportionment.
- Validation adapters (:178–444), semantic checks (:2778–3274) and response
  schema/presence helpers (:3294–3583) have separate reusable responsibilities.
- Repair derivation (:1193–2650) and source assertions (:2653–2775) are consumed
  by the durable runner separately from request compilation.
- `_bind_fragment_foreign_keys` narrows the **model-facing schema**; it is not
  the canonical binder. `_continuity_requirements` reads frozen join context
  for the compiler, schema and Scene Beats semantics; it does not reconstruct
  planning context and is not currently used by the canonical binder.

These facts determine the boundaries; the goal is not to distribute arbitrary
line ranges. Implementation can choose file names and combine small helpers
where ownership remains clear.

## Proposed owners and interfaces

| Owner | Explicit inputs and output | Cohesion and dependency rule |
|---|---|---|
| Canonical fragment binding | Parsed Scene Beats/Storyboard response, immutable StagePlan/work unit and existing timing contracts → StageFragment. Expose canonical ID functions to their real consumers. | Keep bind operation, UUID identity and trusted scene-duration allocation together. No schema projection, repair dispatch, planning or repository access. |
| Frozen join-context requirements | Existing selector-scoped mapping → validated deep-copied join requirement projection, or existing WorkUnitContractError. | A named lower-level authority used by compiler/schema/Scene Beats semantics. No context reconstruction, new DTO/version or new hash algorithm. Reuse a suitable existing owner if it fits; no generic context bag. |
| Response schema and presence | Existing response model plus frozen unit/Bible/guidance/context → a fresh narrowed schema and existing presence issue tuple. | Keep stage constraint projection distinct from generic reference/presence traversal. Existing `json_schema.py` is only 123 lines and is a possible owner for the generic traversal; preserve its behavior rather than introduce a schema engine/dependency. |
| Scene Beats semantics | Parsed response plus existing unit, Bible, context and timing/capacity guidance → ordered ValidationIssue tuple. | One stage acceptance authority. Consume shared frozen requirements and existing semantic/validation functions; no compiler or new repair-derivation dependency. |
| Storyboard semantics | Parsed response plus unit, brief, Bible and frozen scene/beat/cue context → ordered ValidationIssue tuple. | Keep shot/cue/coverage/audio/continuity relationships in the same stage validator. No binder side effects. |
| Work-unit validation adapters | Same typed constructor inputs as today → existing ValidationReport contract. | Coordinate presence, alias-only parsing, stage semantics and trusted binding. Graph content-fill adapter moves only as an adapter; topology search/binding/diagnostic algorithms stay in the existing G3 owner. Factory selection may stay with compilation or these adapters, with one actual owner. |
| Repair families | Rejected value, exact stable issues and existing frozen family context → ordered typed facts; existing source assertions rederive and compare the same authority. | Group graph/join, continuity/entity vocabulary, Scene Beats dialogue, join-entry, and Storyboard entity/audio/timing by real authority. Keep derivation and its existing source assertion together. Reuse existing edge-entry, presence and timing owners where cohesive. |
| Explicit repair dispatch | Stage and existing frozen evidence → family calls in the current order; exact fact-to-issue assertion stays at the repair authority boundary. | Own a small explicit dispatcher independent of compilation. Families never import this dispatcher. No plug-in registry, dynamic family discovery or compiler forwarding API. |
| Request compilation | Existing GenerationPlan/StagePlan/unit, dependencies, brief/snapshot, instructions and renderer → CompiledWorkUnitRequest. | Retain frozen input checks, guidance verification, prompt-variable construction/rendering and provenance assembly. Import actual adapter owners. Do not import repair derivation merely to reexport it. |

All owners consume G1 contracts directly. Lower-level binding, schema, semantic
and family modules must not import `work_units.py`, the repair dispatcher or the
durable runner. The runner may import compilation, dispatcher and family source
assertions; its orchestration and error classification remain G5 and unchanged.

This does not forbid using a validation function from an existing cohesive
authority such as `scene_beats_edge_entry.py`, which intentionally carries the
same requirement through validation, facts and source assertions. Reuse that
module's validation function; do not split it merely to satisfy an import-layer
label or make stage semantics call repair derivation.

Do not pass the compiler/runner object, a mutable shared state object or a bag
of callbacks into the extracted code. Preserve explicit typed arguments.
`FragmentOutput` annotations must not create a return dependency on the
compiler; local type annotations or a genuine shared response-contract owner
are sufficient.

Aim for roughly 400 handwritten lines per owner. Review any owner reaching
500 and explain any retained oversized cohesive owner. Do not add the extracted
algorithms to G1 contract files or create another large `helpers.py`.
Existing 527-line `storyboard_timing_repair.py` already owns one complete timing
plan/constructor contract: a small matching wrapper may belong there, with an
explicit cohesion rationale, rather than forcing a separate file for one
function. A distinct responsibility should have its own owner.

The compiler should finish with compilation-related orchestration only.
Report its actual resulting size and responsibilities. If it remains above
500, provide an architectural rationale for that concrete result; do not
declare G2 complete while binder, stage semantics or repair-family algorithms
remain there under renamed helpers.

## Invariants that extraction must preserve

### Binding and field authority

Author intent and the frozen Bible/graph/context remain authoritative.
Models own response-local content and handles; trusted code owns StagePlan/unit
identity, canonical IDs, duration arithmetic, audio IDs and canonical
coverage-link construction/roles. The model still supplies shot-to-beat
assignments, which trusted code validates against exact coverage requirements.
Repository owners retain admission, leases, sealing, installation and recovery.

Preserve UUID namespace/version and parent scoping; cue/shot/audio indexing,
one-based audio event numbering, primary-link ordering and supporting coverage.
Preserve integer largest-remainder duration allocation, dialogue minima,
authored-order ties and exact node-budget conservation. Do not normalize bad
model order/IDs into acceptance or change the existing local-ID deepcopy step.

No changes to enqueue snapshots, frozen guidance, timing/profile derivation,
allowed source membership or aggregate seal semantics are authorized. Pure
binding must not acquire repository/provider access.

### Validation and schema behavior

Keep this order: **presence → alias-only DTO parsing → ordered stage semantics
→ trusted binding**. Binding exceptions represent program/plan faults; they
must cross the existing fail-closed runner boundary, not become model-correction
issues through a new broad exception handler.

Preserve strict missing-versus-null rules, supporting-array presence,
empty nullable enums, bool-versus-integer checks, local JSON references and
existing anyOf/oneOf/allOf branch behavior. Preserve exact issue codes, paths,
messages, ordering and early-return behavior. Schema helpers may modify only
the fresh schema copy they own; repeated calls, other adapters, rejected source
values and frozen context must remain independent.

For graph content-fill, keep the existing topology owner and native non-finite
value check before JSON model dumping, plus binding/diagnostic append order.
Do not rewrite the graph algorithm or its accepted variants as part of moving
the adapter.

### Repair evidence and source binding

Preserve each family's current malformed-source behavior, including returning
an empty fact tuple where it does today. Preserve fact ordering, cue membership
deferral and the rule that Storyboard timing-plan facts suppress audio facts.
Join source revalidation must use the complete stable issue set and compare
preserved siblings, not just the target key.

Keep the G1 discriminated union, exact-type admission, stable evidence
model-name labels and null-preserving `repair_facts.py` codec. Qualify the
actual validation-artifact → serialize → parse → source-revalidation path,
including authorized null targets, sibling assignments and continuity facts.
A model_dump-only comparison is insufficient.

Move existing family assertions with their derivation; do not invent new repair
authority or relocate the runner's correction-packet compiler/lifecycle.
Runner changes should be direct import/call-owner updates, not G5 extraction.

## Ordered implementation and evidence

1. **Preflight and compact baseline.** Recheck source/status, direct consumers,
   actual R interpreter/import roots, checked dependencies and current
   module/support allocation. Before moving code capture representative schema,
   prompt/contract hash, bound-fragment JSON, issue tuple and fact/artifact
   round-trip results. Include valid and invalid inputs, dialogue allocation,
   audio IDs, coverage, continuity and graph/join cases. Exclude only genuinely
   observational envelope timestamps from comparisons; never omit a contract
   field to force parity. Keep temporary hashes/small projections, not an old
   source fork, media archive or duplicate model implementation.
2. **Canonical binding first.** Extract binding, canonical IDs and duration
   allocation; update actual consumers. Verify ID namespaces, dialogue floors,
   rounding ties, budget conservation, primary/supporting links and nonzero
   audio event IDs. Attempt the small real-owner project integration below
   before broad extraction or qualification.
3. **Validation owners.** Establish lower-level frozen requirement projection
   and schema/presence ownership, then per-stage semantics and adapters. Move
   the graph adapter without touching G3 topology algorithms. Compare schemas,
   valid fragments, exact invalid issue tuples and trusted-fault propagation
   after each cohesive cut. Update imports atomically with the moved owner.
4. **Repair families and explicit dispatch.** Move one cohesive family and its
   source assertion at a time, updating runner/qualification/test consumers
   directly. Keep an explicit independent dispatcher with existing stage/fact
   order and source issue binding. Reuse current small family owners. Compare
   persisted evidence and tamper refusal, then complete the exact-child
   repair/reuse/recovery integration below.
5. **Test ownership and stable review.** Preserve all current assertions/cases.
   Move/split mixed-family tests only where that matches the new production
   owners, sharing existing non-collected fixtures instead of duplicating
   builders or importing collected tests. Update
   `scripts/testing/module-ownership.json`, support dependencies and
   `tests/test_verification_module_ownership.py` consumer expectations together.
   Compare the complete native case union, accounting for new cases and
   selector moves. G2 retires no current contract or test family.
   An independent read-only reviewer checks stable code/evidence, dependency
   direction, hash/order parity and error/source authority. Fix concrete
   in-scope findings and rerun affected selections.
6. **Stable final qualification.** Use existing focused/module tiers while
   developing; one execution owner runs the final full-local gate on a stable
   integrated candidate: `uv run --locked --no-sync python scripts/verify.py full`.
   Preserve first failures honestly, diagnose narrowly, and reuse evidence only
   while its executable/dependency/configuration inputs remain unchanged.
   If a fixture repair permits reuse, run the failed/affected checks and every
   unrun ordered gate; retain the failed full result rather than relabel it a
   pass. Repeat full when material changes invalidate its evidence, not after
   every extraction. Retain the exact passing wheel through existing tooling,
   or narrowly close a real artifact-retention gap with build/smoke; no new
   runner/framework or weakened coverage.
7. **Activate and close out.** Preserve a coherent local main checkpoint,
   complete the scoped installed identity/readback/preservation operation
   below, update the existing single recovery package and remove consumed
   task artifacts. Update this plan, roadmap, audit status and ADR 0220 with
   actual results. Stop here; do not automatically begin G3–G5.

### Small observable proof

Reuse `tests/test_generation_contract_integration.py` and the current V3
`FixtureResolver`/`fixture_profile` from
`tests/project_storage_fixtures.py`. In a disposable production-shaped
project outside installed/live roots, use one choice with two endings,
one scene/beat and one shot per footage node, no dialogue/audio.
Run the actual ProjectPipelineExecutor/LifecycleJobRunner, ordinary canonical
installation, close/reopen and compare canonical plus prompt-provenance
readback. Add or reuse focused nonempty dialogue/audio/coverage fixtures for
binding behavior the minimal project cannot exercise.

For repairs reuse the current exact-child pending-sibling, tamper, pre-seal
process-loss and durable-response reuse fixtures. Show quarantined unit →
existing eligible exact child → preserved sibling reuse → ordered seal/install
and reopen. Exercise source assertions after persisted fact parsing, not only
direct function calls. Cleanup belongs to the source/qualification owner
through the supported disposable lifecycle after quiescence.

This is **provider-free runtime integration**: deterministic responses enter
at the provider boundary while real project, validator, executor and persistence
owners run. It establishes neither live generation nor creative acceptance.
Do not use an unrelated native Art smoke as evidence for G2; the predecessor's
creator installation did not expose its HTTP text pipeline.

No new provider/media generation or generation budget is needed for this
parity-preserving scope. Existing authority remains applicable within its real
limits; a discovered material behavior change or new provider/fallback requires
a deliberate scope/authority decision, not hidden widening.

### Focused safety/consumer coverage

Use actual current selectors and existing fixtures, including:
- `test_m12a_contracts`, Scene Beats/Storyboard fragment contracts and work-unit
  prompts: binding, aliases, IDs, schema constraints and frozen guidance.
- Continuity, join values/topology and work-unit scene facts: family authority,
  context/source tamper, nulls, complete sibling comparison and fact order.
- Correction directives/schema/postconditions: unchanged downstream evidence
  interpretation and acceptance; no G4 algorithm changes.
- Direct generation, exact repair/recovery, installation/sealing, snapshot/
  restore and secret/provider regressions: surviving runtime guarantees.
- Existing G1 cold-import boundaries plus new meaningful dependency checks:
  lower owners can import without loading the compiler/runner/dispatcher, and
  concrete source assertions still reject foreign evidence.

Choose exact affected cases/module unions after inspecting the diff, rather
than treating this list as permission to omit affected consumers. Tests should
guard behavior or ownership; do not add line-count assertions or mirror every
moved helper. No broad unrelated T1/T2 test restructuring is included.

## Operational scope proposed with implementation approval

G1's completed activation is precedent, not independent authorization for a
new G2 rollout. Approval of **this** plan is intended to cover scoped source,
tests and documentation; local verification/main checkpoint; disposable
fixture creation and cleanup; quiet backend/affected owned-bridge activation;
preservation and rollback; prospective source/profile readiness; and refresh
of the existing single functional recovery package. Carry that approval
through ordinary in-scope fixes without new per-slice or per-test approvals.
Standing thread/model permission remains valid.

Use the retained checkout serially with one source writer and one qualification
owner. Independent read-only review/independent checks may run alongside work;
the serial source rule is not a global prohibition on useful parallel reading.

Before deployment inspect current P/source ownership, runtime, protected
configuration and actual queued/active/validator work. Record source/runtime/
platform identity; the predecessor qualified macOS arm64 CPython 3.12.13 and
observed installed Linux aarch64 CPython 3.12.15, not a full Linux test run.
Recheck actual versions and prerequisites rather than assume historical health,
inventory or credentials. No settings/credentials are printed or changed.

At the quiet checkpoint preserve the actual current project/canonical/draft/
media inventory, application/host state, reservations/revocations and protected
fingerprints. Wait only for affected processes and writes that can race this
activation. Leave unrelated gateway/voice work alone; do not cancel healthy
work, clear UNKNOWN or reservations, repin attempts, signal unrelated processes
or bypass guards to manufacture quietness.

Use existing `services/creator_workbench/manage.py` and supported launchd/
deployment lifecycle. Backend imports need a fresh process; `start` can reuse
an unchanged owned bridge, so verify and reload it if required. Install the
exact qualified source/package, then verify actual imports/source hash, health,
ordinary project/read APIs and existing selected-playback availability.
Compare preserved data/configuration/guards before and after, not old fixed
eight-project or 26-stream counts.

Python moves change prospective source/profile hashes. Use the existing profile
builder, checked runtime/toolchain and ordinary readiness plus exact-package
smoke, deriving P's own environment-specific profile. Keep old job/profile pins
immutable. Do not start the unrelated opt-in serial/parallel qualification pair,
add a grant, change providers/settings or claim native generation from readiness.

If local qualification fails, keep the candidate out of P. If activation/
identity/preservation fails, use the existing qualified code/package rollback
and supported service lifecycle, then recheck readiness and state. No data
rollback/migration is authorized or needed for unchanged schemas. Ordinary
causal repair and planned rollback are covered; a genuine material risk/scope
change needs new authority.

After successful readback refresh only the existing
`.local/current-qualified-recovery` source/wheel/manifest package. Verify new
contents before replacing the old working package, keep no second archive,
then delete consumed task snapshots/parity outputs and disposable fixtures.
Documentation-only closeout sync needs no second restart when executable
identity is demonstrably unchanged. A concise receipt in this plan and current
manifest suffices; do not accumulate raw browser/failure/media archives.

## Acceptance and implementation discretion

- [x] Canonical binding, schema/presence, stage semantics/adapters and repair
  families have actual cohesive owners and no return import to compiler/runner.
- [x] Compilation contains compilation orchestration only; repair routing is
  explicit and independently owned. Consumers use actual owners, not wrappers.
- [x] Current schemas/prompts/versions, canonical IDs/durations/coverage and
  exact issue/fact/artifact outputs match the baseline, including nulls.
- [x] Trusted program faults remain fail-closed; malformed/foreign repair
  evidence cannot widen authority, become retryable or bypass source checking.
- [x] All surviving tests/assertions/native ownership and relevant consumers
  are preserved; small runtime/repair proof and stable review are complete.
- [x] Final local qualification and exact wheel/isolated installed checks have
  truthful results, revisions, environment and failure/repair accounting.
- [ ] Quiet activation, P-specific identity/readiness, data/media/settings/
  guard preservation, rollback availability and single recovery update pass.
- [ ] Local main handoff is coherent and clean; temporary artifacts are removed;
  attended workers return actual finals and are archived/unregistered.
- [x] Resulting sizes/cohesion and pending G3–G5/other audit batches are explicit;
  no provider generation, creative acceptance, push or hosted CI is implied.

The implementer chooses cohesive file names, helper placement, adapter/factory
placement, exact focused selectors and small necessary dependency fixes.
Reusing an existing family owner is preferable when it preserves its authority;
a separate owner is preferable for a genuinely distinct responsibility.
No prewritten implementation or new owner approval is required for those
engineering choices. Amend ADR 0220 with G2's ownership/parity decision after
implementation approval, linking this plan rather than duplicating G1 rationale.
Use Relay Direct to manage approved implementation and the repository's model
guide at dispatch; do not introduce parallel source writers.

## Planning review

Independent read-only GPT-6.1 Sol / Medium review found no unnecessary approval
gates, invented budgets/attempt caps, excessive serialization or restrictions
on engineering judgment. Its ownership wording correction is applied: model
shot-to-beat assignments remain model-owned, while trusted code validates and
constructs canonical links. Manager source inspection also clarified that
existing cohesive requirement modules may expose their validation functions;
this avoids forcing unrelated splitting merely for a layering label.

The reviewer checked dependency boundaries, the independent repair dispatcher,
artifact/null-codec parity and G3/G5 exclusions. Requested settings were explicit;
effective host settings remain unverified. It returned its actual final and
released access. Manager documentation checks and archive/reporting cleanup
complete the planning handoff. No implementation, tests/builds, live inspection,
provider, installed-state or recovery operation occurred during planning.


## Implementation and stable-review receipt — 2026-10-25

The owner approved “Go ahead with Relay direct”. Sole source/test/docs worker
`01a1754c-d457-77c2-806b-3e72488bb0dc` registered its native Relay route to manager
`01a04525-e907-7630-9640-78790d69e8ae` before edits. Requested GPT-6.1 Sol / High
settings remain host-unverified. Work uses R's locked `.venv/bin/python`, Python
3.12.13 on macOS 27.0.1 arm64, importing R's actual `src/plotloom`; dependencies
remain unchanged and `uv lock --check` passes.

### Actual ownership and cohesion

| Owner | Lines | Responsibility |
|---|---:|---|
| `fragment_binding.py` | 327 | Canonical scene/beat/cue/shot/audio identity, integer duration allocation and canonical coverage construction. |
| `frozen_join_requirements.py` | 41 | Existing frozen join requirement validation/deepcopy, shared by compiler/schema/Scene Beats semantics. |
| `fragment_schema.py` / `json_schema.py` | 203 / 218 | Stage-specific schema constraints / generic reference, branch and presence traversal. |
| `scene_beats_semantics.py` / `storyboard_semantics.py` | 400 / 402 | Ordered stage acceptance without binding side effects or repair-derivation imports. |
| `fragment_validation.py` / `story_graph_validation.py` | 286 / 189 | Presence, alias-only parsing, semantics and trusted binding / existing graph-topology adapter. |
| `graph_semantic_repair.py` | 447 | Graph/join facts with complete preserved-sibling source assertion. |
| `continuity_repair.py` / `entity_state_repair.py` | 360 / 221 | Sequence facts/source checks / frozen Bible state facts/source checks. |
| `scene_beats_dialogue_repair.py` / `scene_beats_join_repair.py` | 384 / 104 | Capacity, node-budget and source-bound cue order / frozen join-entry facts. |
| `storyboard_audio_repair.py` / `storyboard_timing_repair.py` | 108 / 571 | Exact overflowing audio events / complete text-free timing guidance, plan and issue-bound constructor. |
| `semantic_repair.py` | 208 | Explicit ordered family dispatch and exact issue admission, independent of compilation. |
| `work_units.py` | 489 | Frozen input/membership checks, timing/capacity agreement, prompt variables/rendering and provenance assembly. |

No G2 algorithms remain in the compiler behind forwarding helpers. Lower owners
import neither compiler, dispatcher nor runner. The compiler directly consumes
actual validation and requirement owners; runner changes are imports only.
The pre-existing edge-entry/presence owners remain cohesive and directly reused.
All 47 original top-level algorithms/adapters have a real owner; AST comparison
found only the correction of a deferred nested graph-join annotation to its
actual `StoryGraphJoinContentFill` type, with no algorithm change.

The compiler remains above the 400-line target because frozen input agreement,
prompt construction and the explicit provenance record are one compilation
operation; it is below 500. The timing owner was reviewed at its pre-existing
527 lines. Adding its matching 43-line fact constructor leaves 571 lines: the
constructor references the same complete guidance/plan/hash authority, so a new
wrapper owner would fragment that responsibility. No unrelated oversized files
were refactored or split solely for counts. Generation evidence remains 350 lines.

### Early product proof and exact preservation

Before broad extraction, the binder cut passed 40 focused cases including the
small current V3 project through actual `ProjectPipelineExecutor` and
`LifecycleJobRunner`, canonical installation, close/reopen and exact canonical
plus prompt-provenance trace readback. It uses one choice/two endings, one
scene/beat/shot per footage node, no dialogue/audio. Separate nonempty
cue/audio/coverage cases passed at this early checkpoint. New authored-order
rounding coverage proves dialogue floors, a largest-remainder tie and exact
budget conservation even when the response array order is reversed.

The pre-edit 107-case selection captured 620 return hashes for fresh narrowed
schemas, prompt/contract hashes, accepted bound fragments, rejected ordered
issues, ordered repair families and actual null-preserving codec returns.
The final same selection passes and all 620 hashes match, with no missing,
added or changed observation. No schema, prompt byte, version, ID namespace,
coverage authority or timing algorithm changed. Supporting source/name/null
assertions and malformed-source empty-fact behavior remain intact.

The exact-child pending-sibling case now also closes/reopens and compares
canonical plus child trace readback after quarantine → eligible child → sibling
reuse/pending execution → ordered seal/install. Current pre-seal process-loss,
durable primary/correction response reuse, tamper, snapshot/restore and secret
regressions pass. This is provider-free runtime integration, not live generation
or creative acceptance.

### One demonstrated persistence false-positive correction

The new actual persisted-continuity proof exposed a predecessor blocker:
`ContinuityFactAssignment.key` was treated as a credential field by the generic
artifact setting-name guard. Direct codec tests had not exercised this durable
boundary. The manager explicitly included its narrow causal repair because the
approved plan requires artifact → JSON → codec → source revalidation.
This is the sole intended behavior correction, separate from the 620 unchanged
pure-extraction observations; it restores persistence of an already admitted
current typed contract.

`generation_evidence.py` checks credential-shaped values against original whole
content first. Only a rejected work-unit VALIDATION artifact with matching
current contract/stage/unit and stable issues can receive a nonmutating scan
projection. Its raw repair list is closed-union parsed and must exactly match
the existing canonical serialization; raw extras/duplicate aliases are retained
and refused, never dropped. Only actual continuity fact assignments have their
structural `key` omitted from the setting-name scan. Secret-shaped fact names,
expected values/nested fields and every other content location remain screened.
Persisted content, aliases, nulls and hashes stay exact. Generic raw response
persistence and existing `[redacted]` behavior remain unchanged; no lease,
transaction, runner lifecycle or global secret policy was changed.

Actual persisted join/null/sibling and continuity/null facts survive JSON/codec
parsing and runner source assertions. Tampered assignments refuse before another
provider-boundary call. Twenty-three credential-context cases cover secret fact
names/values/nested fields, sibling/outside keys, malformed/unknown/extra/duplicate
aliases, typed/untyped lookalikes, wrong kinds/context and raw response persistence.
Refusals precede any write lease and create no artifact row. The stable independent
review must include this guard correction before final full qualification.

### Executed scope and remaining gates

- `focused`: original parity selection, **107 passed**; final 620/620 hashes equal.
- `module --module shared-generation --depth contract`: native ownership guard,
  frontend type contracts, **207 Python + 33 Vitest passed** (17.034 s).
- Final runtime/authority/ownership focused union: **96 passed** (21.403 s),
  including both real-owner integrations, exact repair/recovery, all 23 security
  cases, generation secret regressions and module/support assertions.
- Native union: **3,985 → 4,019 Python cases**, all 3,985 retained unchanged;
  34 additions (4 owner/isolation/rounding, 2 schema-presence, 5 durable authority,
  23 security/redaction). No current family or assertion retired.
- Source imports, locked dependencies and whitespace checks pass. The existing
  FastAPI/httpx deprecation warning is unchanged.

The exact-scenario runner/provider helpers moved once into non-collected
`tests/project_storage_generation_support.py`. Native module/support ownership
and `tests/test_verification_module_ownership.py` consumer expectations changed
atomically. No collected test imports or duplicate fixture builders were added.

Review initially retained ignored evidence under R's `.scratch/g2/`: `baseline.json`,
`final-parity.json`, `ownership-parity-summary.json`, `case-union-summary.json`,
`parity-final.log`, `module-shared-generation-final.log` and
`runtime-focused-final.log`. The raw large native collection was replaced with
small case-identity hashes; no old-source fork or new archive exists. These are
consumable task evidence, retained through review/final qualification; the source
worker removes consumed R artifacts on follow-up, coordinated with the manager's
single recovery refresh. Fixtures are disposable pytest projects; current runner
and project handles close after the new reopen proofs.

The stable-review checkpoint below supersedes the preceding pending qualification
status; its final evidence lives under supported `.local/g2/`. The manager owns
P activation, preservation, rollback/readiness and the
single recovery refresh after qualification; this worker touched no P/live data,
settings, provider operation or recovery package. Hosted CI/push were not requested
and were not run. G3–G5, API/domain/frontend and unrelated T1/T2 remain excluded.
Known execution times are recorded above; separate implementation/infrastructure/
coordination wall-time measurements are unavailable. This checkpoint releases
source/process access for review, and is not final delivery or a new owner gate.


## Final source qualification receipt — 2026-10-25

Independent GPT-6.1 Sol / High stable/security review closed `7c6d54ee` without
blocking findings; the manager also inspected the actual guard and callers.
The reviewer verified the 47 algorithm/adapter owners, the sole deferred nested
annotation correction, strict raw-content/alias/context screening and nonmutating
scan projection. The 620 pure-extraction observations remain unchanged; the one
supported-continuity persistence correction remains explicitly separate above.

Product code is qualified at `7c6d54ee4dc35c41a8e089106e9b25d92dc833c5`.
Test-only snapshot proof is `92670a29e11094937902395ca7b00896f062ff0b`;
test-only browser stabilization is `eaf758d4b7842e7d883f17167a99e51d4ca766f8`.
The manager inspected and accepted both narrow test additions. No product,
dependency, schema, prompt, provider, bundle input or source/profile identity
changed during final qualification.

### Persisted continuity evidence really survives recovery

The new positive case creates current continuity validation evidence through the
native runner, including `{kind: fact, key: weather, expectedValue: null}`.
After closing the source handle, it uses supported snapshot/export and restore
into a fresh installation root. The restored artifact content and hash are exact;
JSON/codec round-trip, stable-issue binding and source assertion all pass using
the restored response and Story Bible. The whole security/recovery file passes
24 cases (0.64 s; focused tier 1.953 s). Two fixture-only diagnostics were corrected:
exclusive snapshot requires closing the source handle, and a valid three-stage
project needs a stage-specific payload read rather than the four-stage aggregate
convenience method. No product change was needed.

Native Python allocation is now **4,020 = 3,985 retained + 35 additions**,
with zero removals or current-contract retirements. The final native fingerprint
is `a9bed6351b7c574aa66fb32cc27977b42146e901bbcd77ce7b938335b4a4264e`.
The additional case is the snapshot/restore proof; the earlier 34-case accounting
above describes the preceding stable candidate. Browser allocation remains
99 specs/358 cases with zero overlap or missing cases; frontend units remain 1,538.

### Actual failed attempts and composite closure

The actual command `uv run --locked --no-sync python scripts/verify.py full`
ran once on stable `92670a29` and **failed**, exit 1, after **1,409.178 s**.
All earlier gates passed: locked dependencies, ffmpeg/ffprobe, API unused imports,
archived reader, all 1,538 frontend tests and app type checks. Python took
1,397.505 s and completed both partitions:

| Partition | Actual result | Pytest seconds | Runner seconds |
|---|---|---:|---:|
| 1, 2,152 assigned cases | 2,151 passed; 1 failed | 900.95 | 914.453 |
| 2, 1,868 assigned cases | 1,868 passed | 1,370.76 | 1,384.368 |

The sole Python failure was
`test_extraction_contract.py::test_clean_repository_has_only_declared_product_roots`:
my task-owned `.scratch` directory violated the declared-root boundary even though
Git ignored it. Evidence moved atomically to supported `.local/g2`, and the empty
undeclared root was removed. The exact boundary rerun passed (1 case, 0.06 s;
focused tier 1.667 s). No product/test assertion, dependency or configuration was
changed for that environment correction; the original full result remains failed.

The existing `verify.py` step builder/runner then executed every unrun step in
order, with a retained wheel directory. Its first downstream run passed bundle,
asset parity and allocation, then **failed** the unfiltered browser phase:
357 passed and one failed (651.510 s; follow-up total 655.089 s).
The first gallery reading-state capture measured bottom 1284.609375 against the
unchanged 888 bound at 1700×900. Trace showed one scroll followed immediately by
bounding-box sampling while another mocked 503 read settled; scrollTop stayed
116. Independent manager trace review agreed this exposed a test layout-settling
race, with no changed G2 response path or product reachability contract.

The narrow helper correction re-scrolls/polls observable geometry before retaining
all original bounds, three viewport sizes, screenshots and zero-write assertions.
The full affected three-case file passed (12.3 s browser; focused tier 14.825 s),
with the e2e type check and current allocation guard passing. No assertion or case
was removed. An unchanged diagnostic rerun was unnecessary after trace review.
The first browser result remains failed; the other 357 cases and earlier gates
remain reusable because no product/runtime/bundle/dependency input changed.

| Remaining full gate | Final evidence | Seconds |
|---|---|---:|
| Deterministic production bundle | passed | 1.664 |
| Checked production asset parity | passed; no tracked static diff | 0.033 |
| Unfiltered browser allocation | passed; rechecked after helper change | 1.882 |
| Browser coverage | 357 initial passes + corrected complete 3-case file; all 358 covered | 651.510 + 14.825 focused |
| Retained wheel build | passed | 0.127 |
| Exact isolated installed-wheel smoke | passed | 4.423 |

The original full and browser follow-up attempts remain failed. Together with
their assertion-preserving targeted corrections and all ordered remaining gates,
**local qualification is complete through composite evidence**. No duplicate full
or reduced release coverage was used. Existing FastAPI/httpx deprecation and
Playwright color-environment warnings are unchanged.

### Exact retained package and prospective identity

The exact wheel that passed smoke is
`.local/g2/wheel/plotloom-0.1.0-py3-none-any.whl`, **1,581,963 bytes**,
SHA-256 `20d1de4bbfe399af1abdfcc7adfd408b6f0e62286f4f3ecc93e4761e353567da`.
All 495 package files match source bytes, with exact inventories of 475 Python
files and nine prompt files and no bytecode. Its sorted package-name/SHA-256
inventory digest is
`9b000594e336a35dec9ff71d2c59372368b75f3bc9c5bccd12b7f0cf7ea62577`.
The existing smoke installs this exact retained wheel into a fresh environment
and runs from an unrelated working directory with isolated site-packages imports,
package-owned prompts, project persistence/snapshot and installed receiving.

The actual R prospective builder, checked Python receipt, toolchain and ordinary
login readiness pass: **v8 ready**, CLI `0.164.0-alpha.11.1`. Tests use R's
`.venv/bin/python` 3.12.13; the profile's checked interpreter is R's
`.local/codex-exec/python-env/bin/python`, with its receipt unchanged.
Source SHA-256 is
`f8457309a0ad52947c1f4a03860316586c7b760c80c0cc0e023b1188dc821e24`;
prospective R profile hash is
`2581f99f9c96088e191dcfd0832a86df00bcd20f25684fdc06ac25be60f0aaf8`.
Validator hash is
`799b47ab716c69fa41ac90b3461c2c35e1a270b839bd4b9cb181ee7f220d990d`.
These identities were rechecked after package qualification. P must derive its own
environment-specific profile while matching this qualified source; old pins stay
immutable. No opt-in serial/parallel pair, provider generation or grant was run.

Final ignored handoff contents are only `.local/g2/qualification.json` (compact
parity, security, case-union, source/profile, failure and qualification metadata)
and the exact passing wheel. Successful browser outputs, extraction helpers and
verbose logs were consumed and removed after their relevant reviews. No new
archive or raw-data backup was created. The source owner releases clean local main
and all task-owned verification processes; manager consumes these two artifacts
for P activation/readiness/preservation and the existing single recovery refresh.
That operational closeout remains pending. G3–G5 and all other excluded batches,
creative acceptance, GitHub CI and push remain outside this delivery.
