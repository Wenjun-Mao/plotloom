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

- **Current:** step 1 planned; execution has not started.
- **Verified code baseline:** `ea2d6e1`, `codex/m1b-alpha` (2026-09-07 inspection).
- **Next outcome:** decide current cue-order/timing ownership, then produce the
  two real persisted canaries.
- **Known gaps:** no fresh M1-C canary or qualification evidence from this planning
  turn; no six-sample independent Alpha review yet.
- **Checks in this turn:** planning-document consistency and local-link checks
  only; application behavior was not retested.
- **Usage:** historical audit is summarized in ADR 0023; checkpoint execution
  deltas will be recorded when work runs. Missing/delayed usage is disclosed.
- **Operating rules:** [ADR 0023](../adr/0023-bounded-delivery-and-evidence.md),
  surfaced through root `AGENTS.md`.

For a fresh execution task, pass this file, the verified baseline/worktree,
and one step's outcome/scope/acceptance. Do not fork the full historical
conversation. The task must discover only the code and evidence needed for
that checkpoint and stop at its stated boundary.
