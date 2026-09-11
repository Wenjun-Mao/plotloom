# ADR 0028: Agent-operated image jobs and manual delivery

## Status

Implementation candidate under bounded verification; **director acceptance is
pending**, 2026-09-11. The [P1 revision 2 plan](../roadmap/p1-image-generation-plan.md)
remains the approved scope. P1 opens only this guarded manual Codex-job path;
legacy direct-provider media execution remains stopped. The initial source-bound
receipt is [2026-09-11 P1 Codex image jobs](../verification/2026-09-11-p1-codex-image-jobs.md),
with the copied-brief correction recorded separately.

## Context

The user wants Codex's built-in image generation for development and potentially
as a durable backend. Requiring an HTTP image API or automatic Codex bridge would
postpone useful creative work. Informal image imports alone cannot establish
which frozen approved request the specialist fulfilled.

## Decision

Use **Prepare → Copy assignment → Generate → Refresh → Select** for initial P1.
Plotloom owns admitted ProductionSnapshots and database-frozen job inputs; the
specialist owns generation/delivery; Plotloom validates and ingests the output;
the creator/director explicitly reviews selection.

An opaque ID resolves through a configured exchange location. It is not a secret,
standalone instruction or proof of execution. Initial scope is same-host exchange
with confined per-job input/output directories, not arbitrary server-path access
or assumed sharing of absolute paths between machines.

### P1 ownership contract (implementation amendment)

The author owns canonical storyboard facts, reviewed visual decisions, an
explicit Approval, and one explicit presentation/refinement change for each
prepared job. Trusted Plotloom code alone derives the frozen single-shot
ProductionUnit/Snapshot, visual proposal, reference roles and bytes, request
hash, and copyable assignment. The browser can name an approved shot or an
existing candidate to refine and submit the nonblank presentation change, but
cannot supply a prompt, a filesystem path, a URL, a VisualIntent identity,
an approval substitute, or a reference-byte declaration.

The image specialist owns built-in tool operation and a truthful delivery
manifest: the actual prompt passed to the tool, output filenames/hashes/roles,
tool/task evidence actually available, and limitations. It may make a disclosed
prompt adjustment, but cannot silently change frozen narrative facts or declare
its own result approved. Delivery bytes and metadata remain untrusted until
trusted code verifies confined paths, a complete declared set, hashes, MIME,
dimensions, and bounded raster decoding.

The repository owns atomic candidate publication, immutable delivery history,
conflict handling, job/refinement lineage, and currentness checks. Selection stays
an explicit P0 reviewed-keyframe decision; a cancelled, revoked, stale, rejected,
or late job result is retained as history but cannot be selected. A configured
same-host exchange root is runtime configuration, never canonical state and never
browser input. No job package, manifest, receipt, or public settings may contain
an API key or provider credential.

Versioned delivery manifests bind requests to completed files and available tool
evidence. Publish completion before atomic/idempotent ingestion. Returned files
and metadata are untrusted; hashes establish byte consistency, not model authenticity.
Preserve originals, actual tool prompts, refinement lineage and disclosed limitations.

The same-host package is deliberately readable by the assigned specialist and is
therefore not treated as an enforcement boundary. Copy projects the frozen request,
instructions, and reference bytes; Refresh reconstructs and verifies that complete
projection from the database immediately before reading any delivery. A changed,
missing, extra, or symlinked package entry fails closed and cannot attribute or
publish a delivery. This is a transport-integrity check, not a claim that POSIX
permissions make a local operator unable to edit a copied file.

Export is the manual authorization cutoff. Already copied packages cannot reliably
be recalled; cancellation/staleness limits applicability and selection, not remote
execution. Refresh does not generate, approve, select or rewrite history. Silent
jobs remain awaiting delivery rather than being labelled failed.

This extends ADR 0026's production boundary to an agent-operated backend while
retaining ADR 0012/0016 frozen-input and Approval requirements. P0 previews are not
relabelled as ProductionSnapshots. Ad-hoc images keep import provenance; actual
job-linked specialist outputs use the new lineage. Future automation preserves
the same request/delivery/selection contract.

### Self-contained copied-brief amendment (v2)

Every newly prepared v2 request freezes the creator presentation/refinement
change inside the hashed snapshot. A refinement additionally freezes the exact
current reviewed-keyframe binding, role-specific VisualIntent ID/revision and
intent payload. Trusted code resolves the narrow authored context needed to act
on that Shot: linked scene/beat/cue records, referenced characters, locations,
props and required entity states. It excludes unrelated project data and all
secrets. Canonical narrative changes still require ordinary stage editing and
reapproval; this field cannot silently alter them.

The currentness rule revalidates the frozen binding and intent after Copy. A new
role-specific VisualIntent revision invalidates that refinement job; Refresh
records a complete late delivery as inapplicable and publishes no candidate.
This belongs in the repository currentness contract because it prevents a
changed creator decision from being bypassed by an already-copied instruction.

V2 packages add the discoverable, revalidated
`completion-manifest.example.json` alongside the frozen request and copy
instruction; the assignment names it explicitly. The template shows the exact
versioned completion field shape but is not a delivery. Existing v1 job packages
continue to verify against their original projection, so persistence requires no
migration or rewrite.

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
