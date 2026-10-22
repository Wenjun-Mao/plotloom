# Image instruction access and no-dispatch recovery checkpoint

Local source checkpoint on `main`, based on `b1e0bf98`; implementation is defined
by the commit containing this record and [ADR 0197](../adr/0197-codex-exec-image-instruction-access.md).
At the initial implementation checkpoint, no push, CI, full release gate,
deployment, live settlement or provider call had been performed by the source
owner. Subsequent manager activation and the single final local gate are recorded
below. Prior hosted failures remain failed. The manager owns live operations.

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
operation was claimed by that implementation checkpoint; the manager's subsequent
execution is recorded below.

Inactive current-v8 project reconciliation uses its admitted frozen profile and
records the failed checkpoint without dispatch. A paused run stays paused.
An explicitly canceled/taken-over run may also cancel the stopped proposal using
the no-dispatch proof. Resume still requires current profile/pins and therefore
cannot replay this old policy. Continuation must use its native preview after all
other retained work is terminal; this single recovery does not prove whole-run
eligibility or authorize cancellation, deletion or creative acceptance.

## Small real E2E handoff

The active supported native QA project is
`f03a5e3d-6a75-4f5c-b29a-21420ce9a7b6`, run
`702a6a7e-f87d-45ed-ae12-b07b436120da`, on installed `081d56d4`.
It uses a six-second/two-shot 2D 林禾/sunflower Brief, normal fresh pre-video
admission, `styleAuthority=brief`, `maxJobs=16` and `maxImages=8`. H3 remains
bounded to two submissions/ten requested source seconds. Machine adoption and
provisional selection are genuine native authority, not fabricated human facts.
Actual whole-pack material approval is required before H3 Start; real clip/audio
review and final whole-pack acceptance remain required afterward. This record
does not claim those milestones or completed H3 E2E.

The earlier authored manual draft `fd2608aa-dac9-4559-b216-31c78e365f8a` is unused
with no provider jobs; its standalone storyboard-approval request was withdrawn.
The first native QA `e03aca22-d335-47c9-ac06-5d92af0ce9a9` produced the genuine
image milestone below, then hit its frozen five-image cap because its inventory
required six images. The manager canceled it through native control at revision
34 → 35, retaining all checkpoints and the delivered, unadopted C01 candidate.
No policy edit, invented adoption or continuation shim was used; current native
continuation cannot inherit that delivered-but-unadopted success. A fresh bounded
fixture provides current authority. See ignored manager evidence
`.local/batch-video/native-small-e2e-cap8-start.json` (SHA-256
`1e446cab8602d98955ef1b97e50e3fa03edf596b4506590b052d25fa24ffa464`).
The owner story remains paused and separate. Product/infrastructure/coordination
timing breakdowns and cost deltas are unavailable; recorded gate durations follow.

## Manager activation, recovery and actual ImageGen milestone

Manager evidence checked October 18, 2026, 23:22 EDT records the same installation
clean at detached `081d56d4`, with the application container healthy. The actual
installed-source sandbox reads the exact 8,946-byte skill with SHA-256
`76c6097e2736396762c1133ba9f3dd08bc14968fa0be5a2a42f7f97b9f907d64`;
unrelated `AGENTS.md` remains denied.

The exact P01 recovery returned HTTP 200, `settled/no_remote_dispatch`,
`processExitCode=null`, released budget and no successful receipt/output.
Its retained proof hash is
`29a4d8ec302e316ad7ed2017d4b61d18336659a8c4f9341524f9d3b000a32b95`.
All five protected-file hashes/modes/UIDs and all 15 disabled queue entries match
the manager baseline; no validators remain. The unrelated old UNKNOWN row hash
stays `364e43b268bd231a1c721c53c1af5df5cdbe56f969e7324759f3e48e95b9180b`.
The owner run is paused at revision 123, with eight text/two image adoptions and
P01's failed checkpoint. Recovery did not cancel, continue or resume that run.
Evidence: `.local/batch-video/image-instruction-live-recovery.json`, SHA-256
`7b12a6f57de39f92423938f6afc4f00ed05c9af96ab7e06dcd1edadd3e412023`.

The manager's first real native QA image completed on the same installed source:
attempt `0164f1bc-d4ba-4c2b-a239-459bf3aefa4f`, job
`ij_16a23080408649d6bd6168c1c1487506`, session
`01a15239-a28d-7161-9053-a9114761cc02`. The genuine waiter recorded exit 0;
the exact ImageGen call/event, host receipt and schema-5 completion agree on one
1,546,699-byte output with SHA-256
`86a47626d5e16d42be42880696fecd7e9c534c3a8f8ecedc4898d56e7a231563`.
Remote state is completed and its image budget consumed. This establishes the
repaired native worker → real ImageGen → trusted publication path; it does not
establish creative acceptance or H3 production. Evidence:
`.local/batch-video/native-small-e2e-first-image.json`, SHA-256
`6ad0f95451c8b7cd7e395e89fe7174ac21e11c38b03ca7ccdfcc4c9bf05411d0`.

## Final single local full qualification

One sole executor ran exactly
`uv run --locked --no-sync python scripts/verify.py full` on clean
`081d56d4b69eba24205b26b2100c4c47a7dbe533`. Executable inputs stayed unchanged
through completion, including checked generated assets. Exit 0; elapsed
**1,649.439 seconds (27m 29.439s)**. Runtime was macOS 27.0.1 arm64 / Python
3.12.13, separate from the earlier failed hosted Linux/x64 qualification.

| Gate | Result | Recorded seconds |
| --- | --- | ---: |
| Frontend units | 1,415 passed / 162 files | 6.493 |
| Frontend types | passed | 4.114 |
| Python native suite | 3,365 passed / 289 files | 1,050.831 |
| Deterministic bundle / checked parity | passed / passed | 1.400 / 0.021 |
| Unfiltered browser coverage / suite | passed / 338 passed | 1.879 / 579.448 |
| Wheel build / installed-wheel smoke | passed / passed | 0.123 / 4.319 |

Lock, ffmpeg/ffprobe, API-import and archived-reader steps also passed. Worker 1
completed 1,844 cases in 1,027.44s, fingerprint
`3525fc3fcffe91c273c87ac7e1138f5157df214dfb72933493563a9d93102f31`;
worker 2 completed 1,521 in 941.04s, fingerprint
`46c48df840f157fa2e9773ddf9d4a52608d46065e443f2faee645e449d05985f`.
Their native union fingerprint is
`f5ae62559852ed400497f3821a7f15193958b6701d76ae38ea51ea148581316a`.
Existing Starlette/jsdom diagnostics did not fail their gates.

The raw log is `.local/batch-video/final-local-081d56d4.log`, SHA-256
`1d1f27340a61a5439cbef842c094f7ef83002302a0a5b8da1376883421895070`;
stage/runtime evidence is `.local/batch-video/final-local-081d56d4-summary.json`.
No retries, separate repeated selections, CI, pushes, live provider calls or live
operations were performed by this qualification executor. This later checkpoint
changes documentation only, so the qualified executable revision remains
`081d56d4`. Hosted run `39182416805` remains failed; no hosted replacement or
human material/AV acceptance is claimed.
