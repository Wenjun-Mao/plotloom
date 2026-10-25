# Process-incarnation quiescence investigation, 2026-10-18

> Historical local artifacts in [the cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md) were retired
> on 2026-10-25. References to those files are not available attachments or resumption
> instructions; recorded outcomes, limits and current project-owned media stand.

Status: **fail-closed; no executable correction qualified or installed**.
Source baseline: `5f7dbf43369e3b57e84edd9cf1ee2cab2fee8f69`, retained checkout
`/Users/wjmao/.codex/worktrees/b30f/plotloom`. Deployment remains at `7b90bbc7`.
This record implements the approved investigation fallback, not activation.

## Failure and owning layer

The remaining A99 development home cannot be revoked because its completed host
attempt `1597629c-a398-4f76-99fb-a3bb441adff6` retains worker PID/group `90191`,
and that numeric group is live. The native host deletion guard deliberately
requires positive quiescence independently of terminal state. That guard is the
correct layer; deletion, receipt rewriting or process termination downstream
would not repair the missing evidence.

The current occupant is the CUA node process, with PGID `90191`, SID `1`.
Its differing command and apparent later birth are consistent with reuse, but
the old identity does not by itself certify a different incarnation. The earlier
[activation report](2026-10-18-batch-video-publication-and-activation.md) described
this as reuse; the tests below qualify the evidential strength of that diagnosis.
Historical observations remain retained without being relabelled as proof.

## Actual observations

Runtime: macOS 27.0.1 / Darwin 27.0.0, arm64, kernel `xnu-13432.1.9~1`.
Read-only observations and bounded child probes are retained under
`.local/batch-video/pid-proof-research/`. The two child probes exited normally
through stdin; no nonzero signals were used and no CUA lifecycle API was called.

- `runtime-observations.json`: successful `getpgid(90191)=90191`,
  `getsid(90191)=1`; an owned `start_new_session=True` child had PID=PGID=SID,
  while an owned group-only child had PID=PGID with a different SID.
- The same current PID's `ps lstart` was `Sun Oct 18 15:59:38 2026` under
  `TZ=UTC0`, and **exactly** `Sat Oct 17 21:35:40 2026` under the valid
  `TZ=XXX18:23:58`. The latter equals the retained old timestamp. These were
  per-probe environments, not changes to the host or live worker environment.
- `public_birth.c`, `public_birth`, `kernel-birth.json`: compiled against the
  installed public SDK with warnings treated as errors; `PROC_PIDTBSDINFO`
  returned the exact 136-byte `proc_bsdinfo`, PID/group `90191`, and UTC birth
  `1792339178.407378` (`2026-10-18T15:59:38.407378Z`). No private ABI was used.
- `ledger-time-bound.json`: the exact row, opened SQLite read-only, retains
  `updated_at=1792287398.4017432` (`2026-10-18T01:36:38.401743Z`), numerically
  51780.005635 seconds before that current kernel birth. Runtime `time.time`
  uses `clock_gettime(CLOCK_REALTIME)`, adjustable and non-monotonic.

These observations are not a synthetic exit receipt or a fresh abandonment
preview. No historical token, status, receipt, reservation or slot was changed.

## Proofs assessed and rejected for this retained identity

### Timestamp or command inequality

`control._process_identity` collects local-second start text, group and command
in three separate `ps` calls. It records neither timezone nor an atomic kernel
incarnation identity. The actual alternate-timezone probe reproduces the exact
old timestamp for the current occupant. Command changes can occur within one
incarnation, including exec, and neither completed status nor leader exit proves
whole-group absence. Same-second collisions and sampling races add ambiguity.
No parsing tolerance or command-hash exception repairs these limitations.

### Session-leader retirement

A verified original session leader cannot change its session/group through
exec, `setsid` or `setpgid`. A later successful `getsid(recorded_pid) != pid`
would therefore establish a different incarnation. Reviewed XNU allocation
excludes numbers still present in process, group or session tables, which would
then imply retirement of the old isolated group/session, including leaderless
members that remain in it. See [Python Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen),
[Apple setsid](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/setsid.2.html),
[Apple setpgid](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/setpgid.2.html)
and the [pinned allocator](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/kern_fork.c#L940-L998).

The missing premise is original session-leader provenance. Worker, CLI and
validator production launchers use `start_new_session=True`, including installed
`7b90bbc7`. However `_register_worker` enforces only PID=PGID; the private worker
entrypoint can register from a non-session-leader group. The legacy row stores
no SID or certified launch-origin witness. The normal production call graph is
not a persisted witness for this exact retained row. The manager explicitly
confirmed this premise must not be assumed. Enforcing a new invariant cannot
retroactively certify the old one.

The pinned published XNU source is semantic research evidence, not established
exact correspondence to the running `xnu-13432.1.9~1` kernel. No product platform
support claim was introduced. Missing/denied probes, equal SID, nonisolated
origins and unsupported kernels would require refusal even with a future proof.

### Current native birth later than retained update

`_register_worker` samples `time.time()` after identity capture; ledger updates
also sample it after retaining that identity. This establishes event order,
not numerical calendar order. A valid counterexample is one process born at
calendar value B, followed by a backward calendar step, then registration/update
at U<B. The same process can remain alive at the current probe with native
birth B>U. Later updates can decrease U; they are not necessarily conservative.
[Python documents this clock behavior](https://docs.python.org/3/library/time.html#time.time).

XNU samples separate calendar and absolute times for process birth, preserves
birth across exec, and permits backward calendar steps that also adjust boot
time. Thus current boot time/UUID cannot recover the absent historical mapping.
See [birth preservation](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/kern_fork.c#L1124-L1133),
[calendar/absolute sampling](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/kern_time.c#L772-L783)
and [calendar adjustment](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/kern/clock.c#L674-L748).
No retained compatible-clock guarantee was found. The observed 14-hour gap is
consistent with reuse, but its size does not supply the missing guarantee.

Public `PROC_PIDTBSDINFO` could supply a future original UTC birth sample;
comparing two retained native samples of the same immutable birth avoids the
later-wall-clock bound problem. The old row contains no such original sample.
Unique-ID structures found in XNU private headers are absent from the installed
public SDK and were not adopted. No future identity framework was added.

## Verification, review and next action

The independent read-only Sol/High reviewer challenged launch provenance and the
UTC-bound lead and reached the same fail-closed result. Effective host model
settings were unverified. The existing guard's focused selection passed all ten
cases in 5.622 seconds, exit zero:
`uv run --locked --no-sync python scripts/verify.py focused --pytest tests/services/creator_workbench/test_project_abandonment.py`.
Log: `.local/batch-video/pid-proof-research/existing-abandonment-guard.log`.
This covers its worker/CLI/validator/spawn blockers, stale preview, project
exclusion, UNKNOWN-slot preservation and late-publication refusal. No executable
inputs changed; no new module/full qualification or creative acceptance is
claimed. The native guard, publication/admission fences and revalidation remain
intact. Documentation diff/command consistency checks passed. The independent
review of this stable investigation and ADR note returned no concrete findings.

Safe continuation requires a real supported absence observation for the retained
PID/group, or independently retained original-incarnation evidence satisfying a
reviewed proof. Natural process exit may eventually permit a fresh native
preview; no reset, signal or history rewrite is authorized to manufacture it.
Until then, stage and activate nothing. There is no qualified guard patch to
install before deleting the incompatible home; new-schema readers must remain
uninstalled while that home remains discoverable.

## Separate hosted CI result

[Run 39146800414](https://github.com/Wenjun-Mao/plotloom/actions/runs/39146800414)
finished **failure** at `00773e659fa95a311d8c6ec0c714182352bd9e06`.
Browser shards 2/3/4 passed. Shard 1 failed
`storyboard-static-report.spec.ts:77` (horizontal overflow), including retry.
The verify job's Python/distribution step timed out after 45 minutes around 90%
with failures/errors already printed and no final pytest failure report.
Preceding frontend/type/build/static-diff checks passed. Complete failed logs:
`.local/batch-video/hosted-ci-39146800414-failed.log`. These remain unresolved
implementation qualification failures; they are not waived or attributed to a
new guard. The manager is serializing separate evidence-backed diagnosis.
