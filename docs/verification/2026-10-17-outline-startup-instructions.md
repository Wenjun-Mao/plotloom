# Frozen Outline startup correction — October 17, 2026

## Cause and ownership

The walkthrough's first Outline attempt on `2bb54595` crossed native Popen, then
reported `failed to load AGENTS.md instructions` with an operation-not-permitted
error. Its inspected JSONL stream was empty. The exact original instruction lookup
path is not established; global, ancestor and local discovery all lie outside
the frozen-package authority unless explicitly granted.

The invocation ignored user configuration but did not disable automatic
instruction discovery. That conflicts with its intentional deny-root/auth-home
permission policy during session initialization. Missing exact session and terminal
proof then correctly produced UNKNOWN, not an inferred safe failure.

Implementation: `1b9af397f1167c16ade2a54a73f25c20d5379cba`.
[ADR 0187](../adr/0187-frozen-worker-instruction-discovery.md) records the shared
text/image policy: `project_doc_max_bytes=0`, with the source-owned stdin prompt,
frozen package and pinned resources retaining instruction authority. Command
construction moved to the existing child-environment owner; other auth, model,
feature, permission, prompt and evidence behavior is unchanged. No filesystem
grant was widened and no user instruction file was edited.

## Mechanism and regression evidence

An owned, credential-free native initialization probe used the installed CLI,
the unchanged permission formatter, a fresh fixture with ambient instructions,
an empty diagnostic authentication home and a closed loopback provider endpoint.
Only `initialize`, `initialized` and ephemeral `thread/start` were sent; no
generation turn or existing session was accessed. With default document budget,
the same AGENTS permission error occurred. With zero budget, initialization
succeeded with empty `instructionSources`. Both diagnostic processes exited 0.
The command arrays differ only by `--config project_doc_max_bytes=0`.

Native probe `4f0050` exited 0. Executable SHA-256:
`1afb28c01d7d49e892bd75f11076b10f1451e34e0ee308a95e5ab7f69f9c84fe`.
This establishes initialization behavior, not native model, ImageGen or creative
acceptance. It does not settle the original attempt's remote outcome.

Two expected-red invocation cases demonstrated the missing policy before the
fix. Then **59 focused cases** passed across supervisor environments, missing/
ambiguous image proof, helper reaping, profiles, prompts and JSONL runtime checks.
The separate bridge/isolated/supervisor union passed **71 cases**, with one
Starlette/httpx deprecation warning. Scoped Ruff F/I and whitespace checks passed;
the initial import-spacing finding is retained. Independent review found no
blocking change to permissions, source hashing, prompts or UNKNOWN safety.

The stable implementation at `1b9af397` passed one complete, unchanged
`scripts/verify.py full` invocation: **all 14 steps**, **3,100 Python cases across
261 files**, **1,381 frontend cases**, and **319 browser cases**, including types,
deterministic build/bundle parity, wheel build/installed-wheel smoke, media probes,
dependencies, API imports and archive-reader checks. Total elapsed: **1,254.169s**.
Original native handle `51568` closed naturally, `9cb026` → `9b5c01`, exit 0.
Full-log SHA-256:
`ca1096c54949e9055f956a786dcf598c275ac0755edabf4f195a98980ab9a165`.
This is a single full pass, not a composite of focused results or a speed claim.

Technical evidence is retained under `.local/outline-instruction-startup-20261017/`:
the original error hashes and inspected ledger facts in `rca.json`, the no-turn
diagnostic and results, expected-red output, focused/service logs and full log.
This is not an archive of the discarded user's run.

## Recovery and deployment boundary

Existing cancellation/suspension does not acknowledge an uncertain outcome or
release its hold. Re-starting the project would return the retained run, and
deploying a changed profile is not run recovery.

The owner separately authorized permanent removal of the last failed run, without
saving it. After full verification, with the installation stopped and both recorded
processes and groups absent, an independently reviewed, exact-ID offline operation
removed that run's dependent rows, prepared Outline candidate/execution pin, host
attempt and reserved slot, plus only its job and private-attempt directories.
It cleared the stale candidate pointer; all other project/canonical rows and the
project manifest stayed unchanged, and both databases passed foreign-key checks.
No archive was created. The saved brief and accepted source remain available.

The removal is explicit operator disposal, not fabricated terminal settlement:
the historical remote outcome remains unverified. No replacement generation was
started. Activation uses the existing installation configuration; readiness/profile
checks do not authorize an automatic retry. Do not parse stderr into safe terminal
authority or silently generate a replacement.
Hosted CI, native generation and product/creative acceptance remain separate;
optimization and speculative batching stay parked.
