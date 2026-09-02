# Plotloom architecture provenance maps

This directory preserves the architecture comparison that informed Plotloom:
the path from project defaults or user input to a storyboard, plus the
media-task boundary that follows it. The file names and diagram labels retain
“V1” and “V2” because they identify the two frozen predecessor snapshots; V2 is
the development identity of the product later extracted as Plotloom.

## Read these first

The directory root intentionally contains only this guide and the three
self-contained readers:

1. [`v1-v2-architecture-delta.html`](v1-v2-architecture-delta.html) — start
   here for the V1 / Delta / V2 component and responsibility comparison.
2. [`input-to-storyboard-workflow.html`](input-to-storyboard-workflow.html) —
   compare how the same project input becomes a storyboard in V1 and V2.
3. [`v2-lineage-and-repair.html`](v2-lineage-and-repair.html) — understand V2
   run state, quarantine, repair, cancellation, and restart behavior.

## Supporting files

The authored JSON files are the source of truth. The HTML files are generated,
self-contained readers produced from those specifications.

| Source | Generated reader | Purpose |
|---|---|---|
| `supporting/specifications/narrative-forge-v1.architecture.json` + `supporting/specifications/narrative-forge-v2.architecture.json` | `v1-v2-architecture-delta.html` | V1 / Delta / V2 component and responsibility comparison |
| `supporting/specifications/input-to-storyboard.workflow.json` | `input-to-storyboard-workflow.html` | V1 and V2 generation paths from input to storyboard |
| `supporting/specifications/v2-lineage-and-repair.lifecycle.json` | `v2-lineage-and-repair.html` | V2 run, quarantine, repair, cancellation, and restart semantics |

Everything not intended for ordinary reading is under `supporting/`:

- `supporting/specifications/` contains the editable Archify JSON sources.
- `supporting/validation/` contains the comparison receipt, automated visual
  receipts, contact sheets, and light/dark screenshots.

The comparison deliberately treats V1 and V2 as separate system boundaries.
There is no production runtime edge between them. Their only relationship was
development-time comparison and contract testing. The extraction is now
complete; current repository and identity decisions are recorded in
[`ADR 0010`](../adr/0010-plotloom-clean-repository.md).

## Evidence and scope

These diagrams are authored historical snapshots carried from the verified
source checkpoint named in
[`initial-extraction.md`](../provenance/initial-extraction.md). They are not an
automatically refreshed dependency graph of the current Plotloom tree. Several
important relationships are runtime or domain contracts that a static import
scanner cannot see:

- DOM events and the dynamic V1 project facade;
- FastAPI-to-TypeScript contracts and dependency injection;
- stage ordering, stale propagation, optimistic revisions, and atomic commit;
- prompt, response, validation, candidate, and repair evidence lineage;
- session-only key flow and the explicit absence of secret persistence;
- provider adapter dispatch and safe job recovery.

In the frozen comparison, V1 source scope was `app.py`, `backend/`, and
`static/src/`; V2 scope was `src/narrative_forge_v2/` and `frontend/v2/src/`.
Those old paths do not exist in the Plotloom runtime. The corresponding current
roots are `src/plotloom/` and `frontend/src/`. Generated bundles, tests, local
data, `.venv`, and `node_modules` are not architecture inputs.

Archify repository evidence requires an exact public Git revision. These
historical specifications intentionally retain their original evidence shape;
do not retrofit current Plotloom paths into them and imply that the generated
readers are a fresh code map. Author a new Plotloom-only specification when a
current-repository architecture reader is needed.

## Stable-ID comparison contract

Architecture Delta compares authored IDs. Responsibility-equivalent V1 and V2
components therefore retain stable IDs such as `browser-workbench`,
`generation-api`, `prompt-assembly`, and `media-pipeline`. A genuinely replaced
concept uses a different ID: V1 `mutable-project-state` is removed, while V2
`canonical-domain` and `generation-orchestrator` are added.

Changing these IDs for wording or layout reasons would make the delta falsely
report a removal and addition instead of a changed or rerouted responsibility.

## Rebuilding the readers

The readers were generated with Archify 2.16 at commit
`5de7275fe87a66a19d52a4d9b0b3a4f2a5a90115`. Keep Archify outside the
Plotloom runtime and point `ARCHIFY_DIR` to its `archify/` directory:

```bash
export ARCHIFY_DIR=/path/to/archify/archify
export ARCHIFY_UPDATE_CHECK_DISABLED=1

node "$ARCHIFY_DIR/bin/archify.mjs" validate architecture \
  docs/architecture/supporting/specifications/narrative-forge-v1.architecture.json \
  --quality showcase --json
node "$ARCHIFY_DIR/bin/archify.mjs" validate architecture \
  docs/architecture/supporting/specifications/narrative-forge-v2.architecture.json \
  --quality showcase --json
node "$ARCHIFY_DIR/bin/archify.mjs" compare architecture \
  docs/architecture/supporting/specifications/narrative-forge-v1.architecture.json \
  docs/architecture/supporting/specifications/narrative-forge-v2.architecture.json \
  docs/architecture/v1-v2-architecture-delta.html \
  --receipt docs/architecture/supporting/validation/v1-v2-architecture-delta.receipt.json \
  --quality showcase --json
node "$ARCHIFY_DIR/bin/archify.mjs" check \
  docs/architecture/v1-v2-architecture-delta.html

node "$ARCHIFY_DIR/bin/archify.mjs" deliver workflow \
  docs/architecture/supporting/specifications/input-to-storyboard.workflow.json \
  docs/architecture/input-to-storyboard-workflow.html \
  --quality showcase --json
node "$ARCHIFY_DIR/bin/archify.mjs" deliver lifecycle \
  docs/architecture/supporting/specifications/v2-lineage-and-repair.lifecycle.json \
  docs/architecture/v2-lineage-and-repair.html \
  --quality showcase --json
```

Run `visual-check` on each generated HTML after delivery. Its containment and
screenshot receipt is necessary evidence, but screenshots must still be
inspected by a person before claiming visual polish. Archify initially writes
those sidecars beside each reader; move each complete `*.visual-check.*` family
into `supporting/validation/` afterward so its relative contact-sheet image
links stay intact.

For Architecture Delta, the post-compare `check` is an additional acceptance
gate: base and head can each be valid while old and new rerouted relationships
still collide when overlaid in the Delta view.

The Workflow and Lifecycle readers pass containment at all four desktop test
sizes. The Architecture Delta itself passes all 28 deterministic comparison
checks and is visually readable, but Archify 2.16's comparison-page shell is
taller than the viewport at 1440×900, 1600×1000, and 1920×1080; those sizes
therefore require normal page scrolling and the checked receipt truthfully
remains `failed`. At 2048×1320 it is fully contained. The same shell also
resolves the automated nominal “light” capture as dark. Do not reinterpret
either tool limitation as a clean visual-check pass.
