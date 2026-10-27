# ADR 0222: Qualification, exchange, storage and service ownership

Status: B3–B7 / Script correction / durable-pause source independently reviewed
through54726f69. Native qualification did not pass; prospective Bridge Presentation
producer hardening is selected after causal/method review. Gateway is activated;
core activation is held. 2026-10-27. Authority: [combined delivery](../roadmap/2026-10-26-b3-b7-backend-and-services-ownership.md).

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

The selected native implementation now replaces the former 1,111-line Alpha
owner with cohesive workload/provenance, frozen-campaign, eight-operation receipt,
blind-publication, closed review-contract/gate and CLI owners. Direct consumers
use those owners; there is no compatibility export barrel or legacy executable.
The packaged CLI has no eager dependency on unpackaged service files. Its native
run command requires the actual clean owning checkout and delegates composition
to `services/creator_workbench/alpha_native_runtime.py`, which directly uses
`isolated.RuntimeConfig/compose`. `AutopilotTextPrefix` takes the existing process
lease before ordinary app startup and calls the existing text controller with
its original repository claim/command authority. It durably pauses on current
installation before releasing ownership. Early and late image owners are never
called; persisted launch readiness, image pin/capacity and correction checks stay
in force.

Campaign preparation freezes all nine identities/Briefs before project admission,
actual source/tree/submodule/pins/profile/CLI/checked runtime and the observed
4/2/2/4 pool limits in its own disposable installation. It cannot reuse a frozen
comparison namespace. Public operation receipts count actual native reservations
and receipt-backed adoption, with the exact 60/72 gate and no invented token
measurements. Private bindings retain every job, attempt and installation proof.
Blind publication atomically exposes only the three preselected canonical exports
and public drafts at a neutral path; its owner-only unblinding map stays in
separate private state. Existing rubric thresholds, draft/secret rejection,
confinement and no-overwrite semantics remain. Current commands are documented in
`docs/alpha-acceptance.md`. Focused fixtures prove software contracts only; actual
native qualification and activation remain separate pending evidence.

The first real native admission exposed a CLI-directory prerequisite: the current
CLI refused the deliberately non-Git delivery directory before producing any
session event. The confined production command now supplies the supported
`--skip-git-repo-check` option. Independently validated source, private delivery
cwd, deny-root sandbox, frozen model/tools, file-store auth and ignored user config
remain authoritative; no Git repository or trusted-directory setting is fabricated.
The original attempt remains UNKNOWN with its original slot and evidence.

Review repairs make private terminal publication one atomic directory rename,
with exact-byte reuse and separate cancellation outcomes. An interrupted staging
write cannot wedge an installed paused project or acquire new dispatch. Preflight
requires the exact eleven supported case/stage/route union and recomputes every
plan from its retained production package/source revision. Blind mapping requires
unique complete preselected repeat-one identities with matching story prefixes;
qualification binds every content hash to the corresponding installed receipt
and retained canonical export. These checks introduce no retry or compatibility
path for the original failed matrix.

Two small real verticals exposed current CLI envelope incompatibilities. The
second completed its Characters CLI turn after a reconnect diagnostic, but the
strict reader treated that diagnostic as terminal and the host stopped UNKNOWN
before content validation. The trusted code owns event classification; model
content remains untrusted and subject to the existing validators. The author
owns the frozen Brief and no source-adoption or Approval rule changes.

Prospectively recognize only the qualified current reconnect diagnostic within
an already-started turn, retaining bounded hashes/sizes separately from fatal item
diagnostics and preserving the full raw transcript hash. Official documentation
lists distinct JSONL events without defining universal error fatality; the exact
retained stream supports this narrow exception, not blanket error acceptance.
Text success still requires exit zero, an exact complete bound session/turn and
all normal package/domain/content checks. Generic errors, item errors, malformed
or continued streams and existing bounds retain their refusals.

Image transport uncertainty must remain UNKNOWN before any failure/completion
path can release capacity or budget. No-remote-dispatch recovery explicitly
refuses transport diagnostics. This preserves the existing image/recovery policy
while repairing the observed text path. It authorizes no retry, old-attempt
promotion or model/prompt/sandbox change. Independent assessment requires immutable
real-stream replay plus strict negatives and consumer/hold regressions before a
new frozen source/profile/proof/matrix and another genuine canary. Both original
failed campaigns retain their actual identities, statuses, slots and evidence.

The implemented exception matches only the observed current in-turn reconnect
message grammar (retry 1–5 of 5 with the observed HTTP 429 status phrase). It does
not generalize error fatality. The immutable transport diagnostic stores ordinal,
message hash and byte size only. The existing domain inspection returns UNKNOWN
for image transport evidence before any failure/completion settlement; direct and
postmortem no-remote-dispatch proof refuse it explicitly. The event reader remains
cohesive at 376 lines, and the temporal process owner is unchanged. Immutable
original replay and controlled-child/hold tests establish this software repair;
neither ended campaign is promoted and no fresh model result is implied.

At `b5c9de51`, independent code and genuine canary evidence reviews closed. The
new frozen matrix installed one eight-job sample, then stopped on a known Script
duration rejection in the second sample (17.8s versus 17.85s minimum). Seven
samples remain unadmitted; 12 operations were accepted first pass from 13 actual
attempts. This does not satisfy 9/9 installation or qualify the backend. No
demonstrated source/validator defect was found. Current correction default 1 and
the Outline/Characters/Art allowlist remain unchanged. Adding a bounded Script
correction is a material prospective product-policy decision for the owner;
that decision is pending. Original matrices, failed/UNKNOWN evidence and holds
retain their meaning. The combined plan records software coverage and exact
terminal evidence; no blind publication/review, core activation or recovery refresh
followed this result.


The owner subsequently delegated judgment for the unattended long run. The manager
selected the independently reviewed one-automatic-Script-correction extension under
that authority; this is not personal creative acceptance. Extend the existing default
1 to Script while honoring explicit frozen launch limits including 0. No manual-extra
Script grant follows. Freeze a new correction capability and Alpha acceptance version;
original v1 campaigns/receipts, known rejection and UNKNOWN holds keep their meaning.

Trusted code alone may classify the pinned Script API's normal content issue return;
its wrapper binds exact candidate/input/request/package/plan/profile/attempt identities.
Parser, binding, interpreter/subprocess, cancellation, nonzero model exit and UNKNOWN
failures never become typed content rejection. Native planned-dialogue validation keeps
all existing receiving and report gates; receiving exceptions remain terminal.
A corrected job retains exact author source/Brief/routes/budget/style/model authority
and cannot relax effective estimator/tolerance parameters. Model-owned episode targets
and prose remain model-owned within those unchanged gates. The original failed attempt
and a distinct immutable corrective job remain in history; correction adoption cannot
count first pass. Exhaustion blocks; leases, CAS, currentness and snapshot guards stay.
Existing source-owned correction storage/controller/package owners implement the change;
no second pipeline or generic retry framework. Focused replay/controlled-child evidence
and independent source review precede new genuine correction/native-matrix admission.


The D2 qualification's OS-temporary campaign state disappeared after a user-directed
safe pause; cause unproven. Its six observed installations remain historical, with
lost trusted runtime evidence, and are not promoted into a replacement matrix.
Prospective native Alpha v3 requires physical owner-only durable storage outside
source and resolved OS temporary roots; absent original roots/databases never
recreate an incarnation. Existing model/workloads/validators/corrections and gates
are unchanged. This is recovery from missing disposable state, not rerolling a rejection.

User pauses have immutable revision-specific snapshots separate from terminal
outcomes. Late completion preserves snapshot bytes and records drain separately.
Qualification resume binds exact sample/project/run/revision/snapshot, original
namespace/database incarnations, source/profile/policy and currentness, refusing
UNKNOWN/stale/rebound/terminal states. Existing leases and text prefix remain the
only execution authority. Fsynced intent precedes same-run CAS, immutable ack
precedes every step/claim; interruption recovery accepts only the original paused
revision or exact matching running revision+1, without repeating acknowledged CAS.
Recorded elapsed slices and all actual attempts count once. A pause does not imply
worker quiescence. No successor-reader or multi-version compatibility framework.
Focused fault/reopen/identity/hold proofs and independent review precede a fresh
frozen nine-sample cohort; its real canary deliberately pauses/drains/resumes one
healthy sent attempt without duplicate dispatch, before scale and unchanged gates.

The reviewed implementation refuses selected-evidence/private-path and lexical
reserved-name aliases before compose or launch. A known failed sent attempt is
observed with its strict original identity, then the existing controller may
reconcile it only after durable resume acknowledgement: typed rejection uses the
unchanged capped correction, non-content failure blocks, and UNKNOWN still refuses.
The sample's terminal outcome remains immutable and cannot resume.


At54726f69 the durable real canary proved safe pause/drain/exact resume and all
eight jobs/current installation. The second cell stopped on a genuine Bridge
Presentation content rejection:139non-physical spans had forbidden rendering,
with normal CLIexit0 and unchanged strict binder refusal. The frozen failed cohort
remains oneinstalled/oneblocked/sevenunadmitted,14firstpass/17actualattempts.
Independent causal/method review found no demonstrated validator/runtime defect.

Under delegated judgment the manager selected prospective stage-owned producer
hardening. Author source words/IDs/runtime choices stay frozen; model ownership
remains span partitions/roles, faithful physical rendering and reasons. Encode
physical/non-physical response variants with required empty Literal rendering for
non-physical roles, strict fields/bounds, and explicit point-of-assignment/skill
contract-reading and role rule. The trusted binder/literal projection remain
unchanged: invalid rendering is rejected, never stripped or coerced. Manual
specialists validate/render before completion; native CLI remains candidate-only
and its host validates/renders before publication. This is authored-file schema
guidance, not a claim of constrained-decoding guarantees. No retry/correction
expansion, model/effort/limit/gate change or old-outcome promotion. Acceptance v3
policy is unchanged; new source/schema/package/skill/pins/profile bind the changed
producer method. Focused immutable replay/all-role/receiving/reopen proofs and
independent review precede a fresh exact envelope and genuinely fresh nine IDs.

The reviewed952 producer installed two samples, then its third Outline ended
UNKNOWN before content validation because the current CLI emitted two unsupported
empty catalog item pairs. The exact `codex` tools are `list_mcp_resources` and
`list_mcp_resource_templates`, arguments `{}`, null errors, and one completed text
block containing exactly the matching empty JSON catalog, with null structured
content. The stream/session completed and a separate exit0 wait result exists;
this is a decoder compatibility defect, not a model-content acceptance result.
The original952 canonical UNKNOWN, candidate, identities and held slot stay intact.

Under delegated judgment and independent causal/method review, recognize only
these source-owned observed shapes in prospective TEXT inspection. A pure catalog
state leaf owns bounded unique IDs, exact start/completion binding and immutable
ordinal/hash/size evidence; the shared reader retains turn/terminal/file/byte guards.
Default and image inspection plus direct/postmortem NoRemoteDispatch still refuse;
image refusal precedes all settlement. Normal exit0, exact complete session, package
confinement and unchanged content validate/render remain necessary for text success.
This adds no MCP tool/server permission, prompt/model change, retry or correction
grant. Author/model/trusted content ownership and qualification gates are unchanged.
Protected immutable replay and positive/negative/hold proofs precede independent
source review, fresh envelope proof and any genuinely fresh qualification cohort.
