# ADR 0220: Generation contract leaves and retired execution

Status: implemented, independently reviewed and locally qualified by composite
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
The compiler retains rendering, binding, validation and repair derivation.
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

G2 still owns the compiler's binder/stage-validation/repair-derivation split;
G3–G5 and unrelated API/domain/frontend batches remain unselected. This decision
introduces no compatibility barrel or architecture framework. Source/profile
identity changes prospectively; frozen source pins and prior evidence remain
unchanged. No provider generation or creative acceptance is established by the
provider-free fixture integration, and hosted CI remains unrequested.

Local qualification is complete through one failed full attempt (only an
obsolete retired-test helper expectation), its assertion-preserving focused
correction and all ordered remaining full gates, including 358 browser cases
and exact installed-wheel smoke. The original full result remains failed;
see the plan's qualification receipt for revisions, timings and artifact hashes.
Activation and recovery refresh remain separate manager-owned operations.
