# ADR 0222: Qualification, exchange, storage and service ownership

Status: accepted and implemented. Software release `5971239f` activated and
preservation checked on 2026-10-27. The native `79668e1a` Alpha experiment completed
and FAILED independent content quality. These are separate outcomes.
Authority and evidence: [combined delivery](../roadmap/2026-10-26-b3-b7-backend-and-services-ownership.md).

## Ownership boundaries

The exchange, installation store, native process owner and Gateway mixed cohesive
capabilities with orchestration. Their capabilities now have explicit owners and
direct consumers, preserving wire, persistence, dispatch and settlement contracts.
No compatibility barrel, subclass back-import, generic context bag or second
execution pipeline is introduced.

`ApplicationRunRoutes` owns routing/frozen-profile tables and uses the application's
existing read/write contexts. Profile deletion checks share the caller's
`BEGIN IMMEDIATE` transaction with existence/revision, active selection, metadata
and deletion. Reservation precedes project creation; confirmation follows project
commit; only pending reservations can be discarded. Rebuild of both index tables
is atomic.

Reference appearance and proposal/decision/review declarations have actual schema
owners. Appearance registration retains its original position between managed
assets and visual intents. The captured 91-table metadata and SQLite DDL/indexes
remain exact; there is no migration, reset or schema-version change.
Plotloom's H3 catalogue owns profile/recipe/default/grid values independently of
Gateway. Adapter/profile contract 6 and catalogue 7 retain their meanings.

`image_exchange_files` owns descriptor/no-follow traversal, bounded regular-file
reads and inventory normalization. Manifest/attempt/pin assertions are pure.
The delivery reader owns descriptor lifetimes, raster/hash inspection and pending
versus final publication decisions. Direct callers use these owners; the unused
atomic-write helper is removed. Preserve package locks, own-prefix cleanup,
foreign-file refusal, fsync/rename ordering and frozen package bytes.

Creative identity/JSON, filesystem operations, trusted pin validation/current
checkout discovery and deterministic projection are separate leaves.
`CreativeHandoffPackageExchange` is a concrete capability composed by delivery
exchange, with no mixin-to-subclass helper dependency. Refresh consumes persisted
trusted pins; current skill drift cannot rewrite old authority. Native host and
specialist-chat outputs remain distinct contracts.

`CodexExecHostClient` owns executable/environment and bounded host interactions.
Registry retains settings, bindings, dispatch lock, persisted proof-before-release
and crash reconciliation. Preserve 20/30-second bounds, environment precedence,
private stderr, distinct preflight/ambiguous acknowledgement/invalid status/
unconfirmed abandonment errors and no retries. Manual deliveries may have no
native reservation; successor leases stay protected.

Terminal inspection and immutable output/receipt construction are collaborators.
Supervisor retains mutation, domain validation, durable store, completion marker,
recovery and the complete process guard plus SQLite write fence through namespace,
worker identity, cancellation/auth/capacity/qualification, `Popen` and committed
PID/group/birth identity. Inspection cannot release or publish. Require complete
owned-group exit, refuse signals to potentially reused groups, retain broken-pipe
UNKNOWN and text ImageGen contamination refusal. Image uncertainty stays held.

GC preview excludes only access time from its explicit metadata identity comparison;
device/inode/mode/link/owner/group/size and nanosecond modification/change times,
content hashes and unsafe-entry refusals remain authoritative.

`QwenImageCoordinator` owns creation/reservation and post-CAS execution with explicit
settings/store/files/client and a narrow completion collaborator. Gateway retains
the sole durable global FIFO, Comfy queue blocking and claim. Persist running before
blocking submission; lost acknowledgement remains UNKNOWN across reopen and blocks
later H3/voice. Preserve AUTOINCREMENT, one-active partial unique index,
`BEGIN IMMEDIATE`, queued-only cancellation, registration/grant binding, frozen
JSON/canvas/seed/start binding, managed PNG and transfer/completion semantics.
Voice Lab changes move shared fixtures into non-collected support only.

## Independent native qualification

The owner selected current native Codex and retirement of mandatory two-profile
Alpha execution. The current contract is `alpha_native_codex_three_story.v4`.
Optional saved-profile protocol conformance remains independent. Old 18-run/six-review
and four-stage receipts keep their original meaning and cannot qualify this contract.
This supersedes ADR 0024's four-stage arithmetic for current native Alpha, while
preserving independent qualification of each supported backend.

Pure shared metrics consume already-read traces and explicit stage order; they do
not own storage, execution or policy. `story_workloads` preserves the fixed Chinese
Brief bytes/hash. Alpha provenance, frozen campaign, eight-operation receipts,
blind publication, closed review/gates and CLI are cohesive direct owners.
The packaged CLI has no eager import of unpackaged services; native execution uses
the existing isolated workbench composition from a clean owning checkout.

Freeze three stories times three repeats and all nine identities before admission.
Require 9/9 current text installations, at least 60/72 primary operations accepted
first pass and three preselected repeat-one blinded reviews. The eight operations
are Outline, Branches, Characters, Art, Script, Storyboard, Bridge Intent and Bridge
Presentation. Corrective adoption is never first pass; all actual attempts count.
No invented token measurements or alias-based server weight identity is claimed.
Frozen producer model/effort remains `gpt-6.1-sol` / `medium`.

Each independent review requires no fatal contradiction, every score >=3/5, sample
mean >=3.5/5 and each of six dimension medians >=4/5. Publish canonical content under
opaque random identities; keep source/backend/story/repeat mapping private. Closed
receipts bind exact hashes, rubric and original evidence commit. Draft/secret,
confinement and no-overwrite checks remain. Software tests cannot establish quality.

The native text prefix takes the existing lease before normal app startup and uses
the existing repository claim, command authority and text controller. It stops at
verified current Bridge installation and prevents a competing image controller.
Normal source/image pin/capacity/login/toolchain/profile checks stay required.
It grants machine text/adoption authority only: no product Approval, material
handoff, image/video execution or enrollment under frozen comparison/QA grants.

## Correction and telemetry authority

Current capability `plotloom.text-correction.v4` preserves existing Outline,
Characters and Art semantics and adds at most one automatic Script and Storyboard
correction, defaulting to one. Honor explicit frozen zero, cap both at one even if a larger limit is
configured, and grant neither a manual extra. Branches and Bridge Intent/
Presentation acquire no new correction. Earlier versions never gain new authority.

Only a source-owned normal content issue result after exact frozen guards grants
correction. Parser, input/binding/authority, subprocess/runtime, receiving,
cancellation, nonzero model exit and UNKNOWN failures remain terminal/ineligible.
Bind immutable full parent bytes and exact candidate/request/package/plan/profile/
attempt lineage. The model authors the complete replacement; trusted code never
rewrites it, silently splits it or lowers effective content/timing/report gates.
Existing leases, deterministic child identity, CAS/currentness, publication,
adoption, exhaustion and snapshot guards remain.

Marked Art uses a generated frozen `plotloom.art-structural-result.v1` schema and
strict Pydantic validation of existing structural requirements. Exact schema/marker,
inputs, context and current style checks precede candidate-only ValidationError
classification. Preserve omitted/array props, extensions and tolerated elements;
explicit null refuses because application receiving already refuses it. Unmarked
upstream-only null tolerance stays unchanged. No coercion or model serialization
replaces candidate bytes. Semantic, receiving and render gates remain authoritative;
overflow and infrastructure/authority errors do not become content rejection.

Bridge Presentation producer guidance/schema distinguishes physical rendering from
nonphysical roles requiring an empty Literal. Frozen words/IDs/runtime choices stay
author-owned; the model owns faithful partitions, roles/rendering and reasons.
The strict binder/literal projection still rejects invalid rendering unchanged.
Schema guidance is not a constrained-decoding guarantee. Native delivery is
candidate-only followed by host validation/render; manual specialists validate/
render before completion. No Bridge correction or old-outcome promotion follows.

Prospective text inspection recognizes only the observed in-turn reconnect grammar
(retry 1–5 of 5 with the observed HTTP 429 phrase), retaining ordinal/hash/size and full
stream identity. It also recognizes exact paired `codex` empty-argument
`list_mcp_resources`/`list_mcp_resource_templates` observations with null error,
one matching empty JSON text block and null structured content. Require bounded
unique IDs, exact start/completion binding, one open turn and no dangling calls.
Generic errors, arbitrary/nonempty/mutating tools and malformed streams still refuse.
Normal exit 0, complete bound session and all package/domain/content gates remain.
Default/image inspection and direct/postmortem NoRemoteDispatch remain strict;
image refusal precedes any failure/completion settlement. No new tool permission,
retry, old-attempt adoption or release of uncertain capacity follows.

## Durable pause and retained provenance

Campaign storage is physical owner-only durable private state outside source and
resolved OS temporary roots. Missing original roots/databases never recreate an
incarnation. Immutable revision-specific pause snapshots are separate from terminal
outcomes; late completion records drain without changing snapshot bytes.
Resume binds exact sample/project/run/revision/snapshot, namespace/DB incarnations,
source/profile/policy and currentness; UNKNOWN, stale, rebound or terminal states
refuse. Fsynced intent precedes same-run CAS; immutable acknowledgement precedes
step/claim. Recovery accepts only original paused revision or its exact running
revision + 1, without repeating acknowledged CAS. Count elapsed slices/attempts once.
A pause does not establish process quiescence.

Passive retained Storyboard validation reconstructs known package-v4/plan-v1 from
original canonical request, pin, source, attempt, receipt and frozen plan hashes.
It never compares old authority to today's validator bytes. Its pure projection
checks outer/inherited contracts and derives fixed vectors/input hashes, reads no
old checkout/package and accepts no arbitrary recorded argv. Snapshot inventory
resolves inherited references to their exact origin run/profile/source and requires
attempt.runId equality. Only identical origin references coalesce; foreign or
conflicting owners refuse even when profile/source hashes match.
Current package building/resources/admission retain filesystem-current checks.
This passive boundary grants no dispatch, correction, approval or migration.
Native/image source inventories include the 97-line leaf; ADR 0184 construction
fingerprint remains `c8159d2b5d7f447bf8aa71ac5ccfb6ccd33c4e0bab47fa3dbaa7696fbe4701f9`.

## Evidence, release and disposition

Independent review closed the production repair at `a4d3818a` and test-only fixture
repair at `5971239f`. The latter separates preparation from listener acquisition,
retaining 45s overall/40s seed/25s listener, actual socket ownership, HTTP readiness
and cleanup. Every listener-wait snapshot validates the preparation marker without
resetting its absolute deadline. The original slow phase remains unproven.
Original full/browser failures remain recorded; reviewed composite coverage and
unrun downstream gates are attributed explicitly in the combined delivery record.

The actual `79668e1a` cohort installed 9/9 with 68/72 first-pass operations from 76
attempts. Three blind reviews FAILED narrative clarity and pacing/edit-cost medians
(3, required 4). The software release may be activated after its own safety/gates/
preservation close; this grants no Alpha success, waiver, regrading or owner creative
acceptance. Content optimization is a separate next decision; no fresh cohort is
authorized merely to obtain green results. Historical failed/UNKNOWN evidence and
held capacity keep their original meanings.

Core/bridge and Gateway retain distinct artifact, lock, environment and quiet-window
owners. Derive each runtime's actual profile from its own launch paths, checked
toolchain and persisted pool. Preserve project rows/files/incarnations/settings,
grants and uncertainty; rollback code/services without restoring old user data.
Recovery is one current source/wheel package, atomically exchanged only after exact
committed source/submodule/mode/hash and qualified wheel checks. It is not a user-data
backup or a qualified runtime environment. Lab fixture work needs no serving restart.
No provider/settings/model change, grant repair, push or GitHub CI follows.
