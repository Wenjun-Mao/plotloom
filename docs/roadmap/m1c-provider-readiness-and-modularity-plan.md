# M1-C provider readiness and modularity plan

Status: **Approved**  
Approved: 2026-09-10  
Source baseline: `05518ee` on `codex/m1b-alpha`, clean when inspected

## Outcome

Continue building while the configured llama server is unavailable. Deliver a
provider-neutral connection and adapter boundary that:

- tells the user separately whether the Plotloom application service and the
  selected text backend are reachable;
- prevents a known-unreachable backend from creating a doomed pipeline run;
- selects a versioned text adapter explicitly instead of inferring behavior
  from a provider label, model alias, endpoint, or runtime brand;
- preserves all historical V1/V2 run snapshots, hashes, plans, seals, attempts,
  and evidence exactly;
- can be verified offline with controlled fake backends; and
- is ready for one bounded live retry when the llama server returns.

Before delivery begins, settle and archive the previous Flow coordinator and
any prior executor tasks that are safe to archive. Start the implementation
with one fresh coordinator under Codex Orchestration v0.9.12; do not reuse or
refresh an old coordinator.

This plan advances the remaining modularity work in ADR 0024. It does not claim
that the `default` backend is currently reachable or formally qualified.

## Current diagnosis and evidence

The latest user-created project reached project revision 1, then failed its
first Story Bible unit with `provider.request_not_sent` after the connection
attempt timed out. The request was not submitted, no provider content was
received, and no canonical stage was partially installed. A direct reachability
check to the configured endpoint also timed out.

The visible `API 已连接` indicator remained positive because it represented the
browser's connection to Plotloom's FastAPI service, not the text-model backend.
The immediate failure is therefore a remote-service availability event; the
misleading product behavior is a status-semantics defect. The durable fix
belongs in the service-health and provider-adapter contracts, not in prompts,
validators, automatic retries, or a model-specific exception.

The earlier retained `default` canary remains valid historical evidence at
`05518ee`: one complete four-stage storyboard installed atomically and an edit
survived refresh. Its local data and evidence must not be modified by this work.

## Scope

### 0. Orchestration cleanup and fresh ownership

Use only the installed Codex Orchestration v0.9.12 package for new lifecycle
operations. The known predecessor is:

- assignment `coordinator-assignment-v1-d72eb7433ad18ba78806c20ec1c7337b92d8cd869e235ed344b3c94cb8c53174`;
- run `m1c-usable-storyboard-canary-01a08240`;
- coordinator task `01a08240-154a-7691-9e10-fe85f05449f4`;
- accepted report `report-record-v1-72fbd567a80a748717b8e9040c801e2148834e5acadca4117e9712aeda9f7e54`;
- real idle coordinator checkout `/Users/wjmao/.codex/worktrees/db15/plotloom`.

Its assignment is accepted and its coordinator task is idle, but the iteration
is still open and records the primary checkout as the coordinator worktree.
The legacy run is not a v0.9 run, so the generic v0.9 cleanup planner does not
own it. Resume its exact accepted-assignment closeout with the v0.9.12
assignment lifecycle, then reconcile the resulting archive operation through
the Codex app. Do not edit registry JSON, reconstruct iteration membership,
remove a git worktree manually, or delete a branch.

Inventory other Plotloom coordinator/executor tasks by exact task ID, authority,
activity, checkout, and integration state. Archive only tasks that are idle or
terminal and have no unintegrated result. Preserve the current director task.
If any task's identity or result ownership is ambiguous, leave that task
unarchived and report the exact ambiguity.

After cleanup reaches a settled state, create one fresh coordinator from the
approved plan and the verified current Plotloom baseline. It owns integration
and verification. It should work directly by default; it may create at most two
small, independent executor tasks when parallelism has a concrete latency
benefit. GPT-5.6-Terra is the default for those tasks. GPT-5.6-Sol requires a
specific recorded reason.

### 1. Separate application health from backend readiness

Replace the overloaded connection indicator with two explicit concepts:

- **Plotloom service**: browser-to-application API connectivity and compatible
  application version;
- **Text backend**: readiness of the currently selected, enabled profile and
  its adapter.

The text-backend status contract must distinguish at least:

- `disabled`;
- `missing_configuration`;
- `unverified`;
- `checking`;
- `available`;
- `unreachable`;
- `authentication_failed`;
- `model_mismatch`;
- `capability_mismatch`.

Display the selected profile, last observation time, and a stable reason code.
Never label a backend connected merely because a profile exists, an API key is
available, or the Plotloom service answered. Administrative enable/disable,
observed runtime readiness, and pipeline outcome remain three separate states.

Runtime observations are ephemeral server-owned state. They are secret-free,
profile-scoped, invalidated when material profile settings change, and reset to
`unverified` after an application restart. They do not change a profile's
configuration revision or become qualification evidence by themselves.

An explicit user probe updates the observation. A definite transport,
authentication, model, or capability failure encountered during generation
also updates it. A successful response may update readiness only when it proves
the adapter's declared minimum contract.

### 2. Versioned adapter registry and new-run snapshot

Implement the trusted internal registry described by ADR 0024. A profile for a
new run selects a stable `adapterId` and `adapterVersion`; the first registered
adapter wraps the existing OpenAI-compatible transport used by llama-server and
vLLM. Adapter selection must never depend on a model alias, endpoint heuristic,
or vendor/provider display name. Unknown adapter IDs or unsupported versions
fail before dispatch with stable errors.

The adapter owns protocol translation and optional non-generative readiness
checks. The core continues to own topology, prompts, schemas, extraction,
binding, validation, correction limits, attempts, seals, atomic installation,
and Approval. An adapter cannot weaken these contracts or add hidden retries.

Add a new provider snapshot schema version for newly admitted runs that freezes
adapter identity with the existing public execution configuration. Preserve
exact V1/V2 decoding, serialization, hashes, resolver behavior, plans, and seals.
Do not backfill new fields into historical JSON or re-hash old evidence.

Profile APIs and UI expose adapter selection only from the trusted registry.
Existing profiles migrate to the explicit OpenAI-compatible adapter without
changing their settings revision or historical snapshots. Profile-scoped
session secrets keep their current precedence and isolation. `authMode=none`
must not resolve a key or send an Authorization header.

### 3. Readiness admission policy

The OpenAI-compatible adapter may use a cheap, non-generative model-list or
equivalent protocol check when the endpoint supports it. A runtime-specific
diagnostic such as llama-server slot state remains optional supplementary
evidence and cannot become a universal provider requirement.

Before admitting a new pipeline, rebuild, or repair run, perform the cheapest
safe adapter readiness check when that adapter supports one:

- a definite `unreachable`, authentication, model, or capability result rejects
  admission without creating a failed pipeline run;
- an adapter that cannot implement a cheap check remains `unverified` and may
  proceed to normal generation;
- no readiness path sends a creative completion merely to light a status badge;
- no automatic retry or silent profile fallback is introduced;
- a request with unknown submission outcome is never replayed automatically.

Return a stable, actionable admission error and show: “Plotloom service is
connected; the selected text backend is unreachable” for the observed case.
The user can re-probe or retry explicitly after the remote service returns.

### 4. Offline verification and browser behavior

Build controlled adapter/fake-server tests for:

- reachable OpenAI-compatible service and expected model;
- refused connection, timeout, and DNS/route failure;
- authentication rejection;
- expected-model absence;
- disabled and incomplete profiles;
- adapters with no cheap readiness capability;
- readiness invalidation after settings changes;
- application restart resetting observations to `unverified`;
- `authMode=none` and profile-scoped session-secret isolation;
- generation transport failure updating readiness without changing the run's
  immutable outcome evidence;
- unknown adapter ID/version refusal;
- byte/hash-equivalent V1/V2 snapshots and new-version isolation.

Add browser coverage proving that the Plotloom service can remain connected
while the text backend is unavailable, that the labels and remediation are
unambiguous, and that a definite preflight failure creates no pipeline run.
Capture a 1440×900 baseline screenshot for the disconnected state.

Do not require either remote model host for this checkpoint. Use the smallest
relevant tests first, then the established complete local verification on the
stable candidate:

```sh
uv run pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --exit-code -- src/plotloom/static
npm --prefix frontend run test:e2e
uv build --wheel
```

Run the repository's installed-wheel smoke test using its documented command.
Record exact commands, results, candidate commit, and any skipped external gate.

### 5. Deferred live gate

When the operator confirms the llama service is back:

1. probe the `default` profile and verify the expected public endpoint/model
   identity without exposing its key;
2. confirm the UI changes from `unreachable` or `unverified` to `available`;
3. explicitly retry the user's saved `test001` project once, because the prior
   request is proven `provider.request_not_sent`;
4. verify four-stage atomic installation, bounded attempts, refresh persistence,
   and the visible storyboard, or retain the exact new terminal failure;
5. update the capability matrix and plan status with evidence.

This live retry is not the nine-run single-backend Alpha qualification. Formal
qualification remains a later checkpoint after the adapter candidate is frozen
and the remote service is stable. The deferred vLLM profile is not contacted or
deleted in this plan.

## Non-goals

- no dynamic third-party plugin/package loader or marketplace;
- no model-, alias-, runtime-, IP-, or vendor-specific generation behavior;
- no prompt, schema, binder, validator, topology, or creative-quality tuning;
- no image/video production, deployment authentication, reverse proxy, or
  forced HTTPS work;
- no periodic retry loop, automatic failover, or silent profile selection;
- no live vLLM work and no formal nine-run qualification;
- no modification of `.env`, user-level `AGENTS.md`, retained canary data,
  playground data, or external output files;
- no merge, push, force push, or remote branch deletion during implementation
  unless separately authorized after local acceptance.

## Consequential decisions

1. **Health has two planes.** Plotloom service connectivity and selected text
   backend readiness are reported independently.
2. **Availability is not readiness.** Enabled/disabled is operator intent;
   readiness is a timestamped runtime observation; run outcomes remain immutable
   execution evidence.
3. **Adapters are internal and explicit.** A trusted registry chooses a tested
   protocol adapter by stable ID/version. Models and endpoints do not select
   code paths implicitly.
4. **Cheap checks are optional.** A supported non-generative preflight may block
   a definitely doomed admission. Lack of such a capability yields `unverified`,
   not a fabricated failure.
5. **Historical authority is frozen.** Only new runs receive the new snapshot
   schema. V1/V2 content and hashes are never normalized to current defaults.
6. **Cleanup precedes new ownership.** Old accepted work is settled and archived
   through Flow/App lifecycle operations; a new coordinator then starts from a
   clean, verified source baseline.
7. **Offline evidence precedes the remote gate.** The host outage does not block
   contract, UI, adapter, migration, or failure-path verification. It does block
   a new live-success claim.

The implementation must record these decisions in a concise new ADR or a
focused amendment to ADR 0024 before changing the public/runtime contracts.

## Checkpoints and stopping points

| Checkpoint | Observable result | Stop condition |
|---|---|---|
| 0. Cleanup | Exact prior tasks and assignment are settled or named as unresolved; eligible old coordinator/executors are archived | Any operation would require manual Flow-state/worktree manipulation or ownership is ambiguous |
| 1. Contract | ADR and tests define the two health planes, readiness states, admission behavior, and historical boundary | The proposal requires provider-specific core behavior or a generative health check |
| 2. Adapter | Registry, OpenAI-compatible adapter, profile migration, and new-run snapshot work offline | V1/V2 bytes/hashes change, secrets cross profiles, or old runs change resolver behavior |
| 3. Product UX | UI reports app and backend independently; definite preflight failures create no run | The UI still infers readiness from saved configuration or hides stable reason codes |
| 4. Candidate | Focused and complete local suites pass; static bundle and wheel are verified | A failure reveals a broader prompt/domain redesign or leaves generated artifacts inconsistent |
| 5. Live gate | One explicit `default` retry succeeds and persists, or a new bounded failure is retained | Provider is unavailable, outcome is unknown, identity changed materially, or the same failure class repeats |

Each checkpoint should end with one bounded local commit. Review once at the
stable combined candidate, not after every small edit. A failed checkpoint is
reported with its root cause and cheapest next experiment; it does not authorize
an open-ended diagnostic or retry cycle.

## Acceptance evidence

Completion requires:

- Flow/App receipts listing the exact prior task IDs and final archive or
  retained disposition, with no manual registry/worktree deletion;
- one fresh coordinator identity bound to the approved plan and verified source;
- the ADR and public status/adapter contracts;
- focused migration, adapter, admission, secret-boundary, and historical-hash
  tests;
- Playwright evidence of simultaneous “Plotloom connected / backend
  unreachable” state and zero run creation after definite preflight failure;
- a clean, reproducible production bundle and installed-wheel smoke result;
- secret scanning of tracked fixtures, screenshots metadata, and receipts;
- one exact clean candidate commit and concise verification ledger;
- when the server returns, the probe and one bounded live retry result.

The offline portion may be accepted while the live gate is explicitly pending.
Neither that state nor the earlier one-run canary may be described as formal
backend qualification.

## Execution authority

After this plan is approved, the fresh coordinator may:

- edit Plotloom source, tests, ADRs, roadmap files, and generated static assets
  within this scope;
- use temporary local databases, artifact directories, fake servers, browsers,
  and local processes it creates;
- create bounded local commits and integrate verified executor results;
- use v0.9.12 Flow/App lifecycle operations to archive exact eligible prior
  coordinator/executor tasks;
- probe and call the configured `default` backend only after the operator says
  it is available, using the existing secret path without printing the key.

It may not modify user-level instructions, external repositories, retained
canary/playground evidence, remote model deployments, secrets, or remote git
state. It may not loosen generation contracts, add a model exception, replay an
unknown request, or expand to formal qualification without a new approval.

The director retains plan acceptance, material-scope decisions, final result
acceptance, merge/push authority, and any decision to advertise a backend as
qualified.

## Escalation conditions

Return to the director before continuing if:

- v0.9.12 cannot lawfully close/archive the v0.9.8 assignment because of its
  recorded worktree mismatch;
- an old task may contain unintegrated changes or cannot be bound to an exact
  authority;
- fresh assignment preparation is blocked by unsettled predecessor state;
- the adapter boundary requires rewriting historical snapshots or hashes;
- a readiness check would need a creative completion or provider-specific core
  exception;
- a secret appears in API output, logs, fixtures, screenshots, artifacts, or
  receipts;
- the implementation requires prompt/domain changes, deployment work, live
  vLLM access, or formal qualification;
- the live request has unknown submission outcome or the configured deployment
  identity changes materially.

## Relationship to existing plans

This plan supersedes only the pending adapter/readiness portion of checkpoint
2E in [M1-C completion plan](m1c-completion-plan.md). It does not supersede the
accepted canary result, ADR 0024's independent-qualification policy, or later
M1-C candidate, qualification, and delivery gates.
