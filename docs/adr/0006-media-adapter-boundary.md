# ADR 0006: Shared media service and immutable media inputs

## Context

Plotloom was extracted into a repository containing no V1 runtime code. Media
generation still needs provider-specific request, submit, and polling behavior,
but importing a predecessor service would violate the product boundary and
obscure which immutable project revision produced an asset.

## Decision

- Implement media behavior through Plotloom-owned provider ports and adapters.
  Production code must not import a predecessor media service or provider
  registry.
- Compile image and video prompts deterministically from a frozen Plotloom shot
  snapshot. User prompt overrides are separate authored values.
- A `MediaTask` records the storyboard revision, compiled prompt components,
  enqueue-time public provider options, provider task ID, lifecycle timestamps,
  terminal error, and output URI. Adapter code is versioned with the application;
  a later asset-ingest milestone may copy remote output into the content-addressed
  artifact store. A task never stores an API key.
- Synchronous image results and asynchronous submit/poll protocols share one
  bounded local worker. Session overrides take precedence over server keys and
  are erased at every terminal or submission-failure boundary.
- Startup reconciliation resubmits only pristine queued media tasks. A running
  task with a durable provider task ID resumes polling without another submit;
  a running task without an ID is failed because its submission outcome is
  ambiguous and repeating it could duplicate work or billing. Browser-session
  keys do not survive restart, so resumed polling uses a server key or fails
  safely when no key is configured.

## Consequences and guardrails

The first Plotloom slice exposes single-shot image and video tasks only. Batch queues,
durable local media ingestion, playable export, and final editing remain later
milestones. Plotloom's provider, media-job, dependency-boundary, distribution,
and browser tests are release gates. Historical parity evidence may explain an
adopted behavior, but it cannot become a production dependency.
