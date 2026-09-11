# ADR 0028: Agent-operated image jobs and manual delivery

## Status

Direction accepted by the user, 2026-09-11. Not implemented. The
[P1 revision 2 plan](../roadmap/p1-image-generation-plan.md) is Approved for
implementation. Current runtime media hard stops remain until its guarded path
is implemented and verified.

## Context

The user wants Codex's built-in image generation for development and potentially
as a durable backend. Requiring an HTTP image API or automatic Codex bridge would
postpone useful creative work. Informal image imports alone cannot establish
which frozen approved request the specialist fulfilled.

## Decision

Use **Prepare → Copy assignment → Generate → Refresh → Select** for initial P1.
Plotloom owns admitted ProductionSnapshots and immutable job packages; the
specialist owns generation/delivery; Plotloom validates and ingests the output;
the creator/director explicitly reviews selection.

An opaque ID resolves through a configured exchange location. It is not a secret,
standalone instruction or proof of execution. Initial scope is same-host exchange
with confined per-job input/output directories, not arbitrary server-path access
or assumed sharing of absolute paths between machines.

Versioned delivery manifests bind requests to completed files and available tool
evidence. Publish completion before atomic/idempotent ingestion. Returned files
and metadata are untrusted; hashes establish byte consistency, not model authenticity.
Preserve originals, actual tool prompts, refinement lineage and disclosed limitations.

Export is the manual authorization cutoff. Already copied packages cannot reliably
be recalled; cancellation/staleness limits applicability and selection, not remote
execution. Refresh does not generate, approve, select or rewrite history. Silent
jobs remain awaiting delivery rather than being labelled failed.

This extends ADR 0026's production boundary to an agent-operated backend while
retaining ADR 0012/0016 frozen-input and Approval requirements. P0 previews are not
relabelled as ProductionSnapshots. Ad-hoc images keep import provenance; actual
job-linked specialist outputs use the new lineage. Future automation preserves
the same request/delivery/selection contract.

## Alternatives and consequences

- Automatic bridge first: deferred; unnecessary for P1 and built-in image access
  through the intended bridge remains unverified.
- External image API first: not the chosen route. No silent API/CLI fallback,
  new key requirement or separate billing.
- Image files alone: rejected; insufficient request/refinement identity, completion
  markers and idempotent reconciliation.
- Conversation history as the backend database: rejected; portable jobs and visual
  decisions allow replacement tasks without losing continuity or growing context.

Manual handoff offers neither unattended-service nor remote-cancellation guarantees.
Cross-machine transfer/automatic triggers are future transport work, not hidden P1
requirements. Built-in generation consumes account usage and is not unlimited.
Verify real generate/refine/return behavior before claiming this backend works.
