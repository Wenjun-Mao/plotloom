# Owned copied hosted-test runtime checkpoint — 2026-10-18

Sections through “Retention and remaining gaps” preserve the initial
`f7fcf080` checkpoint. The follow-up below supersedes its pending execution and
authority statements; retained failed evidence is unchanged.

## Authority and boundary

This is the manager-approved continuation of batch-video delivery's
[hosted remediation](2026-10-18-hosted-qualification-remediation.md), step 5.
Sole writer: retained `/Users/wjmao/.codex/worktrees/b30f/plotloom`, `main` based on
`2b3c8d6650122adf0b503c36fa42f48206bd740e`, initially uncommitted corrections.
The five earlier wanted files remain preserved. This follow-up ends at a stable
local diff and scoped evidence for review. It authorizes no new hosted dispatch,
release/full run, push, activation, owner-data deletion or live process action.

## Diagnosis and decision

Diagnostic run 39172239738 passed its provenance preflight, then both exact
proof cases failed at `unsafe regular file` before launch. A test-owned real
interpreter reproduces both failures at 0777 and both passes at 0755. The exact
hosted image's source applies `chmod -R 777 /opt`, covering its reported Python
toolcache location. Direct hosted physical-binary metadata remains unobserved;
this is supported causal evidence, not proof of every original failure marker.
The initial loader hypothesis was not reproduced: stripped-loader startup
exited zero. Original unfiltered run 39166995435 remains failed.

[ADR 0196](../adr/0196-owned-copied-hosted-test-interpreter.md) places the fix in
test provisioning: a fresh owned standard-library copy-based `.venv`, existing
frozen dependencies, genuine observed metadata, and explicit Python pytest.
Source/cache modes, production guards and QA defaults remain unchanged. No
alternate QA metadata, fallback selection, timeout increase, suite filter or
parallelism change was added.

## Implementation

- `scripts/testing/provision_test_venv.py` refuses existing environments and
  ambient interpreter-selection overrides. It verifies regular owned one-link
  copies, expected source hashes and executable modes before normalizing only
  the new copies' group/other write bits. It records genuine executable,
  resolved executable, raw/physical base-prefix, prefix, implementation, exact
  version and architecture; copies/config/aliases/facts must remain identical
  after frozen sync and both no-sync and sync-enabled uv probes.
- Both ordinary hosted jobs invoke that one helper. The complete Python gate
  uses `.venv/bin/python -m pytest -q --durations=20`; its selection and existing
  45-minute step / 55-minute job budgets are unchanged.
- Focused regressions retain unsafe-mode/hash refusals, reject linked,
  mismatched, unowned and nonexecutable copies, and detect configuration,
  alias and runtime-fact drift. Module ownership includes the new test/tool.
- The synthetic paid fixture asserts genuine QA runtime and import provenance
  in prepare, outer and inner processes, recording observations in its existing
  owned receipt directory. The successful entry checks all three. Production
  code, copied-source imports, admission and receipt/HOLD behavior are unchanged.

## Executed scoped evidence

Evidence below is in retained checkout `.local/batch-video/`.

1. **Feasibility:** existing owned nonroot Linux container/checkout, CPython
   **3.12.3 / aarch64**, UID 65534, umask 022. Fresh `venv --copies --without-pip`,
   frozen sync from the existing cache, explicit Python and subsequent uv use
   retained owned one-link 0755 copies with exact source hash/version/facts.
   Actual capsule and paid-entry cases passed **2 / 22.91s**. Source interpreter
   unchanged. `linux-ci/copied-test-venv-feasibility.{log,json}`.
2. **Mac focused:** `verify.py focused` selected
   `test_test_venv_provisioning.py`, `test_ci_browser_contract.py`,
   `test_verification_module_ownership.py`, and `test_cli_handoff_capsule.py`:
   **26 passed**, runner **7.077s**. `copied-test-runtime-focused.log`.
3. **Mac paid boundaries:** successful entry and duplicate-admission cases:
   **2 passed / 39.98s**, focused runner **41.839s**.
   `copied-test-runtime-paid-mac.log`. The subsequent native-fixture edit only
   reordered imports; final bytes are exercised on Linux below.
4. **Final implemented Linux:** fresh helper execution including frozen sync,
   both subsequent uv probes and checkout/frozen pytest import checks. Its
   explicit `.venv/bin/python -m pytest -x -vv --tb=long` selected the same four
   files, successful paid entry, duplicate admission, and
   `test_pair_original_handle_attendance_before_deliberately_held_callback`:
   **29 passed / 47.48s**. Inner Node TAP **55 passed / zero failed/skipped**.
   `linux-ci/copied-test-runtime-native.log`; initial 27-case implementation
   evidence is retained separately as `copied-test-runtime-native-initial.log`.
5. **Actual process observations:** prepare/outer/inner each used the copied
   project interpreter/prefix; application imports came from the disposable
   paid source, pytest from the frozen project environment, test support from
   the intended caller checkout. Three observed receipts plus Node result and
   `pyvenv.cfg`: `linux-ci/copied-test-runtime-observations.json`.
6. **Quick:** `verify.py quick` passed **13.205s**, including all 1,415 frontend
   cases and both type checks. `copied-test-runtime-quick.log`. Later changes
   only affected Python test tooling/fixtures and documentation.
7. **Native ownership:** discovery passed **3,285 Python / 1,415 frontend /
   338 browser** cases, with no test-body execution.
   `copied-test-runtime-native-ownership.log`.

Targeted Ruff checks and `git diff --check` pass. Broad Ruff on the shared
native fixture has three pre-existing unrelated findings; its unused-import/
undefined-name checks pass, and baseline findings are retained in
`copied-test-runtime-native-fixture-baseline-lint.log`.

Initial Mac testing exposed raw base-prefix alias variation: the copied venv
reports an unversioned symlink while the caller reports its resolved versioned
base. Genuine executable/version/architecture and physical base match. Both raw
and resolved values are now retained; only the physical source-base comparison
is canonicalized, while all copied observations must stay identical. The first
log pathname was reused; its retained tool-output excerpt is explicitly labelled
`copied-test-runtime-mac-initial-failure-excerpt.txt`, not a complete raw log.
One unsupported test selector was rejected during collection before execution;
its separate `copied-test-runtime-paid-mac-invalid-selector.log` is not test
evidence. Correct exact selectors are used in the passing runs above.

Independent read-only review requested **GPT-6.1 Sol / High**; effective host
settings are unverified. Base and incremental review found no actionable issue,
including sync-enabled uv use and paid/pair fixture consumers. It ran no tests.

The manager reviewed all 16 candidate file hashes, the actual diff, ADR,
workflow/helper/QA fixtures and Linux process observations; no production source,
guard, QA default or dependency lock changed. Its independent retained-checkout
focused retest selected the same final four files plus successful paid entry,
duplicate admission and the shared pair callback: **29 passed / 50.92s**,
`verify.py focused` elapsed **57.280s**, exit zero. Its initial malformed command
was refused by argparse before collection or test bodies; only the corrected
repeated `--pytest` invocation is executed evidence. A separate attended
read-only Sol/High reviewer found no actionable issue and confirmed hashes;
effective settings remain unverified. These manager-reported results are not a
new full or hosted qualification. The manager then approved coherent local
commits and preparation of a hosted diagnostic draft, with publication,
dispatch, full runs and activation still held.

## Retention and remaining gaps

Only the identified superseded disposable venv was removed after its compact
configuration/alias record was retained; no broad dependency copy, checkout or
container image was created. The final copied environment remains in the
existing owned Linux checkout. Cleanup record:
`linux-ci/copied-test-runtime-retired-env-cleanup.json`.

`copied-test-runtime-candidate-inputs.json` binds this uncommitted checkpoint's
files; `copied-test-runtime-candidate.diff` retains the complete tracked/untracked
diff, including the five earlier wanted files. This is scoped local evidence,
not a current full release gate, hosted success or product/creative acceptance.
Exact hosted CPython 3.12.15/x64 remains untested with this setup; the original
serial-suite runtime budget remains a separate unresolved qualification concern.
Copied executables still use the selected base runtime's libraries; this does
not establish a separate immutable Python installation. Next action: prepare
the bounded exact-host diagnostic draft for manager review before remote writes.

## Follow-up: bind the synthetic CLI's real interpreter

The one authorized hosted diagnostic [39175064170](https://github.com/Wenjun-Mao/plotloom/actions/runs/39175064170)
used product base `f7fcf080` and workflow-only head `6619e729`. Source/copy
preflights passed: source CPython 3.12.15/x64 was directly observed at 0777 and
remained unchanged; all three owned one-link 0755 copies had identical bytes.
All 154 native case IDs matched JUnit: capsule/receiver 70 passed, paid 37 passed
and two failed, pair 45 passed, zero skips/errors/timeouts. This was a valid
failed diagnostic, not release qualification. Its ignored evidence summary,
full logs, 225-file artifact manifest and 214 retained fixture hashes remain
under `owned-runtime-diagnostic-39175064170-*`.

Both actual stderr traces fail importing `dotenv` from copied `plotloom.config`
inside the Python fake CLI sandbox, before real Node validation. Its old
`env python3` launcher did not bind pytest's explicit test interpreter. Exact
remote fake-CLI executable/prefix were not observed. The local ambient Python
already had the dependency; the private dependency-free PATH control reproduces
selection without relying on that inference. This is a synthetic launch boundary
defect, so the fix belongs in the test-owned launcher, preserving production
environment filtering, PATH behavior, guards, QA defaults/pins and validators.

Manager approval binds the wrapper directly to the raw absolute QA entrypoint
under ADR 0196's 127-byte encoded shebang bound, with unsupported paths refused
before wrapper creation/allocation. New small stdlib runtime support records
exclusive PID startup facts before project imports and separate successful
sandbox imports. Assertions use real current QA fields; exact patch/raw prefixes
are observations, not new pins. Valid and invalid journeys verify every sandbox
and actual copied source plus checked-environment `dotenv` origins. They prove a
private `python3 -I -S` control lacks `dotenv`, reset its selection marker, and
require no ambient selection while retaining genuine Node output/hash and
missing-params/no-receipt/no-retry assertions. Duplicate refusal remains narrower
than successful first delivery. Shared helper/test ownership is registered.

Executed scoped evidence (all paths below relative to `.local/batch-video/`):

- Before correction, the existing valid-delivery case under the hostile PATH
  failed at actual ambient selection: **1 failed / 13.38s**, focused runner
  **14.913s**. `fake-cli-ambient-before.log` and
  `fake-cli-ambient-before-observations.json` preserve the real control,
  missing-dependency traceback, failed result and owned settlement.
- Mac CPython 3.12.13/aarch64: initial 12 path/startup cases plus both genuine
  hostile-PATH journeys **14 passed / 39.91s**, runner **42.878s**.
  `fake-cli-launch-focused.log`; actual startup/sandbox/control/validation and
  settlement observations are retained in `fake-cli-launch-mac-observations.json`.
  After adding explicit Unicode-whitespace coverage, final 13 unit cases plus
  seven ownership cases **20 passed / 0.65s**, runner **2.910s**:
  `fake-cli-launch-final-unit-ownership.log`.
  Final native ownership discovery passed **3,298 Python / 1,415 frontend /
  338 browser** cases without executing test bodies:
  `fake-cli-final-native-ownership.log`.
- The existing Linux checkout/copied venv is reused, CPython 3.12.3/aarch64,
  UID 65534. Its 14 recorded executable inputs match the retained candidate;
  its Git HEAD remains `2b3c8d66` with those current working bytes, rather than
  claiming an exact new committed Linux checkout. See
  `linux-ci/fake-cli-linux-observed-executable-inputs.json`.
- Linux execution setup mistakes were retained and diagnosed separately:
  missing uv cache setting stopped before collection; inherited umask 000
  created owned 0777 source roots and caused mode refusals (107 passed,
  16 failed, 38 setup errors); inherited Docker interpreter overrides then
  caused two exact journey preflight refusals, before sandbox invocation.
  These are `fake-cli-paid-pair-families.log`,
  `fake-cli-paid-pair-families-corrected-env.log`,
  `fake-cli-family-setup-mode.json` and `fake-cli-launch-exact.log` under
  `linux-ci/`. The override cause was read from the actual capsule child
  traceback; `fake-cli-launch-override-observation.json` labels its retained
  tool-output excerpt after normal pytest retention removed the original root.
  No guard or source behavior was changed to bypass these setup failures.
- Reassessment restored the established environment: umask 022, existing cache,
  no ambient interpreter/root overrides and the verified copied engine.
  `linux-ci/fake-cli-execution-preflight.json` records actual facts. The exact
  valid/invalid journeys then **2 passed / 35.41s**, runner **37.375s**:
  `linux-ci/fake-cli-launch-clean-exact.log`.
- With that verified environment, focused selections were
  `test_paid_outline_cli_runtime.py`, `test_paid_outline_handoff.py`,
  `test_paid_outline_processes.py` and all four
  `test_qualification_pair_{contracts,measurements,observation,wiring}.py`
  files: **162 passed / 185.88s**, one existing FastAPI deprecation warning,
  runner **191.921s**. `linux-ci/fake-cli-paid-pair-clean-families.log`.
  `linux-ci/fake-cli-final-observations.json` retains actual checked-engine
  startup facts (59 valid / 48 invalid invocations), two valid and one invalid
  sandbox import records, absent ambient markers, real validation output and
  all 54 owned settlement reports. The two actual journeys and 50 other
  reports are empty; two passing adversarial unit tests intentionally retain
  mocked numeric-reuse/missing-spawn uncertainty with no signal. This is not
  live-owner quiescence evidence. The initial collector's overbroad “all reports
  empty” assertion was corrected after reading those existing negative tests;
  no test assertion or process guard changed.

Targeted Ruff and `git diff --check` pass. New helpers stay below 100 lines and
the existing handoff case owner remains below 400 lines.

Independent stable read-only review requested GPT-6.1 Sol / High (effective
settings unverified) found no actionable issue in launcher validation,
provenance, hostile-PATH assertions or the separately approved CI method. It ran
no tests. Full local/hosted qualification and product acceptance remain pending;
no hosted retry, main push, activation, provider or live owner/process action is
authorized by this correction checkpoint.
