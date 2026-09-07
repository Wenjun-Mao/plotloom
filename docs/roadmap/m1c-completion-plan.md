# M1-C completion plan

Planning baseline: `ea2d6e1` on `codex/m1b-alpha`, clean when inspected on
2026-09-07. This document records the next work; no new generation, tests, or
acceptance runs were performed to write it. Later tasks must verify their
actual HEAD and worktree before execution.

The next product outcome is a real, persisted storyboard from each saved local
text profile, visible after refreshing the existing workbench. The release
outcome remains the approved 18-run Alpha matrix, six independent content
reviews, and final verification/CI. The [capability matrix](capability-matrix.md)
is the product progress authority; this file owns the execution order.

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
| 2. Demonstrate real creation | One new project per saved profile completes all four stages and retains its storyboard after browser refresh | Both canaries show atomic installation, valid lineage, bounded attempts, and persistent UI content |
| 3. Freeze a verified candidate | One reviewed, clean source commit suitable for formal acceptance | Focused findings closed and all required local release checks pass on the final candidate |
| 4. Qualify the Alpha | The existing 18-run matrix and six blinded reviews pass | Receipts meet the unchanged acceptance rules and bind the source/content actually assessed |
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

Resolve the two intended saved profiles by ID. Verify each service's effective
per-request/per-slot context against its saved configuration before generation.
Read keys through the existing secret path; retain only public profile hashes
and safe diagnostics in shared evidence. HTTP/Tailscale remains supported.

Use one of the existing fixed Chinese Alpha stories, unchanged for both
profiles. Run each through the real application in an isolated development
data directory using existing configuration controls. Keep the resulting
projects for local inspection; the disposable conformance runner alone cannot
prove browser persistence. Exercise the existing workbench or application API
and browser, without adding a new application entry point.

Confirm four stages sealed, one atomic canonical installation, at most primary
plus two corrections per unit, no unknown submission outcome, and the selected
project/storyboard visible after refresh. Show at least one resulting storyboard
to the user. This is a canary, not the 18-run release receipt.

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

### 4. Qualify the Alpha

Use the existing [Alpha runner](../alpha-acceptance.md) and its fixed stories:
two saved profiles × three stories × three repetitions. Keep its source
checkout unchanged for the entire run. An exact committed worktree may be used
if the normal checkout must remain available for other work. Bind the running
module and receipts to that same source identity.

Launch the matrix as an unattended job using the existing task/job mechanism.
Handle completion or actionable failure, rather than repeatedly waking an
agent to read unchanged progress. Capture terminal receipts and lifecycle
state before any retry. Preserve the existing cleanup and secret boundaries;
do not log keys or invent a new general monitoring framework.

All 18 runs must complete and install atomically. Each profile needs at least
30/36 first-pass stages; no unit may exceed three attempts; unknown outcomes,
secret leaks, and partial installations disqualify the gate. Token counts and
latency remain observations, not provider disqualification criteria.

After the matrix qualifies, send only the six blinded canonical content files
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

- **Current:** step 1 complete (2026-09-07); ready to attempt step 2 under
  the existing contracts. No runtime ownership change is proposed or accepted.
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
- **Next outcome:** resolve the two saved profiles and verify effective service
  capacity, then attempt the two persisted application canaries in step 2.
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
