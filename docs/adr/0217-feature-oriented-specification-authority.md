# ADR 0217: Feature-oriented current specifications and decision history

Status: documentation organization approved by the owner, 2026-10-22.
Application changes and resolution of disputed product intent are not approved.

## Problem

Current requirements are distributed across implementation plans, amendments,
manuals and decision records. A reader can mistake historical qualification for
current intent, or use current code to erase an agreed requirement. Splitting
every cross-layer decision into independent product/technical/architecture logs
would introduce competing authority at the same seam.

## Decision

Use `docs/specs/README.md` as the feature-oriented discovery entrypoint. Separate
current product/UX requirements, engineering contracts and architecture views;
link one decision history, delivery scope and dated execution evidence separately.
Consolidated clauses retain their originating decision/approval chain and
existing C/P/E acceptance identities. Clear later scoped decisions supersede only
the clauses they actually replace. Unknown status or conflicting intent remains
explicit and is referred to the owner, not inferred from implementation.

The workbench baseline is the first consolidated current-spec view. Other domains
initially retain their existing contract owners, discoverable through the map
and complete ADR catalogue. Discovery does not promote proposed/candidate records
or certify every domain's behavior. Source schemas own executable representation;
current implementation does not authorize a product-design change.

Maintain each requirement in its owning spec; manuals summarize operation,
ADRs retain rationale/history, roadmap records approved work, and verification
records actual evidence. Update affected links/clauses together when a new
decision is approved. Preserve historical files and IDs; do not mass-renumber,
rewrite old receipts, create three decision logs or move workflow-local assets.
Chat-origin agreements retain a direct human approval reference and enough
proposal context to establish scope. An assistant proposal, prototype interaction
or forwarded worker report cannot substitute for that decision. Later explicit
approval/status must be reconciled with detailed owners before indexing it.

## Alternatives, consequences and guardrails

A single giant specification would mix lifecycle/status and be hard to maintain.
Three disconnected folder trees would hide cross-layer requirements. A catalogue
without consolidated workbench clauses would still require reconstructing intent.
The chosen map keeps discovery central and owners local, with a bounded initial
consolidation. Every audit finding names requirement, actual evidence, severity,
confidence and verification limit. Conflicts and unexercised states are not FAILs
or PASSes by inference. Check catalogue coverage, relative links, provenance and
documentation-only diff; report findings before proposing executable changes.
