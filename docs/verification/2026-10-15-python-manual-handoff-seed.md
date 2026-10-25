# Manual-handoff seed reuse and scoped Python measurement

> Local QA artifact references below are historical; the [2026-10-25 cleanup](../roadmap/2026-10-25-top-five-cleanup.md)
> retires their storage, replay/launch/cutback instructions and preservation holds.
> Recorded outcomes and limits remain; current ADR/API contracts still apply.

This receipt records accepted local implementation and scoped evidence. Root
accepted the documentation in review `61225c` for a docs-only local checkpoint.
It does not publish source or establish broader qualification or product acceptance. Current
direction and the proposed next slice are in the
[Python continuation](../roadmap/2026-10-15-python-speed-continuation.md).

## Source and functional correctness

Local commit `bec6107c98b50c9610d215e9db15cbc592664ee0`, parent
`5f71239ac278b073b898924093dbd3e5f537e7a5`, changes exactly
`tests/test_autopilot_handoff.py`. The manual-import/recovery case reuses the
existing guarded awaiting-handoff copy for prerequisite material only. Its
two fresh human handoffs, manual replacement, snapshot/restore/acknowledgement,
ordinary admission, exact receipt/currentness and portable-claim refusal remain.
An added final inventory assertion checks seed isolation after handles close.
The only other delta splits equivalent grouped-alias imports for Ruff ordering.

Root independently accepted behavioral/import equivalence and functional proof
(`91cfa8`, `5eb322`), then verified the one-path commit (`2a244e`). The exact
changed case passed, followed by all **14 cases / 2 files** in
`tests/test_autopilot_handoff.py` and `tests/test_autopilot_handoff_seed.py`.
Original native execution `exec-0c89b28f-a95f-44f1-a251-0abbc844f3d2`, session
75793, exited 0. Scoped Ruff F/I passed. This was focused correctness under
contention, not comparative performance; no retest was needed solely to commit
the unchanged tested bytes.

| Identity | SHA-256 |
| --- | --- |
| Candidate owner | `57ca5e4fe2408693b08be473577cc132f3cb204cbca1dafc8994d94ac1ebeda1` |
| Candidate executable input | `79973a3759870ef2c89487709c3b0c8d4c06cfdfa32498fcbbcb5e0a7a9793b8` |
| Reviewed/committed diff | `442e78271ab1b7101025640ffa9cda85165d497fc173f9684509da101afbeb2b` |

The functional result (retired local artifact)
has SHA `53200a7d58b0d4fcfe3ca79bf08484768644832f4befd2fb744c4282841bf989`.
The commit receipt (retired local artifact)
has SHA `ff24e38b8d8f5be62a0fb203633be4f41054a94076574b1698103d1fc4b075e7`.
Its source/environment/cleanup limitations remain unchanged; that functional
run had no separate loaded-module probe. The later pair supplies its own proof.

## Failed first allocation — no measurement

Allocation `manual-handoff-original12-bec6107c-pair-20261015-root-1` is
**FAILED/SPENT**. Original execution
`exec-2d668969-d340-459c-b393-69fc009da33a`, session 40739, exited 1 during
baseline AST preflight, after exact revision/submodule/source-input/owner-byte
checks passed. No collection or measured pytest child ran; no measured wall,
test failure or speed result exists. The
failed receipt (retired local artifact)
has SHA `8ee635f4fbab6162960c689fc5841ad5aa99efbea68e52803a990760e05a40c5`.
Root independently confirmed its four groups absent and exact registered root
removed (`b5ad33`). All nine failed-preparation/launch files remain immutable.

## Accepted v2 original12-owner pair

After separate corrected preparation, review, seal and new allocation
`manual-handoff-original12-bec6107c-pair-20261015-root-2`, original execution
`exec-6b8e7999-178c-4401-85b0-dff6171bc7e5`, session 19212, exited 0 naturally.
Root independently accepted its source/runtime, raw collection/completion,
timing, hashes and fresh cleanup checks in `3c4758`.

| Arm | Exact revision | Full command wall |
| --- | --- | --- |
| Before | `5f71239ac278b073b898924093dbd3e5f537e7a5` | 77.2727594159951s |
| After | `bec6107c98b50c9610d215e9db15cbc592664ee0` | 67.28105670801597s |

Observed difference: **9.99170270797913s**. Each arm ran one standalone
collection and one fresh measured pytest process on the unfiltered
`tests/test_autopilot_handoff.py`, building its natural session seed. Both
proved **12 passed / 1 file**, no skips/xfails, exact fingerprint
`5b5fc3cbb5bb77b1c0c4502cc727944bd77b0eecab20a128f7220d8de5f7faa1`.
The two seed guards remain required correctness coverage; their exclusion from
this original-owner pair does not remove them from whole qualification.

| Native elapsed phase | Before | After |
| --- | --- | --- |
| Setup | 9.746344290964771s | 9.532483455986949s |
| Call | 64.22242653905414s | 54.69313599803718s |
| Teardown | 0.0009787080343812704s | 0.0009716250642668456s |

These are elapsed phase rows, not CPU or additive whole-suite savings. Both
arms emitted the same Starlette/httpx TestClient deprecation warning.

Wall includes Popen through real terminal exit and immediate known-owned-group
settlement: uv/Python startup, pytest imports/collection/setup/call/teardown/
reporting, same-child provenance writing/serialization and shutdown. Source
cloning, parent guards, separate standalone collection and final removal of
test/control temporary trees are outside the timer. Collection may warm import
and filesystem caches. Known-participant coordination did not prove global
host silence or matched performance isolation. One baseline-then-candidate
pair retains order/host noise and supports no statistical, whole-suite,
default-two-worker or 85-percent extrapolation.

All four collection/measured child records prove fixed QA Python 3.12.13,
shared dependencies, Node 24.18.0, identical host and intended source paths for
pytest, handoff/authority, owner, both seed helpers, image/controller fixtures
and timing plugin. All 12 owned command groups were absent; the exact registered
root `kfienfl0` was removed (device 16777232, inode 152321447). Source, environment,
tools, cache, protected evidence and local/public review ref `260a22d0` matched
before/after. Prior189 plus the actual22 v2 files total211 preserved artifacts;
historical CLI per-case cleanup receipt loss remains **UNAVAILABLE**, not repaired.

The accepted result (retired local artifact)
has SHA `ffe2835e2b146ce177ce9bf68f3c7ecc86ec3e38c612ba80d76a302684b2a53a`;
its hash map verifies all 16 raw artifacts. Before/after measured logs have SHAs
`be3f22b32332188bfb8850376f2a50e663e1f7d901d2fdbb1f33743439866889` /
`3b43e5e0d6033854545e1020e7e0e709f300df379329605e5cf3a0bb16cd23aa`.
Sealed plan SHA is
`943b1ac080f413d8d3113d18e60a1743c107d8de920c262343e83c28616cd482`;
observer SHA is
`af8e5fdc5866f60535307fc65b0371e5e6f0c020ee9fa7a6a461e0b298323dff`;
START SHA is
`80b9a22bc7d9e56d11b6be6a081458602360c371390a22b9fb9503d8cdbe64ee`.

## Fixed-QA interpreter-derived pin lesson

The failure belonged to evidence generation, not product/test bytes. Shell
Python was CommandLineTools 3.9.6; qualified QA Python was 3.12.13. Python 3.12
adds `type_params` to FunctionDef serialization. Root diagnostics `d01a7b` and
`712552` reproduced both wrong 3.9 pins from unchanged bytes; the first static
review used the same wrong producer and therefore did not independently detect
the mismatch. The correction restores the existing fixed-QA contract; it does
not introduce a new production/workflow contract requiring another ADR.

Generate and validate interpreter-sensitive AST pins under the exact qualified
physical interpreter, full version and binary hash. For this observation:
`/Users/wjmao/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3.12`,
version `3.12.13 (main, Jun 23 2026, 15:44:24) [Clang 22.1.3 ]`, binary SHA
`7b05d803bbc1bbfc81644af4faf2b88f0a37b8de96b9f42c1e08033e2cd0848a`.

Named evidence contract `fixed-qa-test-ast-v1`: parse exact bytes; retain
source-ordered top-level FunctionDef nodes named `test_*`; dump complete nodes
with `ast.dump(node, include_attributes=False)`; hash UTF-8 canonical JSON using
`sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`. Never strip
fields, normalize versions, accept alternate hashes or weaken comparison.

One shared serializer validates both exact revision Git objects before START
or cloning and then validates each clone. Fixed runtime identity checks precede
that pre-START validation. Exact pins, wrong pin/producer refusal, retained
type_params and ordering were checked with fixed-QA extracted stdlib helpers,
without full observer execution during preparation. Correct before/after pins:
`9728b952225e96d6f2e246df6a02d96bd8fd879d5750a9c77f87ab628d28df8f` /
`211bd8a16c1fd3b1572fe49239fa3c9bbbfbade200ba0da790a3e7320204db04`.

The successful v2 observation does not relabel the first allocation. Source
publication, current whole/full qualification, hosted CI and product acceptance
remain separate and unestablished for this fixture checkpoint. Default Python
concurrency remains two; the original whole-suite target stays open.
