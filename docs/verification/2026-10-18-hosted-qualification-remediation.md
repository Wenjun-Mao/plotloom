# Hosted qualification remediation, 2026-10-18

Status: composed local release qualification and manager review passed.
The final full attempt exposed one browser-test synchronization race; its
test-only correction passed focused and unfiltered downstream qualification.
Correction revision: `0af49b61fc64ed048a239cefbf22a584fb15a096` in
`/Users/wjmao/.codex/worktrees/b30f/plotloom`, based on
`99f2168495087dcc7e96b110e1a560edb0d99c4b`. No publication, live activation,
provider dispatch or creative acceptance is claimed here.
The 14 changed executable/test inputs are pinned in
`.local/batch-video/ci-remediation-inputs.json`, aggregate SHA-256
`7a5c8c30df7c1a892a20c0279169d9a139c90b4edc02aee3eb8663ba2a0c83af`.

## Failed hosted evidence and reproduction bounds

[Unfiltered run 39146800414](https://github.com/Wenjun-Mao/plotloom/actions/runs/39146800414)
failed at `00773e659fa95a311d8c6ec0c714182352bd9e06`. Browser shards 2/3/4
passed; shard 1's Storyboard static report overflow failed twice. The verify
job printed Python failures/errors before its 45-minute timeout, with no final
pytest failure report. Complete failed logs remain at
`.local/batch-video/hosted-ci-39146800414-failed.log`; hosted Playwright artifact
`12144236084` was the manager's read-only browser evidence lead. No gate budget
or required coverage was changed and no hosted rerun has been dispatched.

The reproduction uses a separate tracked-source/Git snapshot under
`.local/batch-video/linux-ci/source`, Ubuntu 24.04 arm64, Python 3.12.3, Node 22,
procps 4.0.4 and the lockfile's Chromium 151.0.7922.34. Hosted Ubuntu x64 used
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
and 1280x460 are retained under the snapshot's `frontend/test-results/`.
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
