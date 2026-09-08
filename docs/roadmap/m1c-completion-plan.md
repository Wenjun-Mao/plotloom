# M1-C completion plan

Planning baseline: `ea2d6e1` on `codex/m1b-alpha`, clean when inspected on
2026-09-07. This document records the next work; no new generation, tests, or
acceptance runs were performed to write it. Later tasks must verify their
actual HEAD and worktree before execution.

The next product outcome is a complete `default` llama storyboard that can be
inspected, edited, and reopened in the workbench. The first retained canary
quarantined at Story Graph; it is evidence to diagnose, not a successful result.
On 2026-09-07 the
user approved [ADR 0024](../adr/0024-pluggable-text-backends-and-independent-qualification.md):
pluggable backend availability and independent qualification. The vLLM
`qwen36_35b` lane is deferred and is not retried. Release now requires the core
gates plus independently qualified advertised backend configurations (at least
one), rather than two available hosts together. Each backend still needs nine
successful runs and three blinded reviews. The old 18-run/six-review gate keeps
its historical meaning; it has not passed. The [capability matrix](capability-matrix.md)
is the product progress authority; this file owns the execution order.

**Approved execution adjustment (2026-09-07):** close the two concrete
availability-review findings, integrate that small slice, then fix the observed
join-correction failure and attempt one real four-stage canary with content
inspection. Do not put adapter registry/V3 snapshots, runtime diagnostics, or
qualification-runner expansion ahead of that creation journey. ADR 0024's
architectural direction and per-backend quality thresholds remain accepted;
this amendment changes their delivery order, not the meaning of old evidence.

## Preserve the completed baseline

Project lifecycle, navigation/drafts, four-stage editing, exact work-unit repair,
structured authoring, and Gate/Approval are implemented. Keep them intact and
reuse their tests. Older passing counts and M1.5 receipts do not establish that
the current M1-C contract has passed real-model acceptance. Media production,
V1 runtime integration, and new deployment/authentication work remain outside
this checkpoint sequence.

## Checkpoints

| Step | Observable outcome | Acceptance and stopping point |
|---|---|---|
| 1. Close the ownership question | A bounded decision about the existing cue-order and timing failures | Reproduce/check the relevant cases at current HEAD; decide whether current fixes suffice or specify one exact contract change |
| 2. Demonstrate real creation | Finish the admitted `default` canary; a successful project retains its storyboard after browser refresh | Atomic installation, valid lineage, bounded attempts, persistent UI content; otherwise retain the concrete failure at the existing stopping boundary |
| 2B. Close the availability slice | Fix only the missing-profile admission bypass and availability-toggle draft loss; integrate | Targeted regression evidence, preserved historical hashes, no new scope |
| 2C. Fix the observed join correction | A source-bound correction cannot drop a still-required state assignment while fixing another value | Reproduce retained failure in focused tests, one shared contract fix, no guessed creative values |
| 2D. Demonstrate a usable storyboard | One real llama run completes all stages; storyboard is inspected, edited and reopened | Atomic installation, bounded lineage, readable coherent content, persistence; stop/reassess repeated failure |
| 2E. Complete necessary backend modularity | Adapter selection and independent qualification after the creation journey succeeds | Preserve old contracts; independent mode cannot masquerade as legacy Alpha; no unnecessary plugin infrastructure |
| 3. Freeze a verified candidate | One reviewed, clean source commit suitable for formal acceptance | Focused findings closed and all required local release checks pass on the final candidate |
| 4. Qualify the supported backend | Nine fixed-story runs and three blinded reviews pass for `default` on the frozen candidate | Same per-backend reliability/quality thresholds; distinct versioned evidence; vLLM deferred |
| 5. Deliver | Verified branch integration, push, final CI, and updated progress record | Remote state reconciled without force push, passing final CI, and a concise user-facing handoff |

### 1. Close the ownership question

Owner: one engineer/agent. Reuse current source, ADRs 0018/0019/0022, and
existing cue-order/timing regressions. Inspect retained failed-unit evidence
only if still available; do not assume temporary preflight artifacts survived.

Produce a compact field-ownership table for cue order, shot order/timing,
cue scheduling, and coverage. For each field state who chooses creative intent,
which values are uniquely derivable, and where validation belongs. Check the
primary prompt, response schema, binder, validator, and correction contract for
agreement. Do not expand this into an audit of all implemented product modules.

Use the relevant tests in `tests/generation/test_correction_schema.py`,
`tests/generation/test_correction_postconditions.py`, and
`tests/backend_core/test_pipeline.py`; select the cue-order and storyboard
timing-plan cases. Successful tests are regression evidence, not real-model
qualification.

There are two valid outcomes:

- Current fixes satisfy the ownership decision: record why and proceed to the
  real canary without another architectural rewrite.
- A deterministic round trip is unnecessary: specify one versioned ownership
  change, amend the controlling ADR, and implement that bounded change with
  focused regression checks. Preserve the original provider response and
  explicit derived result. Do not guess ambiguous ordering, branch meaning,
  coverage intent, or creative content; do not weaken canonical validation or
  mutate historical evidence.

The decision itself does not authorize an unplanned product redesign. If the
smallest sound fix exceeds the stated field scope, checkpoint the finding and
re-scope it before implementation. After this supporting work, step 2 is the
next outcome; no second general harness or audit checkpoint intervenes.

### 2. Demonstrate real creation

Resolve only the intended enabled profile by ID (`default` first). Verify its effective
per-request/per-slot context against its saved configuration before generation.
Read keys through the existing secret path; retain only public profile hashes
and safe diagnostics in shared evidence. HTTP/Tailscale remains supported.

Use one of the existing fixed Chinese Alpha stories, retaining that choice for
future backends. Run it through the real application in an isolated development
data directory using existing configuration controls. Keep the resulting
projects for local inspection; the disposable conformance runner alone cannot
prove browser persistence. Exercise the existing workbench or application API
and browser, without adding a new application entry point.

Confirm four stages sealed, one atomic canonical installation, at most primary
plus two corrections per unit, no unknown submission outcome, and the selected
project/storyboard visible after refresh. Show at least one resulting storyboard
to the user. This is a canary, not backend qualification or a legacy Alpha receipt.

On failure, preserve available local evidence safely and identify the failing
unit, stable issue, and responsible layer. Fix one shared failure class with
focused tests, then attempt this product outcome again. If the same class
persists after the targeted fix, stop the retry/review cycle with a concrete
diagnosis and next experiment. Investigate creative-task/model capability only
after checking contract feasibility and actual provider capacity. Do not add
model-name exceptions or blindly resubmit `outcome_unknown` work.

Capture available usage deltas at the end of steps 1 and 2 to calibrate response
count, context size, and estimated cost per accepted result. Do not promise a
percentage saving or silently enforce a made-up dollar budget.

### 2B. Finish and integrate availability only

Availability candidate `c654fff` and corrections `cad23c8` are now accepted and
integrated locally as `d28e2e7` and `be4bc6e`. The integrated runtime, frontend,
tests and scripts match the tested corrected candidate exactly. The review
identified and closed two bounded findings:

- The repository admitted a new V2 run with an unregistered profile snapshot.
  Require the managed profile at fresh admission; seed isolated qualification
  repositories normally instead of retaining a fail-open compatibility path.
- Availability toggles reloaded the profile form and could discard unsaved
  settings/session keys. Merge availability metadata only; retain the draft,
  base configuration revision and typing during the request or a 409 conflict.

Finish these corrections with focused backend and browser regressions, refreshed
static assets, then integrate. Keep disabled/missing-profile admission distinct
from draining already-admitted work. Do not add another general review; recheck
the specific findings and any directly affected behavior. No registry, new
snapshot schema, new qualification mode or live provider rerun belongs here.

### 2C. Fix one observed join-correction failure

Use the retained run `93e3edd2-74a9-424a-914b-a30498ec0085` and the terminal
canary record below. Read local evidence only as needed; do not publish prompt
or response bodies. The second correction fixed one join value while deleting
another still-required assignment. Identify the exact primary/schema/correction
agreement and source-preservation gap before editing.

Reproduce that failure with a small fixture, state field ownership, and implement
one provider-neutral contract fix with positive and tampering regressions. The
model retains creative state values; trusted code may preserve only facts whose
authority is established explicitly. Update the controlling ADR if that authority
or prompt contract changes, preserve raw evidence and historical contracts, and
never weaken the canonical validator or increase the correction limit.

Stop at focused regression-backed readiness for step 2D. Do not build a new
general repair framework, audit other domains, or claim model incapacity from
this one failure. A broader ownership change requires a concrete re-scope.

### 2D. One real creation journey before more infrastructure

Commit the focused fix and run the same unmodified Chinese story with `default`
through the normal application, with retained isolated data and fresh source
identity. Keep the original failed run unchanged; do not relabel its repair
lineage after a contract change. Recheck service readiness only as needed and
never contact the deferred vLLM host.

Success means four sealed stages, atomic installation, no unknown outcome,
at most three attempts per unit, and the storyboard visible after refresh.
Inspect the actual content for narrative clarity, branch causality, continuity,
performance readability, shot choices/pacing, and editing effort. Exercise one
ordinary edit/save/reopen without concealing the original generated content or
its review. Present the storyboard and specific observations to the user; a
schema pass alone is not creative acceptance. This is not the formal nine-run
qualification or product Approval.

If the same failure class persists after the targeted fix, stop with retained
evidence and reassess that contract instead of retrying or expanding correction
machinery. If another layer fails, record its exact issue and smallest useful
next action; do not silently start an unlimited sequence of fixes and reruns.

### 2E. Remaining backend modularity, after the creation journey

This scope is deliberately deferred until step 2D establishes a usable result.
One implementation owner follows ADR 0024. Implement only the remaining pieces
needed for explicit backend selection and independent qualification; no new
package/plugin system, story pipeline or duplicated enable/disable feature.

1. Add explicit protocol adapter ID/version resolution using the existing ports.
   Introduce a new snapshot schema for new runs; preserve exact V1/V2 decoding,
   JSON and hashes. Do not dispatch based on `textProvider` labels or aliases.
2. Reuse the accepted step 2B availability lifecycle without rewriting it.
3. Separate optional runtime diagnostics from protocol generation. Keep
   declared and observed capacity distinct; never use llama-specific endpoints
   as a universal health contract. Do not contact the deferred vLLM host.
4. Add a separately versioned single-backend qualification mode using the
   existing application runner and fixed stories. Freeze nine expected runs
   and three review identities; keep legacy two-profile mode exact. Bind
   source, execution configuration, adapter and known deployment identity
   without leaking private configuration in public receipts.

Primary seams: `provider_profiles.py`, `persistence.py`, profile/run routes in
`api.py`, `SnapshotTextProviderResolver` in `pipeline.py`, provider settings UI,
and `alpha_acceptance.py`/review pack publication. Reuse profile repository/API,
resolver, generation, and Alpha tests. Cover optimistic conflicts, disable vs
enqueue races, disable of the selected/last backend, drain/resume/cancel,
session-secret isolation, legacy hashes and exact old/new sample cardinality.

Demonstrate disabling an unused profile, continuing creation with an enabled
one, and re-enabling without deleting history. Keep `.env`, user-level
`AGENTS.md`, server processes, prompts, validators and media out of scope.
Do not hide generation-contract fixes in this module change. Review once at a
stable candidate, then step 3.

### 3. Freeze a verified candidate

Use one independent review of the stable diff and its specific high-risk
boundaries when code changed. Give the reviewer the candidate, owned contracts,
and targeted evidence. Address concrete findings; another review pass requires
a specific unresolved finding, regression, or material change.

Run the established complete checkpoint commands on the final candidate:

```sh
uv run pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
uv build --wheel
```

Also run the repository's wheel installation smoke using
`scripts/smoke_installed_wheel.py` and its established invocation. Include
regenerated `src/plotloom/static` files when needed. Verify a subsequent build
leaves `git diff --exit-code -- src/plotloom/static` clean against the candidate;
do not mistake an expected initial bundle update for an unrelated failure.
Record actual commands/results and package identity.

Commit the bounded changes and planning records locally. The acceptance source
checkout must be clean. Freeze one exact commit for step 4. Repeat affected
verification if the candidate changes; correctness takes precedence over a
literal run-count quota.

### 4. Qualify the supported backend

Use the new versioned single-backend mode described by ADR 0024, after step 2E
implements and verifies it; the existing [Alpha CLI](../alpha-acceptance.md)
still requires two profiles until then. Use the same fixed stories:
one selected backend × three stories × three repetitions. Keep its source
checkout unchanged for the entire run. An exact committed worktree may be used
if the normal checkout must remain available for other work. Bind the running
module and receipts to that same source identity.

Launch the matrix as an unattended job using the existing task/job mechanism.
Handle completion or actionable failure, rather than repeatedly waking an
agent to read unchanged progress. Capture terminal receipts and lifecycle
state before any retry. Preserve the existing cleanup and secret boundaries;
do not log keys or invent a new general monitoring framework.

All nine runs must complete and install atomically. The profile needs at least
30/36 first-pass stages; no unit may exceed three attempts; unknown outcomes,
secret leaks, and partial installations disqualify the gate. Token counts and
latency remain observations, not provider disqualification criteria.

After the matrix qualifies, send only the three blinded canonical content files
and their score-sheet templates to an independent reviewer; withhold the
private mapping and profile identities. Keep the existing rubric thresholds,
record `codex_external_review`, and do not create a product Approval on the
reviewer's behalf. Validate source/content provenance before publishing the
secret-free receipt. If code/contracts change, follow the existing provenance
rules for fresh qualification; do not relabel earlier evidence.

### 5. Deliver

Update the capability matrix with verified evidence, replacing stale checkpoint
counts only when fresh results support the change. Commit final receipts and
roadmap changes. Apply the previously approved release workflow: verify remote
history, integrate the accepted branch through a fast-forward where possible,
push once local acceptance passes, and obtain the final CI receipt. Never force
push; unexpected divergence requires reconciliation rather than overwriting.

Hand off the readable storyboard/workbench outcome, exact code/receipt commits,
tests and CI, remaining product scope, and the measured delivery cost when
available. Do not claim clean-machine recovery or later media milestones passed
unless those checks were actually performed.

## Active checkpoint record

Keep this block current at handoff; do not duplicate the product progress matrix.

**2026-09-07 approved amendment:** the `default` canary reached terminal
quarantine at Story Graph after three attempts; Story Bible sealed, no canonical
head was installed, and no outcome was unknown. Readiness passed at 32,768
tokens per slot. Quarantine/lineage survived browser refresh, but no successful
storyboard exists. The terminal evidence from execution commit `ee6239d` is
preserved below. Availability review findings are closed and integrated through
`be4bc6e`; the integrated code matches tested candidate `cad23c8`. Next execute
the shared join fix (2C) and one real creation/inspection journey (2D).
Remaining module expansion (2E) waits.
The service-readiness disposition below is historical evidence from before the
operator's llama restart. vLLM remains preserved and deferred. This amendment
records the approved order; availability is now implemented, while remaining
module expansion and all new release evidence are pending. The earlier four
unfinished correction-file edits were preserved and completed by a fresh bounded
owner after the old task drifted to an obsolete server question following context
compaction. Recovery verification: 15 focused profile tests, 41 affected backend
tests, 23 Alpha tests, 115 frontend tests, both typechecks, deterministic build,
and four profile browser journeys passed. No new provider call or full release
suite was run. Root worktree was clean at integration; usage/cost deltas remain
unavailable. The next assignment must start from this current record rather
than the old task's initial request.

### Step 2B: backend availability lifecycle

**Initial candidate (2026-09-07):** availability-only lifecycle at `c654fff`,
subsequently corrected by `cad23c8` as recorded below. A text provider profile has independently revisioned
`enabled` control-plane state. The migration defaults existing profiles to
enabled without changing their settings JSON, V1/V2 profile hashes, frozen run
snapshots, plans, or receipts. Settings can disable/re-enable even the selected
or last enabled profile; selection remains an unavailable preference and never
falls back to another profile.

New pipeline, rebuild, generic repair, and exact work-unit repair admissions
are guarded in the repository lifecycle write transaction against the frozen
profile's current availability. API prechecks provide prompt feedback but do not
replace that transaction guard. Existing queued/running/resumed work and its
already-admitted corrections remain governed by their frozen snapshot; cancel
remains distinct. Qualification source loaders reject disabled saved profiles,
while Alpha loading keeps pre-availability historical source databases readable
as enabled. Credentials remain server/session-only and availability responses
are secret-free.

Focused checks: `uv run --locked pytest -q
tests/backend_core/test_m15_profile_repository.py
tests/backend_core/test_m15_migration_compatibility.py` (9 passed);
`uv run --locked pytest -q tests/backend_core/test_api.py` (24 passed);
`uv run --locked pytest -q tests/test_alpha_acceptance.py
` (23 passed) and `uv run --locked pytest -q tests/test_conformance.py`
(13 passed);
`npm --prefix frontend test` (115 passed); `npm --prefix frontend run typecheck`;
`npm --prefix frontend run build`; and
`npx playwright test --config playwright.config.ts e2e/provider-profiles.spec.ts`
(3 passed). The browser journey used real FastAPI plus its isolated external
OpenAI-compatible fake provider: disabling the selected profile kept it visible,
showed unavailable state, blocked activation, and rejected a new API run. No
live provider, canary replay, full suite, or formal qualification ran.

**Remaining gap / next action:** this slice deliberately does not add the
adapter registry/V3 snapshot or single-backend qualification mode, and does not
change prompts, validators, or the separate join-key correction defect. Re-enable
still needs operator readiness evidence before a qualification attempt. vLLM
remains deferred. Agent response/cost deltas and fresh-versus-cached/reasoning
usage are unavailable; no instrumentation was added.

The remaining entries are historical checkpoint-1/readiness evidence; the
terminal canary record at the end supersedes their current/next-action entries:

- **Current:** step 1 accepted; step 2 blocked at service-capacity readiness
  (2026-09-07). Neither application canary was submitted. Existing ownership
  contracts remain unchanged; see the step 2 disposition below.
- **Verified baseline:** `70475ada584fa9fdaf671dd0f598fe4a233cf577`, detached
  worktree HEAD, clean before execution; parent `ea2d6e1` is the application
  baseline. This checkpoint changes this record only and is committed locally;
  no merge or push.
- **Outcome/scope:** cue ordering and Storyboard timing ownership checked across
  primary prompts, schemas, binding, validation, and correction. Stop at the
  focused regression result and decision below; no new harness or review cycle.
- **Checks:** `uv run --locked pytest -q
  tests/generation/test_correction_schema.py
  tests/generation/test_correction_postconditions.py
  tests/backend_core/test_pipeline.py
  -k 'cue or storyboard_timing_plan or storyboard_timing_fact'`:
  **17 passed, 59 deselected**, 2.48 seconds; one existing Starlette warning
  about deprecated TestClient/httpx integration. `uv` created `.venv` using the
  checked lockfile. No full suite, frontend checks, or live providers were run.
- **Next outcome:** restore service readiness described below, then resume the
  two persisted application canaries in step 2 without changing their profiles.
- **Known gaps:** Queue-provider regressions do not prove real-model compliance,
  creative quality, browser persistence, or Alpha qualification. No temporary
  failed-unit artifacts were needed or inspected; historical failure descriptions
  below come from ADR 0022, not a newly reproduced live failure. The 18-run matrix
  and six blind reviews remain outstanding.
- **Usage:** task response count, fresh/cached input tokens, total/reasoning output
  tokens, and cost deltas are unavailable in the exposed task usage records.
  No instrumentation was added and no savings or enforced spending cap is claimed.
- **Operating rules:** [ADR 0023](../adr/0023-bounded-delivery-and-evidence.md),
  surfaced through root `AGENTS.md`.

For a fresh execution task, pass this file, the verified baseline/worktree,
and one step's outcome/scope/acceptance. Do not fork the full historical
conversation. The task must discover only the code and evidence needed for
that checkpoint and stop at its stated boundary.

### Step 1 decision: retain the current ownership contract for the canary

**Decision (2026-09-07):** the current fixes are sufficient to attempt the
two-profile real canary without another rewrite. This is a regression-backed
readiness decision, not a prediction that either provider will succeed. ADRs
[0018](../adr/0018-trusted-story-timing-allocation.md),
[0019](../adr/0019-exact-fragment-and-join-state-contracts.md), and
[0022](../adr/0022-executable-correction-contracts.md) remain authoritative.

| Field | Author/model creative intent | Uniquely derivable values / current code policy | Validation authority |
|---|---|---|---|
| Cue order | Model chooses cue text, beat membership, and relative order; author can edit canonical content. | Given safe membership, repair sorts by declared order then source array position and renumbers independently per beat. The tie-break is an explicit policy, not inferred narrative intent. Canonical cue IDs derive from beat ID and accepted order. | Primary prompt explicitly restarts at 1 per beat; schema requires positive order. Fragment/canonical validation requires contiguous beat-local order. Source-rebound correction facts and exact membership/order postconditions prohibit deletion, rename, duplication, or reassignment; mutable membership issues defer the fact. |
| Shot order/timing | Model chooses shot sequence, pacing, action, and primary shot durations within the frozen scene cap; author owns the Brief target. | Binder derives shot identity, not order or duration. Frozen dialogue estimates and cue sums are arithmetic. Repair preserves shot identity/order but chooses minimum durations `max(1, scheduled cue sum)`; those minima are not uniquely correct creative pacing. Scene allocation already belongs to trusted code under ADR 0018. | Primary prompt states contiguous shot order, millisecond budget and cue/audio fit; schema binds feasible shot-count limits. Fragment and canonical timing checks remain mandatory. Exact correction postconditions run before semantic retry branching. |
| Cue scheduling | Model chooses which shot presents each sealed cue; dialogue identity/text belong to the upstream scene. | Ordering within a chosen shot follows canonical beat/cue order. The timing repair planner redistributes frozen cues round-robin over ordered shots, even if the previous membership was valid. This is a deterministic replacement policy, not a uniquely derived creative assignment. | Primary enum plus local checks require each cue exactly once, canonical order within each shot, fit, and owning-beat coverage. Plan facts must match both frozen guidance and a fresh reconstruction from rejected source; postconditions require the exact ordered lists. |
| Coverage | Model chooses each beat's PRIMARY shot and optional SUPPORTING relations/weights. | Binder materializes fixed link roles and PRIMARY weight 1 from model choices. Timing repair preserves existing maps and adds weight-1 SUPPORTING links required by relocated cues; code cannot infer visual meaning from those links. | Primary schema fixes beat keys; fragment/canonical checks enforce identity, one PRIMARY per beat, unique links, and shot/cue coverage. Unsafe source coverage gets no timing plan. Correction postconditions freeze full target maps. |

**Root cause and evidence.** ADR 0022 records beat-global cue numbering without
an executable repair assignment, and timing-plan coverage drift that could
escape into a generic descendant correction. The current shared correction
layer addresses those specific failures: source-derived facts, schema aids,
provider-independent postconditions, and terminal plan-mismatch handling.
The selected tests cover successful cue correction, membership tampering without
native schema, source/fact rebinding rejection, exact timing schema and output
shape (including cue order), successful timing correction through installation,
and coverage rewrite quarantine without another retry. They also reject foreign
or rehashed timing guidance. These are contract-layer failures, so neither a
more tolerant canonical validator nor a provider exception is justified.

**Agreement and limits.** The production fragment templates
`scene_beats_fragment.yaml` and `storyboard_fragment.yaml` agree with
`generation/work_units.py`'s response models, foreign-key/schema binding, fragment
binder, and semantic checks on these fields. Correction directives and
`correction_schema.py` provide the exact repair authority;
`correction_postconditions.py` and `work_unit_pipeline.py` enforce it before
retry branching. `validation.py` retains canonical acceptance authority.
Native JSON Schema is advisory: the cue overlay freezes cardinality, not exact
membership, and timing overlays cannot establish provider-independent compliance
on their own. Remaining audio legality is validated normally; replacement output
alone cannot prove that a source-indexed audio deletion was performed literally.

**Why retain the round trip now.** Cue renumbering is the narrowest candidate
for future trusted derivation, but moving it before binding changes the accepted
response contract and order-derived canonical identity. It requires an explicit
versioned ownership/evidence design, not a hidden normalization. Applying the
entire timing plan automatically would additionally move cue placement, pacing,
coverage additions, and audio removal across the creative boundary. Exact model
reproduction does not prove those choices are narratively good either; the
canary's content inspection must assess that. Passing structural checks must not
be described as creative acceptance. No evidence here requires that broader
ownership change before the direct product attempt.

Keep original provider responses, validation facts, and historical contracts
unchanged. If the canary exposes the same failure class, retain its failed unit
and reassess the precise contract under the plan's stopping rule. Do not respond
with another general harness, repeated broad review, or silent server repair.

### Step 2 disposition: blocked before application submission

Execution baseline: clean detached HEAD
`dcecf6626c523fd82c039632ac29b5ec79c3005e`. One owner; no delegates. The earlier
safe pause performed only read-only discovery; this authorized continuation
reused that work. The observable target remained one persisted four-stage
application storyboard per saved profile, with browser refresh verification.

Profiles were resolved from the existing SQLite configuration at
`/Users/wjmao/projects/HU/plotloom/data/plotloom.sqlite3` using SQLite read-only
mode. Both saved profile revisions are 3. Credentials were resolved in memory
through `PlotloomSettings.from_env` and `resolve_text_provider_api_key`, without
printing dotenv contents or keys. Public evidence below omits endpoints, model
response bodies, and credentials.

| Saved profile | Public profile hash | Declared context | Direct service evidence | Disposition |
|---|---|---|---|---|
| `default` | `8993119dfaee23337da34e222ec1b0c91826bbf040f3297dc28ad728d2020047` | 32,768 | `/props` HTTP 200: default `n_ctx=8192`, `total_slots=4`; `/slots` HTTP 200: all four slots `n_ctx=8192`, all idle | Blocked: effective per-request capacity is one quarter of the saved claim. Server credential was available. |
| `qwen36_35b` | `073239d25b61d5d91c53cfa21c7422e5b54d7086e35519dce83972ba1fa0fb5e` | 32,768 | Independent `/props` and `/slots` GETs both raised `ConnectTimeout` with a 12-second connect timeout | Blocked: service capacity and availability cannot be established. Saved authentication mode requires no credential. |

Checks used the configured service origin, honored saved authentication, and
disabled redirects. Only the selected numeric capacity/slot fields, HTTP status,
and exception class were printed; full service response bodies were not retained.
These were four read-only service metadata requests, not model generations.
The existing final-content probe was inspected but not invoked: neither profile
passed the prerequisite capacity check. Final-content readiness therefore remains
unverified, rather than failed. There was no submission with an unknown outcome.

No isolated data/artifact directory or project was created, because generation
was blocked before that phase. There are no project/run/unit IDs, attempt counts,
seals, installations, or browser artifacts to report. No application server or
browser was started; the metadata-check process exited normally and no request
remains in flight. No narrative/coverage/pacing assessment or persistence claim
is possible. Shared profiles, services, root checkout, and user-level settings
were not changed. Only this checkpoint documentation is committed locally;
no merge or push and no regression suite were run for this diagnostic stop.

The next action belongs at the service/deployment layer: the operator must
provide at least 32,768 effective tokens per request for `default` and restore
reachable metadata/capacity evidence for `qwen36_35b`. Then repeat the bounded
readiness checks, invoke the existing final-content probes, and resume the same
fixed-story application canaries. Do not silently lower saved profile capacity
or alter slot configuration during this checkpoint. The 18-run matrix and six
blind reviews remain separate, unperformed qualification work. Task response,
fresh/cached input, total/reasoning output, and cost deltas are unavailable;
no usage instrumentation was added.

#### Targeted service-access follow-up

At clean `0feea3b8a9e8f0bde49b8da8ec1a6488004ec9b4`, the user authorized
continued scoped readiness diagnosis and safe reversible service fixes.
Saved endpoints were resolved again in memory; they matched the two targets
the user identified. No general repository or peer survey was repeated.

- **`default`:** its exact Tailscale peer is online and answered a targeted
  ping. The configured model TCP port is reachable, while TCP 22 actively
  refuses connections. Batch-mode SSH with strict host-key checking also
  returned connection refused. Existing SSH configuration supplied no alternate
  matching host access. The previously observed 8,192-token slots therefore
  remain a service configuration blocker, not a network-routing failure.
- **`qwen36_35b`:** its exact Tailscale peer is offline (last seen
  `2026-09-06T19:49:40.1Z`). Two targeted Tailscale pings received no reply;
  both the configured model TCP port and TCP 22 timed out. The existing NVIDIA
  Sync `Spark` SSH alias matches this same host, but its local hostname could
  not resolve. Both target routes use the active Tailscale interface.
- **Service-specific correction:** `/props` and `/slots` establish llama-server
  capacity only. The second target is user-identified as vLLM; its earlier
  connection timeouts establish no vLLM capacity fact, and those paths must not
  be required after connectivity returns. Verify its context through applicable
  model/server metadata or recovered launch configuration instead.

No remote login succeeded. Consequently process ownership, other workloads,
and recoverable original service launch configuration cannot be established.
The prior idle llama slots are only a point-in-time observation and do not
authorize restarting an otherwise uninspected shared service. No restart,
profile edit, Tailscale/security change, or remote-access installation was
attempted. All access-check processes exited; there is no in-flight generation.

**Minimal operator actions:** on the llama-server host, recover the current
launch configuration and check workload ownership; arrange a non-disruptive
capacity change providing at least 32,768 tokens per slot (for four slots,
131,072 total context if this runtime divides its pool equally), then verify
the actual slot report. Alternatively provide existing authorized host access
so that inspection and the scoped change can be completed here. On the vLLM
host, restore the machine's existing network/Tailscale connection and running
service; no capacity change is justified until its actual vLLM configuration
is readable. This task cannot perform either host-local action through the
currently available access paths.

Both canaries remain unsubmitted, final-content readiness and browser
persistence unverified. No retained application directory or project exists.
Only this documentation changed; `git diff --check` passed. No full tests,
merge, push, or formal Alpha run occurred. Usage/cost deltas remain unavailable.

### Step 2 resumed default-only canary: terminal quarantine

This result supersedes the earlier readiness blocker and in-progress entry for
`default`. The user restarted llama-server and explicitly deferred `qwen36_35b`;
the deferred service was not contacted in this continuation. Baseline was clean
detached `481a20cc9f872a5d685f140cd1b9abd32da488f3`, which contains the earlier
checkpoint records plus the independently completed package report. Only scope
documentation changed while this source ran; no runtime code changed. The parent
task is separately recording newly authorized per-backend qualification policy;
this diagnostic does not qualify either the historical matrix or that new gate.

**Readiness passed.** The unchanged `default` revision-3 profile hash was
`8993119dfaee23337da34e222ec1b0c91826bbf040f3297dc28ad728d2020047`.
Both llama metadata endpoints returned HTTP 200; the service reported one idle
slot with `n_ctx=32768`, matching the saved profile. The existing application
profile probe returned final content, no reasoning, `finishReason=stop`, no
error, and 699 ms latency. Server credentials were resolved through the existing
environment/session broker path, never copied into the profile or project.

**One direct product attempt.** The unmodified `ALPHA_STORIES[0]` (`story-01`,
`v1`, Chinese “雾港回声”) was submitted via the normal application API and
`LifecycleJobRunner` in an isolated retained runtime. The saved public default
profile row was copied from a read-only source connection, preserving its
revision/hash. No canonical user projects were copied or changed.

- Project: `9213e6e7-150d-4777-9a26-22e066c4b37c`.
- Run: `93e3edd2-74a9-424a-914b-a30498ec0085`.
- Start/end: `2026-09-08T00:21:14.059238Z` /
  `2026-09-08T00:23:59.542801Z` (September 7 local time).
- Terminal state: **quarantined**, `semantic.join_state_effect_missing`.
- Story Bible: primary accepted and aggregate sealed. Story Graph unit
  `unit-story_graph-0001-be7970d333a242ad`: primary missing join assignments,
  first correction conflicting join values, second correction missing join
  assignments again. Maximum attempts per unit: **3**; four total responses.
- Scene Beats and Storyboard were never reached. Exactly one aggregate sealed;
  all four canonical heads remain `missing`, revision 0, with no result revision
  IDs. This verifies no partial installation, not a successful atomic install.
- All responses finished with `stop`; no unknown outcome and no replay. A scan
  of the retained API trace found no occurrence of the resolved server key.
  Prompt/response/validation evidence is in SQLite; the artifact directory had
  no separate files. This scoped key check is not a universal secret audit.

**Narrow diagnosis.** The primary declared two required join keys, one allowed
to vary, but omitted both on the two incoming edges. Correction 1 supplied both
keys, but gave the convergent key two different values. Correction 2 made that
key equal on both edges while deleting the already-valid varying key, leaving
the join's required-key declaration unchanged. The ordinary validator correctly
rejected it. The current correction schema projects only issue-selected keys;
the final correction's executable overlay therefore covered the convergent key,
while retention of the valid varying key depended on the preserve-content
instruction. There was no transport truncation or capacity failure.

The next bounded question is how a source-bound correction retains still-required
join-key presence while fixing another join value. That is an unaccepted contract
option, not an implemented fix or authority to choose branch values automatically.
Keep the raw response sequence intact. At the parent's terminal-boundary request,
no further provider run, repair, contract change, or broad review was attempted.

**Retained inspection evidence.** Data directory:
`/Users/wjmao/plotloom-canaries/2026-09-07-default`; database:
`plotloom.sqlite3`. The real workbench at local port 8875 opened the project from
its directory and retained its project URL, quarantined run, one sealed stage,
and three-attempt Story Graph lineage after a browser reload. Snapshot:
`.playwright-cli/page-2026-09-08T00-25-12-084Z.yml`; screenshot:
`.playwright-cli/page-2026-09-08T00-25-22-524Z.png`, relative to the retained data
directory. The initial root-URL 404 was resolved by using the existing `/v2/`
mount; an initial client-side response-shape mistake occurred before generation
submission and created no duplicate project/run. Neither required a product fix.
There is no successful storyboard to display or assess for pacing/coverage.
The local application and browser are retained for inspection; provider work is
terminal and the completion observer exited. Shared source/configuration remains
unchanged; no vLLM retry, merge, push, full suite, or formal qualification ran.

**Usage:** four pipeline responses recorded **18,774 input** and **6,801 output**
tokens (**25,575 total**); the readiness probe is not included. Cached versus fresh
input and reasoning versus total output are unavailable in normalized receipts.
Task-agent response/token deltas and cost are unavailable. `git diff --check`
passed for this documentation-only checkpoint.

### Step 2B recovery: profile admission and availability-draft corrections

**Outcome (2026-09-07):** the availability slice was corrected before handoff.
The repository transaction had treated a missing profile row as an isolated
historical/conformance exception, which also admitted a new V2 snapshot for an
unregistered profile. It now rejects every new managed V2 admission unless its
named profile row exists and is enabled. This is enforced in the lifecycle write
transaction for pipeline, rebuild, generic repair, and exact work-unit repair
children; it does not affect already-admitted queue/run/resume work.

V1 remains byte-for-byte on its original snapshot/hash path: a historical V1
snapshot without a control-plane row is still admitted without synthesizing V2
state. A V1 request that names an existing disabled row is nevertheless rejected
as a fresh request for that disabled backend. Disposable conformance and Alpha
repositories now seed the requested enabled profile explicitly, so they exercise
the production admission contract rather than carrying a broad repository
exception.

The availability UI no longer reloads the profile catalog after a toggle.
Instead it merges only returned `enabled` and `availabilityRevision` metadata
into the catalog and current draft. Unsaved endpoint/model configuration,
configuration revision/hash, `profileDirty`, and the profile-scoped tab-session
key remain intact, including edits made while the request is pending and after a
409 availability conflict. The regenerated workbench bundle is included.

Files: `src/plotloom/persistence.py`, `src/plotloom/conformance.py`,
`src/plotloom/alpha_acceptance.py`, `frontend/src/App.tsx`, regenerated
`src/plotloom/static/workbench.js`, focused repository regression, and
`frontend/e2e/provider-profiles.spec.ts`.

Checks: focused profile/provider tests **15 passed**; affected
conformance/migration/API tests **41 passed**; Alpha acceptance tests **23
passed**; frontend unit tests **115 passed**; frontend and E2E typechecks
passed; deterministic frontend build passed; the four real-FastAPI plus isolated
external OpenAI-compatible fake-provider profile browser journeys **4 passed**.
The new browser coverage holds a live availability response while typing a model
and key, verifies disable and re-enable leave the persisted configuration
revision/hash unchanged until explicit save, and induces a real 409 without
discarding the draft or leaking the key. No live provider call, canary replay,
full unrelated suite, or qualification run occurred.

**Remaining gap / next action:** this bounded correction does not add adapter
registry/V3 snapshots/qualification/runtime probes and does not address the
separate join-correction defect. After integration, the approved next priority
remains that shared join correction followed by one real llama canary and content
inspection. Commit and final worktree state are recorded with this recovery
handoff.

### Step 2C correction: source-bound join sibling preservation

**Outcome (2026-09-07):** the retained default canary's Story Graph failure is
addressed as one shared correction-contract change. Its first correction made a
required convergent key valid; the next correction deleted the other required,
allowed-to-vary key because the prior contract projected only issue-selected
keys. The ordinary validator correctly stopped that response at
`semantic.join_state_effect_missing`; the defect was preservation authority,
not a reason to choose branch values in trusted code or relax validation.

`JoinStateEffectRepairFact` now carries exact per-edge
`preservedStateEffects` for only the other required join keys that the rejected
response already validates: complete frozen incoming-edge membership, finite
canonical JSON (including null), and convergent equality where applicable.
Keys with a missing, conflict, non-finite, or required-key-promotion issue in
the same rejection remain unfrozen, including multiple simultaneous repairable
keys. The compiler re-derives every persisted join fact from the rejected
response, stable issues, and frozen topology before compiling a correction;
source rebinding, unknown IDs, membership tampering, and changed sibling values
fail closed. Schema projection and the provider-independent postcondition now
enforce preservation. This remains preservation-only: no response is patched
and no branch value is invented.

The changed identifiers are `WorkUnitPromptContract m1.12t`,
`bounded_correction.v22`, `correction_directives.v4`,
`correction_evidence_projection.v3`, and `correction_response_schema.v4`.
ADR 0022 records the ownership, cause, and historical-artifact boundary. The
implementation is confined to join repair facts, correction directive/schema/
postcondition compilation, correction source verification, focused regressions,
and the ADR; existing failed retained run data remains unchanged.

Checks: six focused generation contract suites **118 passed**; the focused
Story Graph correction and compiler-version pipeline regressions **2 passed**
(56 unrelated pipeline tests deselected), with `git diff --check` clean. The
regression recreates a convergent conflict beside different valid allowed-variant
values, then accepts a correction that changes only the convergent key. It also covers source
rebinding, JSON null round-trip, schema and postcondition mutations, unknown
edge rejection, and simultaneous repairable keys. No provider call, canary
replay, profile/configuration change, full unrelated suite, merge, or push ran.

**Remaining gap / next action:** this is focused-test readiness only. Root must
review the changed contract before one new real llama canary and content
inspection; the old failed run must not be relabelled or repaired in place. A
repeat of this failure class on that new run requires reassessment rather than
expanding correction scope.
