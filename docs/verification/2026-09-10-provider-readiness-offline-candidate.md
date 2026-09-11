# Provider-readiness candidate verification

Date: 2026-09-10

## Outcome

This candidate separates Plotloom service reachability from the selected text
backend's readiness. New pipeline, rebuild, and exact-repair admissions obtain
a V3 frozen snapshot with a trusted adapter ID/version, then reject only a
definite non-generative preflight failure. V1/V2 snapshots retain their
historical hash and resolver paths.

Readiness observations are application-memory-only, profile/revision scoped,
timestamped, and secret-free. They are cleared after a material profile or
availability edit and return as `unverified` after restart. The workbench shows
the service plane separately from backend state, profile, reason, observed time,
and remediation.

Migration `0012_text_profile_adapter_selection` stores adapter ID/version as
profile control-plane fields outside historical V2 settings JSON. Profile
create, copy, update, get, and list paths preserve that selection; the UI binds
it to a selector limited to the server-published trusted registry. New V3 runs
freeze the selected entry, and neither endpoint nor model labels select adapter
code.

## Automated evidence

- Focused provider/API/regression suite — 59 passed.
- Unfiltered `uv run pytest -q` — 524 passed, 9 skipped. No test was deselected
  or waived.
- `npm --prefix frontend test -- --run` — 115 passed.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build` — passed; generated workbench assets were
  refreshed.
- `npm --prefix frontend run test:e2e` — 23 passed against real FastAPI and the
  external OpenAI-compatible fake-provider fixture. Coverage includes the
  persisted adapter selector, session-only key handling, disabled admission,
  project lifecycle, canonical editing, and exact repair.
- `uv build --wheel` — built `plotloom-0.1.0-py3-none-any.whl`.
- `uv run python scripts/smoke_installed_wheel.py dist` — passed from an
  isolated installed-wheel environment.

## Retained visual evidence

The 1440×900 disconnected baseline is retained at
[`assets/provider-readiness-disconnected-1440x900.png`](assets/provider-readiness-disconnected-1440x900.png).
Its SHA-256 is
`99904bbcbc40b4e0edcced28080778dbeb81b60469107638c881497fae69c754`.

Visual inspection confirmed all three workbench columns and the intended plane
separation: `Plotloom 服务：已连接` is green while `文本后端：unreachable ·
default · readiness.transport_unreachable` is red. This directly guards the
misleading connected badge that triggered the change.

## Bounded live readiness evidence

After the operator restored the default llama-server, one non-generative probe
was run from an isolated temporary Plotloom data directory. It passed on the
first request:

- profile: `default`, revision 0;
- adapter: `openai_compatible` version `1`;
- configured model alias: `qwen3527b`;
- state: `available`;
- reason: `readiness.models_verified`.

The probe used the adapter's model-list check and did not submit a completion,
create a project, or retain endpoint, IP, key, prompt, or response content. The
server was stopped and its disposable data moved to Trash immediately after the
check. A new generative trial was deliberately not started: the previous canary
already established generation, while this checkpoint changes preflight,
admission, and adapter identity. The next user trial remains a separate gate.

## Secret boundary

The candidate persists only public profile configuration, adapter identity, and
safe readiness state/reason/time. Browser and server credentials are leased only
for probe or dispatch and are never included in a profile, frozen snapshot
observation, trace, log, UI response, screenshot, or this ledger. The retained
PNG contains no provider endpoint, IP, authorization label, or key material.

## Review corrections

Independent review found and corrected three contract-level defects before this
receipt was finalized:

1. Exact repair had preflighted mutable profile configuration instead of the
   source run's frozen snapshot.
2. Unsupported model-list responses had been treated as terminal instead of
   remaining `unverified`.
3. Migration `0012` persisted adapter identity, but profile writes and the UI
   still assumed the registry's first entry. CRUD and UI now round-trip the
   selected trusted entry, reject unsupported selections before mutation, and
   invalidate readiness through the profile revision boundary.

The two previously exposed repository regressions (join repair-fact ordering and
the stale Alembic-head expectation) were also corrected; the unfiltered suite is
the acceptance authority above.

## Provenance limitation and remaining gates

The original Flow task's immutable write fence did not admit
`docs/verification`. The user explicitly authorized ordinary-Git, source-only
continuation after the Flow lifecycle defect was reported. This receipt records
the resulting repository evidence but does not claim retroactive Flow
compliance or close that external run.

The vLLM lane remains operator-deferred and was not contacted. No push, remote
merge, or Alpha qualification is claimed by this checkpoint.
