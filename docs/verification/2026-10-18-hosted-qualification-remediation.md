# Hosted qualification remediation, 2026-10-18

> Historical local artifacts in [the cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md) were retired
> on 2026-10-25. References to those files are not available attachments or resumption
> instructions; recorded outcomes, limits and current project-owned media stand.

Status: `2b3c8d66` was published after composed local release qualification and
manager review. Its unfiltered hosted run failed in browser shard 3 and Python;
wheel/smoke were skipped. The bounded test-only decomposition and explicit-QA
fixture correction passed focused checks; remaining hosted Python failures are
unresolved, so publication and another release-CI run remain held.
The final full attempt exposed one browser-test synchronization race; its
test-only correction passed focused and unfiltered downstream qualification.
Correction revision: `0af49b61fc64ed048a239cefbf22a584fb15a096` in
`/Users/wjmao/.codex/worktrees/b30f/plotloom`, based on
`99f2168495087dcc7e96b110e1a560edb0d99c4b`. No live activation,
provider dispatch or creative acceptance is claimed here. Publication and the
later hosted outcome are recorded separately below.
The 14 changed executable/test inputs are pinned in
`.local/batch-video/ci-remediation-inputs.json`, aggregate SHA-256
`7a5c8c30df7c1a892a20c0279169d9a139c90b4edc02aee3eb8663ba2a0c83af`.

## Failed hosted evidence and reproduction bounds

[Unfiltered run 39146800414](https://github.com/Wenjun-Mao/plotloom/actions/runs/39146800414)
failed at `00773e659fa95a311d8c6ec0c714182352bd9e06`. Browser shards 2/3/4
passed; shard 1's Storyboard static report overflow failed twice. The verify
job printed Python failures/errors before its 45-minute timeout, with no final
pytest failure report. Complete failed logs were recorded at
`.local/batch-video/hosted-ci-39146800414-failed.log`; hosted Playwright artifact
`12144236084` was the manager's read-only browser evidence lead. No gate budget
or required coverage was changed. Subsequent hosted dispatches are recorded
separately below; this failed run is not relabelled green.

The historical reproduction used a separate tracked-source/Git snapshot with
Ubuntu 24.04 arm64, Python 3.12.3, Node 22, procps 4.0.4 and the lockfile's
Chromium 151.0.7922.34. Hosted Ubuntu x64 used
Python 3.12.15: these are material environment differences, not a hosted pass.
No live data/configuration volume is attached. Later process checks use the
owned `--init` container `plotloom-ci-qualification-20261018` for orphan reaping.
Paid-entry diagnostics clear Docker-only `UV_PROJECT_ENVIRONMENT`/`UV_PYTHON`
before invoking the installed interpreter; real launcher refusal of ambient
overrides is preserved. An initial container umask of 0000 produced unsafe
fixture roots; subsequent runs use hosted-style 022. Neither condition caused
a production-policy change.

## Demonstrated root causes and repairs

### Explicit test-owned host resources

Immediate `-x -vv --tb=long` reproductions of the first profile case and
`test_actual_owner_reservation_freezes_before_original_admission` both failed
at the required Mac OpenSSL file check. Their source/runtime fixture owned the
synthetic Python receipt but not the platform config. The same omission was
then reproduced in the independent paid-source and pair-schema entrypoints.

ADR [0194](../adr/0194-provider-free-host-platform-resources.md) supplies one
private owned config per fixture owner. The shared host parent uses a
function-scoped substitution; actual helper children receive a test-owned
startup module. Separate paid/pair/fake-sandbox programs select their copied
source and bind that resource explicitly. The guarded launcher receives no
Python environment override. Its existing synthetic uv exec seam owns lookup
and temporary IO under the case root, rather than creating Mac system paths.
The fake sandbox still compares the full production command and runs real Node
validation/rendering. Production defaults, regular-file refusal, source/profile/
receipt/permission checks and copied production source remain intact.

Before logs: `linux-ci/profile-before.log`, `qualification-before.log`,
`paid-family-first.log`, `pair-before.log`. The intermediate paid wrapper error
is retained in `paid-native-io-after.log` and its test-owned validator stderr;
it led to tracing each interpreter boundary rather than weakening validation.

### Command width is not process identity

The expanded Linux family found a live helper with matching PID/group/start
but differing command hashes. Snapshot-only diagnostic probes showed the helper
recording its complete argv, while the reconnecting caller observed a command
cut at 78 characters. The same defect affected the test-process journal's
detached guard and caller. Both correctly refused equality and held work.

ADR [0195](../adr/0195-command-identity-display-width.md) requests unlimited
command width using `ps -ww` in both owning observers. No prefix comparison,
identity tolerance, ancestry exception or signal shortcut was added. Owned
long-argv cases compare narrow/wide environments. Original tokens remain
unchanged, and a previously truncated token can still refuse ownership.
Before logs: `linux-ci/helper-identity-trace.log`,
`codex-family-width-fixed.log`, `qualification-process-settlement-before.json`
and `paid-process-settlement-before.json`. Temporary diagnostic instrumentation
was removed from the source snapshot before qualification.

This is consistent capture, not a new incarnation/exit proof. The separate
[fail-closed investigation](2026-10-18-process-incarnation-proof-investigation.md)
and A99 activation blocker remain unchanged.

### Static report intrinsic sizing

The exact Linux browser case showed iframe client width 1195px and document
scroll width 1253px. The five `.kpis` tracks expanded to 1221px inside a 1131px
grid because `.kpi .d` descriptions had nowrap intrinsic minima; the last KPI
ended at x=1252.64. This was not a segment/card/gate overflow. Measurements are
retained in `linux-ci/browser-before.log`.

The static projection gives KPI items `min-width:0` and wraps their descriptions
with visible overflow and breakable long tokens. Renderer column breakpoints
remain intact. No hiding/clipping, archived-byte rewrite, script permission or
structured-review change was introduced. See [ADR 0126](../adr/0126-static-script-report-presentation.md#static-storyboard-summary-sizing-2026-10-18).
After measurements were client/scroll 1195/1195 with no overflowing descendants
(`linux-ci/browser-first-fix.log`). The existing archive/security/no-write case
also checks uncut KPI scroll areas. Summary screenshots at 1700x900, 1280x768
and 1280x460 were captured under the snapshot's `frontend/test-results/`.
All three desktop captures were inspected: all five descriptions remain visible.

## Executed verification and remaining qualification

- Linux initial profile suite: 20 passed after the config fixture repair.
  Exact qualification, child-config propagation and completed/UNKNOWN real
  helper cases: four passed. Logs: `linux-ci/python-first-fix.log`
  (20 passed before an unrelated umask artifact), `python-second-fix.log`.
- Linux reconnect and command-width regression: two passed in 3.54s;
  `linux-ci/process-width-after.log`.
- Linux expanded Codex selection: **341 passed** in 125.94s;
  `linux-ci/codex-family-current.log`, exact file selectors in
  `linux-ci/codex-family-selectors.txt`.
- Linux exact paid/pair entrypoints: two passed in 22.28s;
  `linux-ci/paid-pair-entrypoints-after.log`.
- Linux expanded paid/pair/process selection: **149 passed** in 194.15s;
  `linux-ci/paid-pair-families-current.log`. Exact files:
  `tests/test_paid_outline_handoff.py`, `tests/test_paid_outline_processes.py`,
  `tests/test_qualification_pair_contracts.py`,
  `tests/test_qualification_pair_measurements.py`,
  `tests/test_qualification_pair_observation.py`,
  `tests/test_qualification_pair_wiring.py`.
- Linux focused static presentation: **17 Python + one browser** passed,
  runner exit zero in 23.039s. Command:
  `uv run --locked --no-sync python scripts/verify.py focused --pytest tests/test_script_report_presentation.py --playwright e2e/storyboard-static-report.spec.ts`.
  Log: `linux-ci/static-report-focused.log`; browser includes its e2e typecheck.
- Mac initial profile/environment/static selection: 45 passed, exit zero in
  10.074s (`ci-remediation-mac-focused.log`). Later exact paid/pair entrypoints
  and full environment file: **12 passed**, exit zero in 32.191s
  (`ci-remediation-mac-entrypoints.log`).
- Mac focused Storyboard browser case: **one passed**, runner exit zero in
  17.408s (`ci-remediation-mac-browser.log`), including e2e typecheck. The native
  1280x768 summary screenshot was also inspected; the descriptions remain visible.

All log paths above are relative to `.local/batch-video/`. The independent
read-only reviewer returned no actionable correctness/safety findings in the
stable diff and ADRs. Requested settings were Sol/High; effective host settings
remain unverified. No tests or live operations were delegated to that reviewer.

The reviewed module union is `shared-provider-dispatch` plus
`creative-production`, depth `contract`: the former owns profiles, helper/host
identity and paid/pair fixtures; the latter owns static projection and its
readers. The printed plan contains 97 Python files and the declared frontend
contract/type checks, not every release gate. Plan:
`ci-remediation-module-selection.log`. Execution:
`uv run --locked --no-sync python scripts/verify.py module --module shared-provider-dispatch --module creative-production --depth contract`.
The runner passed **1,367 Python + 483 frontend cases in 56 files**, both frontend
type checks, and native ownership discovery; exit zero in **623.415s**.
Log: `ci-remediation-module-contract.log`. Native discovery collected all
3,275 Python / 1,415 frontend / 336 browser cases without running those whole
suites. Those counts are coverage validation, not full-suite passes.

The actual diff leaves frontend production sources, package/lock/build inputs
and `src/plotloom/static/` unchanged; its frontend edit is the browser regression
only. Existing deterministic frontend bundle evidence remains applicable to
those unchanged executable inputs. Static report styles are Python-served
derived HTML and were exercised through the real report route above.

The scoped evidence above does not identify every failure hidden by the
original quiet hosted timeout or qualify hosted x64. Final local qualification
and manager review are recorded below. New source hashing includes the
command-capture change, so older unchanged-product evidence alone must not be
presented as complete qualification of that new runtime input.
Neither a live helper stop/reset nor revocation/deletion/activation is authorized
by these corrections. A separate later owner approval conditionally permits the
manager to verify and gracefully stop only the exact idle CUA helper; it does not
change the incarnation proof or give this worker concurrent live authority.
This source worker performed no live operation or retained-fact mutation.

## Manager review and exact-revision retest

The manager reviewed the actual `0af49b61` diff and ADRs 0194/0195 with no
findings, then independently reran **50 Python + one real Chromium case**,
including e2e typecheck, exit zero in **62.672s**. Exact selectors and output:
`.local/batch-video/manager-ci-remediation-retest.log`. Fresh 1280x768 and
1280x460 report captures showed all five KPI descriptions. Intentional semantic
failures in that controlled report fixture are not product acceptance.

The manager and independent read-only reviewer could not bind the current CUA
helper PID 90191 to its owning chat or prove no pending automation. The owner's
conditional stop approval therefore remains unfulfilled. No shutdown, reset or
signal was performed; activation remains held. CPU, cwd, shared parent and an
executor UUID lookup were not treated as ownership/inactivity proof. This
assessment adds no new process-incarnation evidence or live-operation authority.

## Final local attempt and bounded browser-test repair

One unfiltered `uv run --locked --no-sync python scripts/verify.py full` ran on
clean `0af49b61`, log `.local/batch-video/ci-remediation-full-0af49b61.log`.
It **exited 1 in 1687.008s**: locked dependencies, media probes, API lint, archived
reader, **1,415 frontend cases in 162 files**, frontend type contracts,
**3,275 Python cases**, deterministic bundle/parity and unfiltered browser
coverage passed. Python workers passed 1,707 and 1,568 cases; native case-ID
SHA-256 was `83823784b115619d37edae935bde8449d6495c787faf2a90c5aa1f41a7555022`.
Browser execution had **335 passed / one failed** in 597.239s; wheel/smoke were
not reached. This invocation is retained as failed, not relabelled successful.

The sole failure was the graph-action explanation case in
`creator-workbench-operations.spec.ts`. Its nonretrying `innerText()` captured
the pending production-read status, then its exact accessible-description
assertion retried against the later settled status. The retained trace records
the successful production-bridge read at that boundary; the error report shows
24 subsequent reads of the settled text. `GraphWorkflowActions` renders both
visible status and accessible description from the identical span. The known
fixture is unconfirmed, so its settled creator text is explicitly
`先确认当前图内容，再应用到故事路线。`; the professional view supplies no status.

The correction awaits those exact fixture-owned states with `toHaveText()`
before asserting the full exact description. All accessibility, geometry,
no-write and no-dispatch assertions remain. No sleep, timeout increase,
substring relaxation or production change was introduced. Failure screenshot,
trace, video and context were copied before rerun into
`.local/batch-video/local-full-0af49b61-failure/`. The manager independently
reviewed the owning components and test-only diff with no findings.

Focused whole-spec verification passed **seven browser cases**, including e2e
typecheck, exit zero in **34.031s**; log
`.local/batch-video/ci-remediation-graph-actions-focused.log`. An initial selector
used `frontend/e2e/...` and was refused before test execution; its separate
`ci-remediation-graph-actions-selector-refusal.log` is not execution evidence.

Only that browser test changed after the full attempt. Passed Python, frontend,
type, bundle and parity inputs remain unchanged and are reused; all 14 original
correction inputs were rehashed and matched their pinned manifest. The changed
operations spec SHA-256 is
`7e8cfd04e3de7f18db21a9829a7e88ca2ed9a018ee3899dbb6a59a8a1ca86a7a`.
The exact unfiltered browser coverage/suite and unreached wheel/smoke commands
ran through the existing `_full_steps`/`_run_steps` definitions, log
`.local/batch-video/ci-remediation-full-downstream.log`: **336 browser cases**
passed in **590.676s**, wheel build and installed-wheel smoke passed, runner
exit zero in **597.344s**. E2e typecheck ran within browser execution. This is
positive composed local release qualification, not a fresh successful full
invocation or a new verification tier. No gate was waived or filtered.

Remote `main` was freshly fetched and remained at `5f7dbf43`; only the reviewed
test synchronization and this evidence record differ from `0af49b61`.
Publication follows the normal fast-forward check. Required unfiltered hosted CI
is still pending. No source activation or broader helper shutdown is implied.

## Published revision and hosted imported-still failure

After a fresh fetch showed no remote divergence and the checkout was clean,
`99f21684`, `0af49b61` and the test-only local-race correction/evidence commit
`2b3c8d6650122adf0b503c36fa42f48206bd740e` were normally pushed to `origin/main`.
Exactly one `gh workflow run ci.yml --ref main -f 'browser_grep=.*'` dispatched
[run 39166995435](https://github.com/Wenjun-Mao/plotloom/actions/runs/39166995435)
at that exact head. `gh run watch 39166995435 --interval 30 --compact --exit-status`
attends it without automation. Browser shards 1, 2 and 4 passed; shard 3 had
71 passed / one failed. The verify job later failed after 47m18s: its Python
step exceeded 45 minutes with 17 visible failure markers and only 63% progress;
wheel/smoke were skipped. Final metadata and full failed logs are
`hosted-ci-39166995435-final.json` / `hosted-ci-39166995435-failed.log`.
This run is completed FAILURE, not qualification.

The original and retry of `imported-still-preview.spec.ts` both exceeded the
unchanged 45-second body budget at different late assertions (lines 145/144).
The downloaded native artifact is `playwright-test-results-3`, ID `12151312415`.
The complete job log and ANSI-free copy are
`hosted-ci-39166995435-shard3-job.log` / `-job-plain.log`.

The traces support cumulative journey-budget exhaustion, not an approval
contract failure. Before Hooks ended at 253191.020 / 311617.878ms; After Hooks
began at 298152.660 / 356549.715ms, about 44.96 / 44.93 seconds later. Teardown
therefore starts before the late failing assertions. Original reapproval POST
returned 201 in 90.968ms and its review GET returned 200 in 87.041ms; the exact
approval-label assertion passed during teardown. The next assertion had only
1.266 seconds before context closure. The retry reaches teardown even earlier
relative to board save/reapproval, after which pending reads have no response.
Four real UI-import waits each consumed 2.38–3.42 seconds, navigation 2.61–2.66
seconds; there was no demonstrated pre-deadline 10-second assertion stall.
The timing extraction is `hosted-ci-39166995435-imported-still-trace-summary.json`.
The full original case and its shared setup helpers were unchanged by the prior
remediation. No deadline, retry policy, test coverage or CI budget was relaxed.

After the two failed hosted attempts, the method was reassessed with the manager
and a read-only static review before another execution. The manager approved
three cohesive, independent test bodies: the trace puts the replacement
checkpoint near 43 seconds, so simply moving reapproval would leave little
margin in the original body. Each new case owns a fresh project; native API
preconditions run inside the same 45-second body, not an extended fixture.

| Coverage obligation | New owner |
| --- | --- |
| Four real UI imports/provenance, explicit candidate comparison and first-shot intent, two independent typed target-use/identity reviews, three-shot preview/playback | Import/review/playback case; original UI actions/assertions retained |
| Four imported originals, approved/reviewed three-shot state, current source/reference/identity context and preview receipt | Native API setup in the restart case; real imports, draft CAS/consumption, approval, selections, references and reviews, with current-state assertions |
| Exact original bytes and assets/intents/bindings/preview receipt before/after actual backend process restart | Restart/replacement case; existing exact comparisons retained, reference and identity-review equality added |
| Explicit UI replacement makes old receipt stale and produces a new current receipt | Restart/replacement case; original UI replacement and staleness/renewal assertions retained |
| Authentic prior replacement/current preview, then authored board edit invalidates approval and all three reviewed frames; normal explicit reapproval | Reapproval/deletion case; fresh native API state includes old-source context, independent target reviews and the replacement, then original UI edits/refusal/reapproval assertions |
| Exact final selection ACK plus complete current read, followed by native archive/permanent-delete/404 | Reapproval/deletion case; original assertions retained, selected asset additionally checked against the seeded replacement |

Workflow-local `imported-still-preview-fixtures.ts` contains the existing
canonical-project/byte-capture helpers plus these native prerequisites. It is
registered to `media-lifecycle` in the support-ownership map. No DB mutation,
fabricated current flag, shared mutable project, API stub, sleep, hidden fixture
budget or production behavior was introduced. Native APIs still enforce source,
identity, revision and draft-consumption contracts.

Mac whole-file focused verification passed all **three cases** (12.3 / 10.0 /
7.0 seconds), e2e typecheck and runner exit zero in **37.774s**. Log:
`ci-remediation-imported-still-mac-focused.log`. An initial e2e typecheck caught
an accidentally omitted existing helper import during extraction; that import
was restored before execution (`ci-remediation-imported-still-types.log`).
Linux whole-file verification in the same isolated Ubuntu arm64 environment
passed all **three cases** (19.2 / 15.9 / 12.4 seconds), e2e typecheck and runner
exit zero in **61.993s**, with `CI=1` and no retries needed. Log:
`linux-ci/imported-still-split-focused.log`. These are not hosted x64 results.

Native ownership discovery passed **3,275 Python / 1,415 frontend / 338 browser
cases**, with test bodies unexecuted (`ci-remediation-imported-still-ownership.log`).
The browser manifest passed **95 specs, 338 cases, shards 89/74/74/101**, zero
overlap/omissions (`ci-remediation-imported-still-browser-coverage.log`). Focused
verification of `tests/test_verification_module_ownership.py` and
`tests/test_ci_browser_contract.py` passed **12 cases**, exit zero in **4.327s**
(`ci-remediation-imported-still-contracts.log`). The new helper has only the
three imported-still cases as direct consumers; shared helpers are unchanged.

Independent read-only review requested GPT-6.1 Sol / Medium; effective host
settings are unverified. It found no actionable issue in the actual diff,
native preconditions, coverage mapping or restart/reapproval invariants; it ran
no tests or live operations. Its explicit limit is that persistence/reapproval
now consume equivalent native-created prerequisites, while the original UI
creation remains covered by the first case; one continuous UI-created project
lifetime is no longer the test organization.

The only changes since published `2b3c8d66` are this test organization, its new
workflow-local helper, support-ownership registration and this record. Production
source, APIs, persistence/admission, provider/prompt behavior, dependencies,
timeouts, fixture runtime and build/package inputs are unchanged. Reuse the
passed local Python/frontend/types/bundle/package evidence and the 335 unchanged
browser cases; the three revised cases have fresh Mac/Linux evidence. This does
not claim a fresh unfiltered 338-case invocation or a new full pass. The original
hosted run finished naturally and its additional Python failure is recorded
below. No cancellation or replacement release run has occurred.

## Additional Python failure: confirmed fixture gap and unresolved remainder

The quiet hosted log has three `F` markers near 37% and fourteen near 63%,
then cancellation without final tracebacks. Exact current Mac and Linux native
collections both contain the same 3,275 cases in the same order. A provisional
marker map therefore points to three capsule cases and fourteen paid Outline
cases (`hosted-ci-39166995435-python-marker-map.json`), but the hosted inventory
was not retained: these remain inferred targets, not hosted traceback IDs.

Immediate Linux `-x -vv --tb=long` reproduction of the capsule file passed the
actual Node case, then failed `test_missing_or_stale_bundle_is_refused` in
2.74s. Its positive structural setup omitted `qa_bytes`, so `bound_sources`
followed the checked-in operator QA's Mac project root and raised
`FileNotFoundError: /Users`. The overwrite/symlink test had the same omission.
Log: `linux-ci/hosted-next-capsule-repro.log`.

Both tests now obtain the existing `current_test_qa()` bytes once per case and
pass those identical bytes through seal/verify, including negative paths.
Stale-input, overwrite and linked-path refusals are unchanged. No production
default, pinned operator file, validator guard, global monkeypatch or synthetic
Mac directory changed. The full capsule file passed **four cases**, Linux
native console pytest in **3.12s**, Mac focused runner in **10.971s** (test
execution 9.05s). Logs: `linux-ci/capsule-explicit-qa-after.log` and
`ci-remediation-capsule-qa-mac.log`. Manager static review independently confirmed
the omission and the existing fixture seam. This does not explain the remaining
hosted markers.

The first inferred paid-entry case passed isolated Linux in **22.18s**; actual
Node plus paid-entry through console pytest also passed in **23.90s**. Native
loader/cache/session/order differences remain hypotheses rather than fixes.
After two invalid nonroot preflights (an omitted newly tracked fixture, then
copy modes contaminated by the container's default umask 0000), both failures
were preserved and the method was reassessed before another case invocation.
Neither invalid preflight counts as a product or UID result.

The fresh nonroot v2 snapshot uses exact published project Git head `2b3c8d66`,
dependency head `4f9b2128`, current uncommitted test corrections, authoritative
source bytes/modes, its own frozen-lock environment, native console pytest,
default bytecode/cache behavior, and explicit umask 022. Its separate preflight
passed before tests: 2,379 files, ownership/modes/link counts, project/dependency
Git contexts, interpreter/shebang, editable `.pth` and actual imports all
matched. Evidence: `linux-ci/hosted-next-nonroot-v2-preflight.log` and
`linux-ci/current-source-manifest.json`. The two exact cases passed **21.66s**
(`linux-ci/hosted-next-nonroot-v2-cases.log`); UID alone is not established as a
cause. Initial diagnostic project Git was `99f21684`; `4f9b2128` was its
dependency, not project HEAD. Those contexts are not relabelled current.

Actual hosted Node v22.23.3 matches the container. Hosted Python is 3.12.15/x64
from setup-python, versus the container's 3.12.3/arm64. Hosted setup exports
`LD_LIBRARY_PATH`; the paid fixture uses `env python3`, while the owning
supervisor deliberately strips `LD_*` variables. This is an unproved loader
boundary lead, not authorization to weaken production filtering or alter its
QA contract. The cheap primary audit cannot establish hosted loader dependence
using the system interpreter available in the container.

The manager authorized exactly one temporary workflow-only hosted diagnostic,
isolated from retained `main` and wanted corrections, based on failed `2b3c8d66`.
The isolated workflow-only commit is `6dd4cd4f357c4355644fb1d9a284a9c441d909ed`
on `codex/hosted-python-diagnostic-20261018`, exact parent `2b3c8d66`. It replaces
only the existing registered `.github/workflows/ci.yml`, with explicit read-only
contents permission, successful-preflight gates for both exact native cases,
and scoped JUnit/fixture-log artifacts. YAML and embedded Python syntax checks
passed; independent read-only review found no blocking issue. Exactly one
`workflow_dispatch` created diagnostic run
[39172239738](https://github.com/Wenjun-Mao/plotloom/actions/runs/39172239738)
at 22:26:37Z on 2026-10-18; initial metadata confirms that exact commit/ref.
The job failed naturally in **1m7s**: setup and preflight passed, then both
exact cases failed; collection and artifact upload passed. Preflight confirms
Python 3.12.15/x64, Node 22.23.3, UID 1001, umask 022 and exact source/import
provenance. Removing `LD_*`/`DYLD_*` for interpreter startup exited zero with
empty stderr: the proposed loader dependency was not reproduced. The full run
log, final metadata, artifact metadata and SHA-256 file manifest use prefix
`hosted-python-diagnostic-39172239738`; artifact `12152653959` has digest
`sha256:36e403a51cc451606deed60823b04df1674a235a1cce9684aaaee325607f6958`.
This diagnostic is not release qualification; retained `main` corrections remain
uncommitted and held, with no replacement full run authorized or dispatched.

Both cases fail before native launch at the helper's `unsafe regular file`
read guard. Node TAP is **20 passed / 33 failed / zero skipped**, all 53 inner
cases retained. Paid prepare returns raw `HELD`, calls only `prepare`, and has
no original handle or child. The helper checks QA regular-file identities with
`read(name, false)`, requiring no group/other write bits. The exact runner-image
source tag `ubuntu24/20261012.334`, `configure-system.sh` blob `829f338b`, applies
`chmod -R 777 /opt`, covering the reported `/opt/hostedtoolcache` interpreter;
the official Python 3.12.15 Ubuntu 24.04 x64 archive itself starts with a 0755
physical binary. Evidence is in `hosted-python-exact-image-permissions.json`
and `hosted-python-3.12.15-official-archive-metadata.json`. These are provisioning
source/archive evidence, not a direct hosted physical-binary stat.

A bounded local causal check used one test-owned copy of the actual Linux
interpreter, UID 65534 / one link, with only its mode changing. At 0755, Node
passed **2.17s** and paid entry **20.17s**. At 0777, both failed at the same
`unsafe regular file` boundary (**0.84s / 4.22s**); after restoring 0755, Node
passed again. The original disposable venv interpreter alias was restored in
`finally`; no system interpreter was changed. Source and helper guards remained
unchanged. Logs and result are under `linux-ci/hosted-python-qa-mode-causality*`
and `linux-ci/qa-mode-causality-logs/`. This establishes the shared unsafe-mode
precondition, not successful release coverage of the original 17 markers.
A workflow-owned test-environment correction was proposed for manager review;
no production filtering, QA defaults or refusal guards have changed.

The manager subsequently approved owned copy-based test-runtime provisioning,
excluding chmod of the source/cache interpreter. Its stable local implementation,
focused evidence and remaining hosted/budget gaps are recorded in the separate
[owned-runtime checkpoint](2026-10-18-owned-test-runtime.md).

After preserving the invalid v1's exact Git context, tracked source hashes and
modes (`linux-ci/hosted-next-invalid-nonroot-v1-preservation.json`), only the
identified synthetic container directory `/tmp/plotloom-hosted-nonroot-20261018`
was removed under the manager's prior cleanup authorization. The valid v2,
logs, managed diagnostic worktree and remote branch remain retained. No live
home, host row, deployment, credential file or helper process was changed.
