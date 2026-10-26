# ADR 0222: Qualification, exchange, storage and service ownership

Status: independent B4–B7 and target-independent B3 leaves implemented and reviewed;
Gateway-only activation complete. Current native Codex selected for B3;
target-dependent implementation and combined qualification/core activation pending,
2026-10-26. Authority: [combined delivery](../roadmap/2026-10-26-b3-b7-backend-and-services-ownership.md).

The exchange, installation store, native process owner and Gateway each mixed
cohesive capabilities with orchestration. Move those capabilities to explicit
owners while preserving the current wire, persistence, dispatch and settlement
contracts. The owner subsequently selected current native Codex for B3; its
separately versioned qualification decision is recorded below.

`ApplicationRunRoutes` owns its two routing/frozen-profile tables and uses the
application's existing read/write contexts. Deletion checks consume the caller's
connection under the same `BEGIN IMMEDIATE` as profile existence/revision,
selection, metadata and profile deletion. Reservation still precedes project
creation; confirmation follows project commit; only pending reservations can be
discarded. Two-table rebuild remains atomic.

Reference appearance and proposal/decision/review declarations have actual schema
owners. The appearance import occurs at the original position between managed
assets and visual intents; the schema registry imports classes from their actual
owners. Exact 91-table metadata registration and SQLite DDL/indexes match the
captured pre-extraction source. No migration, reset or schema version change.
Plotloom's H3 catalogue owns profile/recipe/default/grid declarations; adapter 6,
profile contract 6 and catalogue v7 retain their meaning independently of Gateway.

Image descriptors/no-follow traversal, bounded regular-file reads and inventory
normalization belong to `image_exchange_files`, consumed directly by the package
commands, atomic publisher, delivery reader and terminal reader. Manifest/attempt/
pin assertions have a pure owner. The delivery reader retains all descriptor
lifetimes, raster/hash inspection and pending versus final publication decisions.
The unused atomic-write helper is removed. Publication locks, own-prefix cleanup,
foreign-file refusal, fsync/rename ordering and frozen package bytes are preserved.

Creative package identity/JSON, filesystem operations, trusted pin validation and
current-checkout discovery, and deterministic package projection are separate
leaves. `CreativeHandoffPackageExchange(root)` is a concrete capability; it
consumes the projection and filesystem leaves directly, with no subclass helper
dependency or `_projection` facade. The delivery exchange composes this capability.
Retained evidence and video directions consume the actual projection and filename
owners directly.
Refresh consumes only persisted trusted pins; current skill drift cannot rewrite
old delivery authority. Specialist-chat output and native host output remain
separate contracts. No new mixin, compatibility barrel or context bag is introduced.

`CodexExecHostClient` owns executable/environment and bounded host interactions,
with the original 20/30-second bounds and distinct preflight, unknown acknowledgement,
invalid status and unconfirmed abandonment errors. Registry retains settings,
bindings, dispatch lock, persisted proof-before-release and crash reconciliation.
Manual deliveries still need no native reservation; successor leases stay protected.

Native terminal inspection and immutable output/receipt assembly are collaborators.
The process owner retains mutation, domain validators, durable store, completion
publication, recovery and the complete process guard plus SQLite write fence
through cancellation/auth/capacity/qualification, `Popen` and process-identity commit.
Inspection cannot release or publish. Text ImageGen contamination, strict image
no-dispatch proof, broken-pipe UNKNOWN and complete process-group exit remain
required. Direct evidence-hash consumers use the evidence owner.

The service safety suite exposed a pre-existing GC preview false refusal: reading
private evidence updates access time across a whole-second boundary. The guard now
compares explicit device/inode/mode/link/owner/group/size and nanosecond modification/
change times, excluding only access time. Preview receipts keep their existing
shape; content hashes, ownership, hardlink and unsafe-entry refusals are unchanged.
Real access-time mutation succeeds while subsecond modification still refuses.

`QwenImageCoordinator` owns creation/reservation and execution after the Gateway's
CAS. Its explicit settings/store/files/client and narrow completion collaborator
have no lane or worker authority. Gateway retains the sole global durable FIFO,
Comfy queue blocking and claim. Running precedes blocking submission; lost
acknowledgement remains UNKNOWN across reopen and blocks later H3/voice work.
Frozen JSON/canvas/seed/start binding, managed PNG and transfer/completion semantics
are unchanged. Lab changes only move shared fixtures into non-collected support.

Explicit ImageGen and native validator inventories name the new capability files;
future pins and Python-tree identities change, while frozen old evidence does not.
Controlled CPU/API/SQLite/child-process/browser proofs establish software contracts,
not native model success, creative acceptance or material QA enrollment. No provider,
model, settings, grants, UNKNOWN clearing, live project edit, push or CI is authorized
by this ownership decision.


Target-independent B3 work shares only deterministic token accounting, sanitized
issue codes, whole-stage primary-attempt statistics and maximum attempts per work
unit. `acceptance_metrics` consumes already-read `RunTrace`/`RunExecutionTrace`
records and an explicit stage order; it has no storage, execution or qualification
policy authority. Each receipt owner still reads its own execution evidence and
retains its original fields, sorted issue-code projection, thresholds and lifecycle.
No Alpha/conformance workload or claim is merged by sharing measurements.

`story_workloads` owns the exact fixed Chinese Brief used by probes and fixtures;
its serialized bytes/canonical hash and conformance workload hash are unchanged.
Direct consumers import that owner. The four cross-collected Alpha review builders
and their two-helper dependency closure now live in non-collected test support,
with an unchanged collected Alpha case union. Runner retirement, versioned target
criteria and actual backend/model qualification remain held for the target answer.
The Alpha owner remains above 500 lines (1,111): its other provenance, publication,
review, receipt and execution responsibilities are separable but belong to the held
B3 follow-up. This bounded assignment removes duplicated measurements and adds no
responsibility; further extraction is deferred until target settlement under the
current handoff, rather than expanding the independent cut.

The owner resolved the target choice with current native Codex. Current Alpha
qualification becomes `alpha_native_codex_three_story.v1`: three fixed stories
times three repeats, all nine current text installations, at least 60 of the 72
eight-job operations accepted first pass, and three preselected blinded repeat-one
reviews under the existing quality rubric. This retains the earlier 5/6 first-pass
fraction while naming the actual native workflow. Preserve the current correction
default and allowlist; no validator weakening, extra retries or model change.

The runner consumes the existing native process lease, repository claim, command
authority and text controller, stopping at verified current Bridge installation.
An explicit internal ownership boundary prevents the ordinary background image
controller from competing. It introduces no second generation pipeline or public
text-only product mode. Real CLI/toolchain/login/validator/profile prerequisites
remain required. Qualification has machine text/adoption authority, not human
Approval or material-generation authority. Frozen comparison-pair grants cannot
be repurposed. Exact source/runtime/profile/attempt identities and secret-free
receipts remain distinct from content-only blinded review exports.

Retire mandatory two-profile Alpha execution and obsolete tests/invocations. Old
18-run/six-review and saved-profile four-stage results retain their original
meaning; they do not qualify this new version. Optional protocol conformance keeps
its separate workload, disclosure and gates. This supersedes ADR 0024's four-stage
Alpha arithmetic only for current native qualification; each supported backend
still qualifies independently. The combined plan owns actual implementation,
preflight, genuine canary/campaign, review and activation evidence.
