# Checked Python validator runtime · 2026-10-14

## Scope and revisions

The owner-approved isolated runtime repair implements ADR 0169. The source
candidate is `e24cb80ec313929a9a6bf768028d462271843755`; the test-ownership
follow-up is `7685a868ac6cdb208b137451cf9aae7872fadd43`.
The follow-up changes six test/fixture files only. Production validator,
resource, profile, environment, prompt, dependency and tool inputs are unchanged,
so the native evidence remains bound to the original source candidate.

The original failure was a disagreement between the Python import parent,
environment aliases and filesystem grant. The repair explicitly provisions one
physical copied environment outside attempts, checks its lock/configuration,
interpreter, dependency and versioned-runtime identities, and grants the
validated `src` parent only to Python plans. Readiness and execution refuse
missing or changed setup. An empty host-owned regular file prevents bytecode
lookup from following a model-writable cache directory.

## Native preflight

The single allocated provider-free preflight passed **all eleven** production
validation plans, each with its exact validate/render pair: Outline, Branches,
Cast preset/saved Brief, Art preset/saved Brief, Script, Storyboard
upstream/saved Brief, Intent and Presentation. It used production package pins,
resource/environment builders and sandbox commands. It did not admit a job or
dispatch a model. Deterministic source examples and test-owned candidates were
used; no successful host adoption or creative acceptance is claimed.

All **29 commands** passed: 22 validator/renderer steps, one runtime/import
control and six denial controls. The import control verified the copied
environment, physical base runtime, copied Pydantic dependencies and pinned
Plotloom source. Valid malicious bytecode seeded in the old writable cache was
not imported. Original `.venv` metadata and the intermediate uv alias remained
denied; Python and Node both denied synthetic sibling and auth-file reads.
Real credential contents and valued sibling-project data were not accessed.

Every process group was absent after completion. Package and candidate hashes
were unchanged; each delivery contained exactly its candidate and HTML report.
Final profile/runtime identity checks passed. Stdout, stderr, process identities,
exact argv/configuration, profile and input hashes were saved in the retained
root below before/after launch as appropriate.

| Identity | Value |
| --- | --- |
| CLI | `codex-cli 0.162.0-alpha.17.2` |
| CLI SHA-256 | `0d5ac7aae20c4eda6242428d5e218c55ba96d8763fda2a271088ff37104b9d28` |
| Contract / permission | `plotloom.codex-exec.v7` / `plotloom_autopilot_delivery_v5` |
| Runtime profile | `node_openssl_private_zsh_tmp_and_checked_python_v3` |
| Profile hash | `8a1c15c689975afb63447f291fd9b407c070c5bccd53681786056c44b02f2891` |
| Validator hash | `e30480364ceabd369b1bb762f0a85399ca4516b4c910ce1c3f03a5ef07281cc6` |
| Checked environment identity | `02149676aaa4d2a28ec98b66bd6160f4890be1e9487a3122aa30007ab7e4b2d7` |
| Script SHA-256 | `c129e99c3e369657957ee96bff985f4b916c25d9e402dbf466846bca41ec9330` |
| Plan SHA-256 | `620bc3742bf62e7a98233a316d8865ee12fbdd97f073ad354808519eac974acf` |
| Result SHA-256 | `de764b13391cb0efb631eeabf635f0c586d0289119084e1824740bedbb0c4ce8` |

Retained local evidence:
`.local/native-proof/checked-python-runtime-v7-20261014/` contains `plan.json`,
`result.json`, the exact script/helper snapshots, per-command results/logs,
frozen packages and report trees. The script entrypoint is the original
`.local/checked_python_native_preflight.py`; its bytes match the saved snapshot.
An initial invocation of the relocated snapshot failed to import the service
before entering the harness or launching any sandbox child. The corrected
entrypoint consumed the one-shot launch marker exactly once; no native command
was replayed. Earlier provisioning failures and root07 evidence are retained
unchanged, including root07's failed import and unexecuted Branches pair.

The manager independently reviewed the complete script, all expanded argv and
139 retained artifacts, and accepted this bounded native gate at `e24cb80e`.
That acceptance does not qualify generation, pool behavior or live activation.

## Focused checks and independent review

The stable source candidate and the later test-ownership repair each received
an independent read-only review with no blockers. Requested reviewer selection:
GPT-6.1 Sol / High; effective provider settings were not confirmed.

The manager found that resource/supervisor tests initially depended on ignored
host setup. The owning fixture now creates uniquely allocated temporary source
and submodule copies with synthetic physical runtime metadata. Production
snapshot/inspection/resource/profile code remains exercised; the fixture
interpreter responds only to `--version` and refuses validation execution.
The bytecode regression uses the current test interpreter explicitly. Actual
copied-runtime execution is established separately by the native gate above.

A fresh checkout of `7685a868`, with the checked-runtime receipt absent before
and after testing, used ordinary `uv sync --locked --offline --link-mode copy`
dependency setup. It passed:

- `verify.py focused`: resources, profile, Python-environment and supervisor
  environment test modules — **34 passed**.
- Explicit service pytest selection: `test_bridge.py`,
  `test_codex_exec_supervisor.py`, `test_codex_exec_supervisor_ledger.py` —
  **49 passed**.
- `verify.py focused`: auth, contracts, validation, receipts and delivery test
  modules — **75 passed**.

Exact commands/logs are retained in `fresh-focused.log`, `fresh-service.log`,
`fresh-contracts.log`
and `fresh-verification.json` under the same evidence root. Scoped Ruff I/F and
`git diff --check` passed. No frontend files or generated assets changed.

## Handoff boundary

This completes the isolated runtime repair and bounded native gate. No provider
generation, pool qualification, full release gate, hosted CI, activation,
merge/push or global settings change was authorized or performed in this window.
The paused canary and unknown art run retain their original state and evidence.
The worker returns the committed checkpoint and releases the source/check
window; the manager owns subsequent Python work, integration and any separately
allocated native-generation proof.
