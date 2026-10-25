# Generation contract leaves and retired execution paths

Status: **independently reviewed plan; awaiting owner implementation approval**.
Date: 2026-10-25. Source baseline: `096a573eef0081234e3309d0a8d1902afd05e248`
on retained `main` at `/Users/wjmao/.codex/worktrees/b30f/plotloom` (R).
Installed checkout: `/Users/wjmao/projects/HU/plotloom` (P).

## Goal, agreement and stopping condition

The owner accepted the [modularity audit](../verification/2026-10-25-modularity-audit.md)
recommendation to start G1 and retire R1–R3, then requested planning through Relay
Brainstorm and Plan. This approves the design direction and planning, **not
implementation or operational changes yet**. Standing permission for separate
Codex worker threads and model/reasoning choices remains valid.

Deliver **G1 leaf generation contracts**, remove its import-cycle workaround,
and retire three obsolete execution contracts: legacy scope-less stage repair,
generic raw-media execution and Atlas/Wan fallback. Preserve the supported
durable generation/exact-repair path, managed image/H3 work, readable current
projects, snapshot/restore, credentials and uncertain-dispatch safeguards.

The complete implementation outcome proposed for approval includes source
changes, assertion-preserving tests, current ADR amendments, one local main
checkpoint, local qualification, quiet activation in P, preservation checks and
refresh of the existing single functional recovery package. No push or GitHub
CI. Stop when those outcomes have evidence, or report a concrete blocker without
claiming unfinished activation or real provider acceptance.

This is the first bounded implementation from the audit, **not completion of
all 52 extraction recommendations**. G2–G5, backend domain/API modularization,
frontend changes and documentation styling remain named, unselected audit
batches; do not sweep them into this assignment.

## Why this sequence

Two reasonable sequences are possible: retire old paths first to shrink the
tree, or establish the shared leaf contracts first to stabilize imports and
parity evidence. Use **G1 first, then R1, R2, R3**, with focused checkpoints and
one integrated qualification. G1 addresses the observed cycle and gives the
subsequent removals a cleaner current dependency surface. The retirements are
small enough to follow serially; a combined compiler/runner rewrite would
obscure behavior parity and is outside this scope.

The public breaking removals are intentional current-contract cleanup, not a
request to retain compatibility shims for unknown external Python consumers.
Preserve readers and safety guards only where current supported code still
uses them. No new archive, bulk backup, history replay engine or migration is
needed.

## G1 design: leaf ownership with contract parity

Current `generation/work_units.py` owns response DTOs (:156–242),
repair-fact contracts/unions (:243–1052), prompt provenance (:1196–1459),
compilation, binding, semantic validation and repair derivation. Correction
schema/postconditions import its models. Correction directives explicitly
avoid that cycle using concrete class-name checks. Complete Storyboard response
DTOs also live in `storyboard_presence_repair.py:70–123`.

Extract by these responsibilities; names below describe owners, not mandatory
file names or a requirement to create one file for every type:

| Owner | Contents and boundary |
|---|---|
| Response contracts | Scene Beats scene/beat/dialogue DTOs; Storyboard shot/audio/supporting-link DTOs. Preserve existing class names, fields, aliases, defaults, intrinsic validators and discriminators. Separate scene/storyboard families if cohesive; do not put both into a new monolith. |
| Repair-fact family contracts | Dialogue capacity/node budget/cue order; graph edge/join authority; continuity endpoint/assignment/sequence/entity authority; Storyboard audio/entity authority. Keep each model's intrinsic validation and its necessary pure helper together. Existing edge-entry, timing-repair and presence-fact owners need not be split merely because they are short. |
| Repair union/codec | The actual `SemanticRepairFact` discriminated union and its TypeAdapter. The small parse/serialization helpers may move with that union where this establishes a direct reusable leaf; preserve authorized JSON nulls and exact nested round trips. Do not move derivation, issue/source matching or orchestration here. |
| Work-unit prompt/request contract | `WorkUnitPromptContract`, `CompiledWorkUnitRequest`, their intrinsic validation and contract/version constants needed without a return import. Keep generation planning/dialogue/timing *contract* dependencies explicit; do not move their algorithms. Reuse an existing suitable base/error owner or place it with its actual contract, rather than create a generic utility package. |

The compiler imports these owners; schema, postconditions, directives, runner,
qualification code and test consumers import the owners they actually use.
Keep compiler APIs/adapters in `work_units.py`; remove incidental reexports of
moved contracts instead of preserving it as a compatibility barrel. Update the
generation package's explicit exports as needed; supported current exports do
not require a forwarding layer for retired internals.

Replace fact admission based on `type(fact).__name__` with actual leaf-type
authority and fail closed on unsupported/forged same-name values. Choose exact
type membership or equivalent checked parsing to preserve the current closed
model set; do not accidentally admit arbitrary subclasses or duck-typed values.
**Keep model-name strings used in serialized audit/evidence projections**
(`correction_directives.py:634/:673`): those are existing data, not the cycle
workaround. Preserve registry ordering, versions, directive text, hashes,
prompt-local issue indexes, null assignments and deferred authority.

Compilation, binders, deterministic IDs/durations, schema overlays, directive
registry decomposition, repair derivation/source assertions, canonical seal
logic and durable runner composition stay in place. If intrinsic model
validation needs a helper, move that helper with its contract rather than
introduce a leaf→compiler back import. G1 does not authorize changing author,
model or trusted-code field ownership.

Public schema/serialized contract hashes and prompt versions should remain
unchanged for supported inputs. A demonstrated unavoidable change is a
contract finding to resolve deliberately, not permission to bump versions or
rewrite frozen evidence to make tests pass.

After G1, `work_units.py` will still exceed 500 lines: compilation, binding,
stage validation and repair derivation remain known G2 responsibilities. This
is an explicit staged scope boundary, not a claim that the remainder is one
cohesive module or a promise to fix it when next edited. The implementation
handoff must state its resulting size, what moved and the still-pending G2
boundary; do not add a new responsibility to it.

Apply the owner's size rules to new owners too: target roughly 400 handwritten
lines, architecturally review any owner reaching 500, and justify a remaining
oversized cohesive owner. Do not create another large model bucket or split
one contract merely to meet a number.

## Retirement boundaries

### R1 — Scope-less stage repair and the legacy engine

Keep `PipelineEngine` and its live durable/exact-repair dispatch. Remove only
the scope-less legacy branch (`pipeline.py:374–392`), legacy executor/helpers
(:434 onward), its private trace observer (:230–307) and orphan imports.
The live `RunSecretBroker`/provider resolver (:70–227) remain available to their
current consumers; extracting those is G5 unless a smaller dependency move is
strictly necessary for this removal.

Remove `generation/orchestration.py` and its unused exported
`GenerationOrchestrator`, in-memory quarantine store and observer interfaces,
their direct tests, and the `repair_json.yaml` template and retired prompt
inventory entries after the final scoped caller check.

Generic new-run admission must reject scope-less `RunKind.REPAIR` before row
creation, planning, reservation or dispatch. Remove obsolete creation-only
parameters where callers no longer need them, or reject them explicitly at the
current boundary; exact children are created through
`generation_repairs.py` with their immutable scope/lineage. An exact child
with a missing, mismatched or corrupt scope must fail closed, never fall back.

The current project-folder API already exposes exact work-unit repair rather
than a stage-repair route; do not invent or remove an endpoint that is absent.
Retire the retained Python admission/execution promise. Preserve:
- Exact repair eligibility, parent/source/sibling bindings, idempotency,
  cancellation, response reuse, ordered seals and atomic installation.
- Existing `GenerationRun`/RepairSource trace decoding where still consumed.
- Interrupted-legacy terminal classification in `generation_recovery.py:197–211`,
  schema-version refusal and every current UNKNOWN/no-replay rule.
- Current snapshot/restore; no live row rewrite or schema reset.

### R2 — Generic raw-media execution

Remove `src/plotloom/media.py`, its obsolete adapter/compiler tests in
`tests/test_media.py`, `MediaTaskRequest` and its reexport, and the unused
MediaScheduler/MediaPromptCompiler declarations duplicated in API models and
protocols. Remove `media_image.yaml`/`media_video.yaml` and their obsolete
render/inventory/package expectations: current source has no other execution
consumer. Update dummy extraction-path fixtures to a current template rather
than keep a deleted path artificially alive.

Do not expand into the audit's full B2 protocol cleanup. Retain the three live
run/text protocols in their current owner unless a direct import adjustment is
required to remove the two dead media protocols.

Preserve managed images, image package/delivery/selection, H3 requests, selected
media, project media persistence/codecs/recovery and the existing empty media-task
read response if still part of the current public read contract. A name containing
`media` is not evidence of obsolescence. Current prompt files and their hashes
are unchanged; wheel inventories exclude only the three retired templates
(`repair_json` plus the two raw-media prompts).

The corresponding inventories include `tests/generation/test_prompts.py`,
`tests/test_extraction_contract.py` and `scripts/smoke_installed_wheel.py`;
update all three rather than let the isolated installed check expect deleted
templates.

### R3 — Atlas/Wan execution fallback

Remove `atlas_wan_transport.py`, `WanCapabilities`/its unused instance,
`AtlasWanAdapter` and `video_jobs.py`'s default Atlas construction.
Make the adapter explicit and required; current production composition already
supplies H3. Keep neutral provider ports, production/output contracts and
exceptions that current H3 uses.

Retire the nine Atlas-only transport test functions (33 statically expanded
cases) at `tests/backend_core/test_atlas_wan_transport.py:19–226`.
**First relocate its four diagnostic-allowlist cases** (:229–240) to a neutral
dispatch-diagnostic owner. Keep `WanDispatchDiagnostic`/`WanDispatchError`
despite the historical names: H3 transport and job error handling consume them.
Do not broaden into a rename of every Wan-labelled type.

Preserve frozen Wan request integrity/readback at
`persistence/project/media_video_integrity.py:75–115`, current conservative
dispatch accounting, reservations and UNKNOWN recovery. No ledger release,
data deletion or conversion belongs here. Remove the obsolete
`PLOTLOOM_ENABLE_WAN_P2=false` manual example; even a nonempty string
`false` is rejected today. Keep startup rejection of the retired toggle.

## Decisions and documentation

After implementation approval, use the current ADR/index convention for one
concise decision covering leaf ownership and the three retired execution
contracts. Explicitly supersede only the callable legacy execution promise in
ADR 0015, generic raw-media execution as clarified by ADRs 0012/0031/0048, and
Atlas execution/test-retention in ADR 0034. State what current readers and safety
contracts remain and their functional use. Link rather than duplicate this plan
or rewrite historical decisions as if they had never existed.

Update current development/operations references and prompt/package inventories
that describe removed execution. Historical architecture readers/research
chapters stay historical; this is not a redesign of their frozen source maps.
Update audit/roadmap status per completed G1/R1–R3; leave unrelated batches
pending. Use one concise execution receipt in this plan or the existing
verification convention, not raw output archives.

## Ordered delivery and verification

1. **Preflight and establish parity evidence.** Confirm source/status and
   current callers, test module allocation, relevant package assets and
   affected profile/source hashing. Reuse locked dependencies and the known
   local execution envelope. Confirm the actual interpreter/import root is R
   for source checks; the later installed-wheel smoke must run outside R
   without source-path leakage. Before edits, capture only small temporary
   baseline schema/serialization/hash results for representative response
   models, every repair fact family/union and prompt contracts. Retain no
   duplicate model implementation or permanent old-source copy.
2. **G1 vertical slice first.** Move response contracts plus the minimum leaf
   dependencies; update consumers. Use a current disposable project outside
   installed/live roots, the existing `project_storage_fixtures.py` V3
   fixture profile/provider, `ProjectRunDispatcher`/`LifecycleJobRunner`
   or `ProjectPipelineExecutor`, real validators/storage and ordinary
   install/readback. Use the smallest valid split graph (one choice, two
   endings), one scene/beat and one shot per footage node, no dialogue/audio.
   Complete the relevant stage chain, reopen and compare persisted canonical
   results and prompt/schema provenance. Then finish repair/prompt leaves and
   verify a quarantined unit → exact child → reuse/seal/install with existing
   current repair fixtures. Keep this small outcome ahead of broad testing.
3. **Focused G1 checks.** Run response/fragment, directives/schema/postconditions,
   continuity/join/cue/timing/entity, planning/aggregation, prompts and affected
   runtime tests. Compare final schema/hash/null serialization with the
   pre-edit baseline. Verify cold imports in relevant orders and dependency
   direction: leaves, schema and postconditions do not depend on the compiler;
   directives admit actual fact types but preserve evidence labels. Add
   meaningful boundary/forged-type/null regressions using existing fixtures,
   not line-count tests or a mirror of each implementation.
4. **R1, R2, R3 serial checkpoints.** Each removes its exact obsolete source,
   exports/tests/assets/references and adds refusal coverage where current
   behavior otherwise lacks protection. R1 proves no scope-less row/provider
   allocation and retained exact-child recovery. R2 proves current image/H3
   contracts and surviving prompt/package inventory. R3 proves required
   adapter composition, preserved H3 diagnostics and frozen integrity/no-replay.
   Update `scripts/testing/module-ownership.json` with moved/deleted tests.
   Account explicitly for tests retired with contracts; preserve the native
   union and assertions for all **surviving** behavior, not obsolete case totals.
5. **Stable independent review.** One source/qualification owner hands off a
   stable candidate. Independent read-only review checks actual imports,
   contract parity, failure/admission ordering, source/profile identity,
   preservation limits and whether removals leave orphan shims. Fix concrete
   in-scope findings and rerun changed/affected selections; do not turn review
   findings into unrelated modularization.
6. **Final local qualification.** Use focused/reviewed module selections during
   development; run `uv run --locked --no-sync python scripts/verify.py full`
   once on the stable integrated candidate under one execution owner.
   Reuse matching wheel/installed-smoke artifacts and unchanged evidence.
   Diagnose failures narrowly and rerun affected/downstream gates under AGENTS;
   repeat full only for material invalidation, never weaken tests. No hosted
   CI or push. No frontend source changes are planned; any generated assets
   produced by required tooling must still meet deterministic parity.
7. **Activate and finish.** Preserve a coherent scoped local main checkpoint,
   validate the changed source/profile readiness and exact installed-package
   identity, perform quiet activation
   and preservation/readback below, update the single recovery package and
   record actual results, remaining gaps and cleanup. Do not stop at a worker
   report or a unit-test pass.

### What the small proof does and does not establish

The affected runtime is dispatcher → PipelineEngine → DurableWorkUnitRunner
using a frozen HTTP text-provider contract. The deterministic fixture supplies
model responses at its provider boundary while exercising real project,
validation, execution and persistence owners. Report it as **provider-free
runtime integration**, not native Codex generation, paid-provider E2E or creative
acceptance. An unrelated native Art/host smoke does not prove the moved G1 DTOs.

This structural/parity and retired-code scope requires no new media or paid
text generation. Do not invent a provider-budget/creative-review gate to move
unchanged DTOs. Real installed service open/read and current package/profile
validation remain required. If implementation discovers a behavior/schema
change whose acceptance actually requires live generation, name the changed
claim and use already-granted applicable authority; a new provider/fallback or
material scope expansion needs explicit authority. Do not imply that fake
responses establish an unexecuted live-provider result.

## Activation, permissions and rollback proposed with plan approval

**Nothing in this section is executed during planning.** Approval to implement
this plan is intended to cover its source/tests/ADR changes, local main
checkpoint and qualification, exact disposable fixtures/cleanup, quiet backend
and affected owned-bridge reload, preservation checks, prospective profile
qualification and update of the existing recovery package. Carry that approval
through normal in-scope fixes and planned rollback without new milestone
approvals. Thread/model standing approvals do not independently grant rollout
or provider authority.

- Use R serially; inspect P for new owner work before touching it. Use existing
  `services/creator_workbench/manage.py` and deployment/launchd lifecycle.
  Revalidate the current supported commands rather than substitute private
  guard bypasses.
- Establish a quiet checkpoint for the affected installation/owned processes,
  validator work and admitted writes that can race activation. Unrelated
  gateway, voice or other independent work is not a global stop gate. Let
  healthy affected work settle; do not cancel, resend, clear UNKNOWN,
  release reservations or signal unrelated processes to manufacture quietness.
  A necessary wait for real active work is an operational condition, not a
  request for the owner to approve an already-covered restart again.
- Before activation compare current project/canonical/draft/media identity,
  application settings, reservations/attempts/revocations and protected
  configuration/credential fingerprints without printing secrets. Preserve
  the actual current inventory, not old eight-project/85-attempt totals.
  Derived hashes and existing functional rollback suffice; no live-data dump.
- Python leaf moves change `codex_exec_profile.py`'s full source-tree hash even
  if prompt/schema hashes stay stable. Construct and validate the prospective
  profile/source pin with the existing profile builder, declared CLI/version,
  validator/toolchain checks, ordinary readiness and exact-package smoke.
  This does not invoke the separate opt-in serial/parallel finite qualification
  pair, enroll a new QA scope or claim new provider capability. Keep old
  profile/attempt evidence immutable.
  Never repin queued/in-flight jobs or bypass a source mismatch. No test
  acceptance receipt or live QA grant may be fabricated.
- Install the exact locally qualified source/package through the existing
  supported lifecycle; backend container recreation loads changed imports.
  Inspect affected owned bridge imports/lifecycle too: `manage.py start`
  can reuse a matching launchd process, so recreate/restart it if needed to
  load the new source, then verify actual runtime identity.
- Verify startup/health, current project directory/open/read and an already
  ready player's read-only availability where applicable, without approval,
  editing or generation. Run the current-profile/package smoke in isolated
  disposable roots, not by mutating a real project. Compare preservation
  baselines again, including safety guards and prospective/current identity.
- If qualification, startup, identity or preservation fails, diagnose the
  smallest cause. Keep an unqualified candidate out of P; after a failed
  activation restore the previous qualified code/package using the existing
  functional recovery path and recheck readiness/data identity. No data
  rollback is needed or authorized because this plan changes no schema/data.
  A genuine material risk expansion requires the owner; ordinary correction
  and planned rollback are covered.
- After successful activation replace the contents of the **existing single**
  `.local/current-qualified-recovery` with the newly qualified source/wheel/
  manifest through its current mechanism and verify recovery usability.
  Keep the old working recovery until the new candidate is proven; leave no
  second archive. Delete task-created disposable roots through their supported
  lifecycle only when quiescent; report any real unresolved hold honestly.

No provider/model/endpoint/credential setting changes, new generation grants,
migration/reset, live-project deletion, history-only preservation bundle,
GitHub workflow changes, CI or push is proposed.

## Acceptance checklist and handoff

- [ ] G1 response/fact/prompt contracts have cohesive direct owners and no
  compiler return dependency; supported schemas/hashes/nulls are unchanged.
- [ ] Class-name admission workaround is removed; evidence model-name labels
  remain stable; unsupported/forged types fail closed.
- [ ] Scope-less stage repair, raw-media execution and Atlas fallback and their
  exclusive tests/assets/exports are gone; current supported contracts pass.
- [ ] Exact repair, H3 diagnostics, frozen readback, snapshot/restore,
  transaction/lease ordering and UNKNOWN safety remain intact.
- [ ] Small provider-free project/repair proof, focused checks, stable review,
  final full-local qualification and exact installed-package checks have
  honest evidence. Provider and owner creative acceptance are not claimed.
- [ ] Quiet activation/profile identity, preservation checks and single
  functional recovery update are complete, or precisely reported incomplete.
- [ ] Scoped source checkpoint is on local main; actual code sizes and remaining
  named audit batches are stated; no unwanted source/QA artifacts remain.
- [ ] Delegated work is attended through actual final, manager review, access
  release and archival/Relay unregister. No duplicate qualification owner.

Implementer may choose cohesive file names, helper placement, focused selectors,
necessary intrinsic validation helpers and small causal fixes within these
boundaries. Do not require a new owner decision for each extraction or test
adjustment. Use Relay Direct for delegated implementation once approved, with
the existing model-choice guide applied at dispatch and one source writer;
parallel read-only review or independent checks are allowed.

## Planning review

Independent read-only review by GPT-6.1 Sol / Medium found no blocking technical
or execution-limits issue. Its two clarity suggestions are incorporated:
quietness covers only affected processes/writes, and source-hash changes use
current profile/readiness and package checks rather than automatically starting
an unrelated finite qualification campaign. No unnecessary milestone approval,
invented generation budget or arbitrary attempt cap was introduced. Effective
model settings were requested explicitly and remain unverified by the host.

Manager checked source boundaries, current prompt/package consumers, local link
targets, documented verification commands and the documentation-only diff.
The reviewer returned its actual final and released access; archival/reporting
cleanup is completed before handoff. Implementation, tests/builds, provider
work, live inspections and operational actions remain unstarted.
