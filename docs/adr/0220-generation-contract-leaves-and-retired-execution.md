# ADR 0220: Generation contract leaves and retired execution

Status: G1 implemented, independently reviewed and locally qualified by composite
evidence and activated with preservation checks, 2026-10-25, under the owner-approved
[delivery plan](../roadmap/2026-10-25-generation-contracts-and-retirements.md).

Response DTOs, repair authority and frozen prompt records lived beside compiler,
binding and derivation algorithms. Correction consumers imported that compiler;
directives admitted facts by concrete class-name strings to avoid a cycle.

Scene Beats and Storyboard response owners now define their model-authored
fields. Dialogue, graph/join, continuity and Storyboard fact owners retain each
model's intrinsic validators and pure helpers. `repair_facts.py` owns the actual
discriminated union and lossless null-preserving codec; `work_unit_contracts.py`
owns prompt/request records and versions. Consumers import their actual owners.
G1 left rendering, binding, validation and repair derivation in the compiler.
Directives admit exact types in the closed union, refusing forged same-name
objects and subclasses. Registry/evidence model labels, versions, directive
text, schema hashes, ordering, null authority and field ownership are unchanged.

Three callable execution contracts are intentionally retired:

- Scope-less stage repair and its standalone orchestrator/observer/result DTOs
  are removed. Dispatcher entry and repository admission reject `RunKind.REPAIR` before
  project opening, route/profile reservation, snapshot, lease or row allocation. Exact children are created only through
  immutable-scope repair admission; absent/corrupt scope refuses execution
  before provider resolution. This supersedes only ADR [0015](0015-exact-work-unit-repair.md)'s
  retained callable legacy stage-repair promise.
- Generic raw-media adapters/compiler, request/protocol declarations and their
  two prompt templates are removed, together with the obsolete stage repair
  prompt. This supersedes the generic raw-media execution surface in ADRs
  [0012](0012-approved-storyboards-and-production-units.md),
  [0031](0031-bounded-wan-video-production.md) and
  [0048](0048-retire-shared-repository-runtime.md).
- Atlas/Wan transport, adapter/capabilities and automatic video adapter fallback
  are removed. `VideoJobService` requires an explicit adapter; current runtime
  composition supplies H3. A missing production contract also refuses before
  persistence/lease/reservation work; no new Wan snapshot is synthesized. This supersedes ADR [0034](0034-provider-neutral-video-adapters-and-local-h3.md)'s
  Atlas execution and test-retention promise.

Current durable `GenerationRun`/`RepairSource` trace decoding and interrupted
legacy terminal classification remain because project readback/recovery uses
them. Frozen Wan request integrity/readback and its ledger/reservation/UNKNOWN
safety remain because persisted jobs retain authority. Neutral provider ports,
production/output contracts and `WanDispatchDiagnostic`/`WanDispatchError`
remain consumed by H3; four diagnostic allowlist cases move intact to a neutral
owner. Managed images, selected media, project media persistence, the empty
media-task read response, snapshot/restore, leases, atomic installation and
schema-version refusal remain supported. No live rows or settings are rewritten.

The owner approved [G2](../roadmap/2026-10-25-g2-work-unit-ownership.md) with
“Go ahead with Relay direct” on 2026-10-25. Its completed implementation
separates canonical binding/IDs/duration allocation, frozen join requirements,
response schema/presence, ordered stage semantics, validation adapters and
repair-family derivation/source assertions. `semantic_repair.py` owns explicit
ordered dispatch; `compile_work_unit_request` remains the actual compilation
entry with direct owner imports. The graph adapter still delegates topology
algorithms to G3; the runner changes only its actual owner imports.
All 620 pre-edit schema/prompt/binding/issue/fact/codec observations match.

One required persisted-fact proof exposed a predecessor false positive:
continuity fact assignments' structural `key` field was rejected as a credential
field before validation evidence could persist. The manager included the narrow
causal correction: only closed-parsed canonical continuity assignments in a
rejected work-unit VALIDATION artifact with matching contract/stage/unit/issues
receive a nonmutating setting-name scan projection. Original whole content still
passes the credential-value scan first; secret fact names, nested values, raw
extras and all other locations/kinds retain their checks. Stored bytes, hashes,
aliases/nulls and generic response/redaction behavior remain unchanged. Actual
persisted JSON/codec/source checks and 23 adversarial/redaction cases pass.
This supported-contract restoration is separate from extraction parity.

G2 independent stable/security review and composite full-local qualification are
complete. A newly persisted continuity null fact survives supported snapshot/restore
with exact artifact/hash/codec/source validation. The original full failed only on
an undeclared task-evidence directory; its exact boundary rerun passed after moving
evidence to `.local`. The ordered browser follow-up retained a geometry-helper
failure, corrected by waiting for observable layout without changing its limits,
captures or zero-write assertions. All 4,020 Python/1,538 frontend/358 browser cases
are covered, and the exact retained wheel passes isolated installed smoke.
Both failed attempts remain failed; the plan owns complete timings and identities.
Manager-owned quiet backend/bridge activation, source/profile/readiness checks,
exact installed-state preservation and single recovery refresh are complete.
Eight projects and 26 selected playback ranges remain available. The plan owns
the operational receipt; the single recovery manifest owns final source/wheel
identity. G3–G5 and unrelated API/domain/frontend batches remain unselected. This decision
introduces no compatibility barrel or architecture framework. Source/profile
identity changes prospectively; frozen source pins and prior evidence remain
unchanged. No provider generation or creative acceptance is established by the
provider-free fixture integration, and hosted CI remains unrequested.

G1 local qualification is complete through one failed full attempt (only an
obsolete retired-test helper expectation), its assertion-preserving focused
correction and all ordered remaining full gates, including 358 browser cases
and exact installed-wheel smoke. The original full result remains failed;
see the plan's qualification receipt for revisions, timings and artifact hashes.
G1 activation and recovery refresh are complete in its delivery plan; G2's
corresponding operational closeout is recorded in the G2 plan.

The owner's request to plan and then implement G3–G5 together selects the
[combined ownership plan](../roadmap/2026-10-25-g3-g5-generation-ownership.md).
Planning contracts/context/topology precede correction authority/schema owners,
then durable exchange/evidence/compiler and explicit stage/unit composition.
Current schemas/versions/hashes, dispatch ordering, delivery-certainty categories,
response reuse, exact-child scope, UNKNOWN safety and layered release stay fixed.
Internal checkpoints are not renewed human gates; final integrated qualification
and quiet preservation-checked activation are included. Independent planning
reviews passed; implementation follows the planning checkpoint. No provider or
creative acceptance is inferred from the local real-adapter loopback journey.
