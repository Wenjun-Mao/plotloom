# 2026-09-02 local text-provider smoke receipt

## Scope

This receipt records one user-authorized, real text-provider run through the
Plotloom runtime. It does not record the provider URL, credentials, prompt
contents, response contents, or generated story text.

The run used a temporary SQLite database and artifact directory. Both were
deleted automatically when the test process exited, so the user's existing
Plotloom projects and provider configuration were not changed.

## Input profile

- Provider protocol: OpenAI-compatible Chat Completions.
- Provider-advertised model ID used for the run: `gemma4`.
- Auth mode: server-managed bearer lease; the credential was never printed or
  included in the run snapshot.
- Structured-output capabilities: native JSON object and JSON Schema disabled;
  Plotloom embedded the strict schema in each prompt and validated every
  response locally.
- Effective output ceiling: 4,096 tokens, frozen into the GenerationPlan.
- Execution concurrency: one work unit at a time.
- Story scale: one start node, one ending node, one scene and beat per node,
  and one shot per beat.

The checkout `.env` names
`gemma-4-26B-A4B-it-Q4_K_M.gguf`, while `/models` advertises only `gemma4`.
The smoke test selected the advertised ID in memory and did not edit `.env`.
This receipt therefore proves neither that the configured alias is stable nor
that the backing model is Qwen.

## Result

| Observation | Result |
|---|---:|
| Terminal run status | `succeeded` |
| Wall time | 127.4 seconds |
| Provider attempts | 6 |
| Durable work units | 6 |
| Sealed stage aggregates | 4 |
| Rejected validation reports | 0 |
| Installed stage heads | 4 `ready` |
| Generated characters / nodes / scenes / beats / shots | 1 / 2 / 2 / 2 / 2 |

The four stage aggregates were sealed in canonical order and installed only
after every requested stage succeeded. The run did not partially install any
stage while work was in progress.

## Finding fixed during the smoke

The first attempt failed before dispatch because a canonical ProviderSnapshot
stores capability keys in camelCase while the internal provider adapter model
accepts snake_case. The resolver now performs an explicit typed conversion at
that boundary, with a regression test. The failed attempt made zero provider
generation calls.

A later review found that non-HTTP repository callers could enqueue a partial
ProviderSnapshot and let the resolver fill missing fields from mutable runtime
defaults. ProviderSnapshot now resolves its required text provider, API root,
and model before hashing and enqueue; the resolver no longer has an execution-
time defaults path. A regression test mutates the caller's original mapping
after enqueue and verifies that dispatch still uses the frozen values.

## Evidence boundary and remaining gates

This is a local worktree receipt, not a release receipt: it is not yet bound to
a Git commit or remote CI run. It covers one minimal text-generation story via
the real runtime, but not a real-browser generation journey, exact work-unit
repair, larger/forking stories, image generation, video generation, creative
quality review, or repeatability statistics.
