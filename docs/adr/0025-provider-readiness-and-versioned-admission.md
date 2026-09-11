# ADR 0025: Provider readiness and versioned admission

## Status

Accepted 2026-09-10. This is a focused implementation amendment to ADR 0024.

## Context

The workbench's API-connected indicator reports browser-to-Plotloom service
connectivity. It cannot establish that the selected text backend is reachable.
The observed outage therefore created a doomed run even though the application
was healthy. A saved profile, an enabled switch, and an available secret are
also configuration facts, not runtime readiness evidence.

## Decision

- The service-health plane and the selected text-backend readiness plane are
  independent. Backend observations are server-memory, secret-free,
  profile-scoped, timestamped records. They are invalidated by material profile
  edits and start as `unverified` on every application restart.
- `disabled`, `missing_configuration`, `unverified`, `checking`, `available`,
  `unreachable`, `authentication_failed`, `model_mismatch`, and
  `capability_mismatch` are stable readiness states. State details are an
  actionable, stable reason code; URL, credential, and response details are
  never returned or persisted as observation evidence.
- A trusted internal registry resolves a new-run adapter by exact
  `adapterId`/`adapterVersion`. The first entry is the versioned
  OpenAI-compatible protocol adapter. Model names, endpoint shapes, IPs,
  runtime brands, and display labels never select adapter code.
- The current registry has exactly one approved entry. Profile APIs publish it
  and the settings UI names the selected immutable entry beside the provider
  field; it is intentionally not editable until a future migration introduces
  a persisted profile adapter-selection field. Endpoint and model inputs can
  never substitute for that registry selection.
- New admissions receive a V3 provider snapshot which freezes that exact
  adapter selection. V1 and V2 snapshot bytes, hashes, serialization and
  resolver behavior remain historical authority; they are neither migrated nor
  re-hashed. Existing mutable profile records may gain the default registry
  selection without a configuration-revision bump.
- Before a new pipeline, rebuild, or repair is persisted, an adapter may run
  its cheapest supported non-generative preflight. Only definite transport,
  authentication, model, or declared-capability failures reject admission.
  Unsupported checks remain `unverified` and may proceed. No health path sends
  a creative completion, retries automatically, falls back to another profile,
  or replays an unknown outcome.

## Consequences and guardrails

The UI names both planes, the selected profile, observation time, reason code,
and remediation. Generation failures may update an ephemeral observation but
never rewrite a run's immutable outcome evidence. `authMode=none` resolves no
key and emits no authorization header. Tests preserve historical snapshot
bytes/hashes and prove a definite preflight failure creates no run. The live
default-backend retry remains an operator-triggered, explicitly pending gate.

## Rejected alternatives

- Treating a saved profile or application API response as backend readiness.
- A provider/runtime-specific core exception or generative badge request.
- Rewriting V1/V2 snapshots to append registry fields.
- Automatic retry, profile fallback, or unbounded diagnostic polling.
