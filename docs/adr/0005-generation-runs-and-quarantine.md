# ADR 0005: Versioned prompts, generation runs, and quarantine

## Context

Legacy generation does not retain the rendered prompt, raw model response,
validation report, template version, or installation mapping. When JSON is
malformed or semantically incomplete, users cannot determine what failed or
reproduce a repair.

## Decision

- Store prompt templates as versioned repository files with strict variable
  rendering and a declared input/output contract.
- Every generation run freezes its input snapshot, rendered messages, template
  ID/version/hash, provider/model settings, attempts, usage, raw response,
  validation report, and parent repair run.
- Prefer provider-native JSON Schema output when advertised by the adapter;
  otherwise use a strict JSON prompt and apply the identical local validators.
- Parse, schema-validate, and semantic-validate before installing a complete
  stage atomically. Invalid candidates are quarantined and never become a stage
  head.
- Manual repair and explicitly requested AI repair both create child runs. There
  is no hidden model retry for a semantically invalid successful response.
- Public provider settings are frozen when a run is enqueued. A queued worker
  never rereads mutable provider settings. API keys remain separate, ephemeral
  leases and are not part of the snapshot. The domain and repository enforce a
  single public-field allow-list and reject secret-shaped fields, values, and
  credential-bearing URLs even when callers bypass the HTTP API.
- A repair is allowed only for the stage of a durable failed model attempt with
  both raw-response and rejected-validation evidence. Its parent snapshot must
  still be current; otherwise the user starts a fresh rebuild from current
  canonical heads.
- Startup performs one durable reconciliation pass. Pristine queued runs are
  resubmitted, `cancel_requested` runs become cancelled, and previously running
  runs become failed with any open attempt closed. Generation calls are not
  automatically replayed because the previous provider side effect cannot be
  proven absent or idempotent.
- Enqueueing a repair freezes the exact failed-attempt, response-artifact,
  validation-artifact, and reusable candidate-artifact IDs. Execution resolves
  those IDs rather than searching for whichever artifacts happen to be latest;
  copied candidates retain a `sourceArtifactId` lineage link.

## Consequences and guardrails

Prompt traces are local project data and may contain story content, but they must
never contain provider secrets. A temporary UI key is represented only by an
in-memory secret lease; a restart can require the browser to provide it again.
Startup resubmission therefore falls back to a configured server key and fails
safely when none exists.
Tests cover trace completeness, repair lineage, quarantine, and secret absence.
They also cover enqueue-time provider snapshots, atomic multi-stage commit, and
rejection of repairs that could overwrite later manual edits or change their
evidence after enqueue.
