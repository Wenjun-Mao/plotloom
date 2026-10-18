# Owned copied hosted-test runtime checkpoint — 2026-10-18

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
