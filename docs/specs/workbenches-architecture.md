# Workbenches: current responsibility view

Scope: consolidated ownership from approved decisions, not an automatically
generated full-code dependency map or a claim of runtime acceptance.

| Responsibility | Owner / boundary | Must not become |
| --- | --- | --- |
| Navigation, lifecycle, shared review reads | Workspace controllers and draft guards; shared project/revision-owned Source state | A second approval state in the six-step guide |
| Authoring state / commands / Undo | One GraphWorkbench provider and typed source-bound `story_graph/root` contract | Creator and Professional graph copies or competing writers |
| Creator presentation | Automatic topology layout, page-vertical/chart-horizontal navigation, bounded selected-node inspector | Free-position graph authority or sizing persisted in authored state |
| Professional presentation | Technical canvas/details over the same graph owner; active-project-session visual context survives mode switches and resets on project change/reload/close-reopen | Independent canonical graph save, durable authored layout or a reset of shared selection/content |
| Canonical reading | Accepted StoryGraph, shared topology/field projections, mode-specific shell | Fake authoring draft/source binding or revived legacy writer |
| Story and production context | Existing exact Script/review/bridge and shot/media owners | Node-only generation, guessed scene mappings or duplicate media state |
| Project durability | Existing typed project draft CAS and one graph owner; verified per-document journals, exact receipts, separate explicit Apply; nullable pre-Brief identity; optional Freeze with pure read leases and refused writes | Browser dumps, automatic canonical approval/generation, last-write-wins, hidden Unfreeze or historical repository fallback |
| Provider execution | Existing specialist/bridge/gateway owners and frozen request/dispatch identity | UI navigation implicitly generating, approving or selecting media |
| Batch revision | Existing native review, control and replacement owners; creator UI projects their exact persisted state and lineage | One fictitious transaction, automatic retry or a competing batch/job store |
| Timing and status | Existing run/batch GET owners project immutable facts; browser derives labelled display age | New persistence clocks, progress inferred from polling or extra provider execution |
| Delegated QA | Server-owned exact original-runtime grant and typed actor checks; browser has explicit project-local opt-in only | A global actor toggle, title/URL-based authority or unnamed-human fallback |

Primary records: [0218 working autosave / Freeze](../adr/0218-working-input-autosave-and-optional-freeze.md),
[0121](../adr/0121-current-source-graph-authoring.md),
[0122](../adr/0122-creator-workspace-presentation.md),
[0123](../adr/0123-node-context-story-production-workflows.md),
[0138](../adr/0138-one-current-story-explicit-rebuild.md),
[0145](../adr/0145-current-read-authority-for-graph-and-directory.md),
[0148](../adr/0148-workspace-owned-branch-mutations.md),
[0155](../adr/0155-recommended-creative-workflow-guide.md),
[0198](../adr/0198-delegated-disposable-qa-authority.md),
[0204](../adr/0204-explicit-rejected-batch-take-replacement.md),
[0040 project storage](../adr/0040-project-folder-storage-boundary.md),
[0048](../adr/0048-retire-shared-repository-runtime.md).

One data path connects workspace navigation → shared current graph owner →
source-bound draft/preview/admission → accepted canonical graph. Creator and
Professional are presentation branches off that owner, not separate stages.
Accepted Script/production projections read exact admitted identities and hand
off to existing shot/media controls. Reading and private geometry never grant
the mutation authority carried by current validated source/draft state.

The [older architecture readers](../architecture/README.md) retain frozen V1/V2
comparison provenance. They are not this view's source-of-truth for current files
and are not rewritten during consolidation. Broader service ownership remains in
[0216](../adr/0216-media-services-monorepo-boundaries.md) and service-owned runbooks.
