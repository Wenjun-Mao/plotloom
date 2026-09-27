# ADR 0093: Observed Voice Lab queue and generation progress

**Status:** Implemented in the specialist Voice Lab, 2026-09-27.

## Context

The single Voice Lab worker already serializes voice-design and clone jobs, but
the browser showed only `queued` or `running`. Authors could not tell whether
a request was behind other work or which part of a running job had been reached.
Qwen3-TTS does not expose a trustworthy completion percentage for this path.

## Decision

- `GET /api/generations/{generationId}/progress` reports the persisted status
  alongside a live, read-only projection of the in-process serial queue.
  `queueAhead` counts **both** voice-design and clone jobs ahead of a queued
  generation. An admission that has not yet entered the queue reports `null`,
  not a guessed position.
- The worker exposes only observed phases: starting, loading the model,
  synthesizing, preparing audio, and finalizing. Elapsed time starts at worker
  dispatch and is measured with a monotonic clock. Neither phase nor elapsed
  time promises an ETA or a percentage. Terminal results remain authoritative
  in SQLite; a restart marks unfinished jobs interrupted without replay.
- The browser polls the lightweight progress projection while the project has
  active work and updates the existing candidate card without replacing its
  text editor or audio control on every phase change.
- Field captions are ordinary selectable text, associated with inputs through
  `aria-labelledby` instead of wrapping `<label>` elements whose click-to-focus
  action interfered with drag selection.

## Alternatives and consequences

An inferred percentage based on typical runtime would misrepresent slow model
loading or generation variance. Persisting ephemeral phase/queue rank would
add false precision and migration burden; after restart there is no active
worker state to restore. The current projection is intentionally specific to
the one-worker service. If multiple workers are ever introduced, queue
ownership and the projection contract must change together.
