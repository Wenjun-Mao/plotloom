# Image instruction access and no-dispatch recovery checkpoint

Local source checkpoint on `main`, based on `b1e0bf98`; implementation is defined
by the commit containing this record and [ADR 0197](../adr/0197-codex-exec-image-instruction-access.md).
No push, CI, full release gate, deployment, live settlement or provider call was
performed by the source owner. Prior hosted failures remain failed. The manager
owns installation and live operations.

## Observed root cause and exact evidence

Owner project `eee1ddaa-b047-460a-9987-703d678a295c`, run
`31854798-9ec5-4d90-b6b6-b85cca2bf510`, was paused by the owner.
P01 attempt `17006dd2-f4e4-432d-b9f8-bbe75a4806c2`, job
`ij_ad8ab108000f44c0bf6957e075757bc5`, retained UNKNOWN.
The exact session `01a151fd-b3f5-7011-9d62-697ba0900455` records three read
commands; its pinned-skill `cat` failed with `Operation not permitted`.
That third command is absent from stdout, so stdout alone was insufficient.

- stdout: 12,485 bytes, SHA-256
  `52a06c2c54a205ca26c002d39a79c7ec03992ae52e08afec855be16cd46ae6b2`.
- rollout: 152,630 bytes, SHA-256
  `b17de81d11bb932ee0cc10d527c4f6b6e3a197edd81374e7041446c71518fdcf`.
- Frozen request hash:
  `6d074c31b060e61cee38c70e7a5bea932c7986dfb66d85bd8607b8a2432413c6`.
- Frozen skill hash:
  `22114087e59f3bd73ac065547e4fb2c9c0371cc2048ed1a23411270d7c335698`.

Images supplied no source read paths, while the assignment required the pinned
skill. That skill also conflated manual delivery with host-owned package v8.
The repair validates and grants exactly one pinned skill file at admission and
launch, separates the two procedures, and versions the image assignment to v5.
Its current skill hash is
`76c6097e2736396762c1133ba9f3dd08bc14968fa0be5a2a42f7f97b9f907d64`.

## Early native evidence and focused verification

Before broad qualification, an actual `codex sandbox` invocation reproduced the
existing denial and then read exactly the frozen skill with a single-file grant.
The candidate resolver subsequently read the new pinned skill while unrelated
`AGENTS.md` stayed denied. Both made zero provider calls. The observed executable
SHA-256 matches the owner's frozen CLI executable identity.

Ignored evidence in the retained checkout:

- `.local/batch-video/image-skill-sandbox-70m2x1nh/evidence.json` — old denial
  versus exact-file read, before implementation.
- `.local/batch-video/image-skill-candidate-1k8i5jig/evidence.json` — actual
  candidate resource resolver and unrelated-source denial.
- `.local/batch-video/image-recovery-candidate-evidence.json` — read-only
  positive census of the original P01 telemetry, executable identity and source
  file hashes. This is parser evidence, not executed live recovery.

Executed local checks, with unchanged evidence reused across scoped repairs:

- `focused`: resource, prompt, environment, image failure and census owners:
  50 passed in 5.95s (runner 10.671s).
- `focused`: census, recovery owner, image failure, staged admission and attempt
  contracts: 84 passed in 9.01s (runner 13.906s).
- `focused`: namespace and finite qualification: 41 passed; the accompanying
  new project-consumer case initially failed. Its cause was a project snapshot
  still at RUNNING while the host had passed UNKNOWN and settled. A narrow
  process-bound coalesced terminal transition fixed that contract.
- Exact corrected project-consumer case: 1 passed in 4.79s (runner 6.581s).
  It verifies canceled-run receipt reconciliation after a host-profile change,
  a failed checkpoint, truthful proposal cancellation, frozen policy retention,
  and no new image admissions/resumes.
- Follow-up census/recovery and six adversarial terminal-contract cases:
  39 passed; the new live-waiter case initially expected one parser invocation
  although the closed census deliberately rereads the same exact session.
  Replacing that implementation-count assertion with an exact-session identity
  assertion yielded 1 passed in 1.53s (runner 3.043s). Its ordinary failure uses
  the genuine simulated `Popen.wait()` result and retains the private witness.
- Additional source-local supervisor and authenticated endpoint checks:
  17 passed in 16.29s, using `uv run --locked --no-sync python -m pytest -q`
  with `services/creator_workbench/test_codex_exec_supervisor.py` and the exact
  `test_bridge.py::test_control_endpoint_passes_the_exact_attempt_snapshot_to_the_supervisor`
  selector. These paths are outside `verify.py focused`'s accepted selectors;
  that initial selection was refused without execution.
- `quick`: 1,415 frontend tests, both type checks, lock and API-import checks
  passed (14.226s). Existing jsdom `window.scrollBy` diagnostics were emitted
  while tests passed. No frontend source/assets changed.
- Targeted Ruff on new recovery/resource test owners passed after import and
  unused-import cleanup. `git diff --check` passed. An initial wider Ruff call
  also exposed a pre-existing import-format warning in `codex_exec_resources.py`;
  that unrelated import was not changed.

Independent read-only review by `copied_test_runtime_review` found a shell-path
quoting gap; it was corrected with `shlex.quote` and three adversarial-path
regressions. Final review found no remaining actionable finding, including the
new-table ownership guards and coalesced terminal transition. The reviewer did
not rerun tests or operate live state. Effective model settings were unverified;
the retained requested setting was GPT-6.1 Sol / High.

## Installation and native recovery contract

The manager must first preserve/recheck the protected-file, old UNKNOWN and
disabled-queue baseline, exact deployment revision and process quiescence. Load
this coherent commit in the existing deployment checkout and restart the
source-importing bridge/application through their supported lifecycle. Dependencies
and frontend assets are unchanged. The private ledger creates two evidence tables;
existing attempt/receipt rows are not rewritten during initialization. Recheck the
new host profile and exact skill permission using its configured executable before
any new generation. Do not resume or repin the old frozen image policy.

The explicit operation is authenticated
`POST /exec-recover-no-remote-dispatch/17006dd2-f4e4-432d-b9f8-bbe75a4806c2`
with the existing private bearer authentication and JSON body
`{"attempt": <fresh exact full UNKNOWN attempt snapshot>}`. Do not log the token.
The caller supplies no exit code, proof or replacement identity. The native owner
reconstructs and twice checks bounded stable evidence under `BEGIN IMMEDIATE`,
requires positive worker/CLI PID and group absence, no validator, unchanged
package, empty stderr/delivery, one complete exact native turn, and exhaustive
allowlisted completed tools. Unsupported evidence leaves UNKNOWN and its capacity
unchanged.

Expected success is `settled`, `terminalResult=no_remote_dispatch`,
`processExitCode=null`, `remoteToolState=not_applicable`, released image budget,
no successful receipt/output, and an immutable retained original UNKNOWN snapshot
plus proof in `exec_recovery_evidence`. Only this attempt's slot/queue entry is
removed; the operation never drains queues. Verify original stdout/rollout/package,
protected files, disabled queues and unrelated old UNKNOWN
`06e80972-9dde-41ff-be71-b477c1477465` remain unchanged. No live execution of this
operation is claimed here.

Inactive current-v8 project reconciliation uses its admitted frozen profile and
records the failed checkpoint without dispatch. A paused run stays paused.
An explicitly canceled/taken-over run may also cancel the stopped proposal using
the no-dispatch proof. Resume still requires current profile/pins and therefore
cannot replay this old policy. Continuation must use its native preview after all
other retained work is terminal; this single recovery does not prove whole-run
eligibility or authorize cancellation, deletion or creative acceptance.

## Small real E2E handoff

The manager's isolated authored QA project is
`fd2608aa-dac9-4559-b216-31c78e365f8a`, with two shots and at most ten source
seconds. Existing manual image send uses specialist-chat authority; there is no
supported authored-project-to-native-Codex-Exec image path without a genuine
autopilot run. Use actual manual ImageGen delivery for the H3 journey and retain
native sandbox permission proof as separate evidence. Human storyboard/material
approval, real provider outputs and persisted batch readback remain required.
No synthetic run, receipt, approval or new adapter was added. The owner story
remains separate. Product/infrastructure/coordination timing breakdowns and cost
deltas are unavailable; the check/probe durations above are the recorded scope.
