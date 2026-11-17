# Separate roadmap documents from local story projects

## Current status

Updated: 2026-11-16. Owner: this chat, sole source and relocation writer.
Baseline: synced main `4b2bebf4`, two existing modified roadmap documents and
5,535 untracked story-project files. The owner explicitly chose to keep all
story-project files local and outside Git. Implementation and provider-free
layout verification are complete: 5,565 story/history files moved into ignored
`.local/stories/`, with all original file identities, sizes and modification
times preserved. Roadmap now contains planning documents and its archive; the
index is 106 lines rather than 1,532. Next story work uses the local catalog.
Exact scoped commit/sync status is recorded separately in the local publication
receipt below, under the owner's existing committed-change sync instruction.
No application, provider or service activation is part of this outcome.

## Acceptance

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| Local story ownership is explicit | Sources, assets, records and deliveries under ignored `.local/stories`; no new story files staged | No | PASS: original 5,535 untracked story files relocated; local sources/records deliberately excluded |
| Roadmap is a planning index | Story manuscripts and generated/report folders removed; study results have appropriate destinations; maintained links updated | No | PASS: only planning Markdown and archive remain; story-derived study records stay local; three engineering records moved to verification |
| Relocation preserves current work | Exact move manifest and file identity/readback; 70 selected clips and four final exports remain present; retained evidence bytes unchanged | No | PASS: 5,565 story/history file identities preserved; both previously dirty documents match their original baseline SHA-256 values |
| Delivery remains usable | Current viewer links resolve; a separately identified relocated selection binds the same ordered clips and review hashes | No | PASS: 70 review hashes, four exports, six HTML viewers/26 targets and 166 maintained Markdown targets verified |
| Git changes reflect documentation only | No generated story assets in status; scoped commit and authorized sync; CI not requested | No | PASS: documentation-only diff and ignore boundary verified; exact publication state in the local receipt |

## Scope and method

This is documentation and local-file organization, not production activation,
generation, deletion, history rewriting or schema migration. Root owns the exact
move manifest and local validation. Read-only workers classify documents and
inspect path dependencies. Use existing filesystem, Git and HTML/link parsing;
do not introduce a migration framework or symlink compatibility layer.

Move each story's sibling folders together so existing relative viewers retain
their layout. Preserve frozen JSON, manifests, receipts and hashes. Old absolute
paths inside historical evidence remain historical; an explicit relocation
record and a current selection derivative describe new locations without
claiming legacy preflights were rerun. Existing ignored native execution helpers
with absolute paths are not reactivated or repaired by this task.

Keep product engineering plans and reusable-skill decisions versioned. The
owner's story-project choice applies to creative inputs and production records,
not an abandonment of application features. Current Git deletions do not erase
earlier committed history. Preserve the content of both existing dirty documents
as it moves into the appropriate index/project record.

## Evidence and limits

The local task record is `.local/roadmap-organization-20261116/`:

- `move-plan.json`: 42 exact source/destination moves, 5,568 files including
  three engineering records, original SHA-256 values and file identities.
- `move-result.json`: same-filesystem rename and identity readback; no media
  deletion, provider call, runtime change or symlink fallback.
- `navigation-result.json`: maintained link repairs and the relocated selection.
- `verification.json`: actual layout/selection/viewer/ignore checks, including
  preservation of both preexisting dirty documents.
- `publication.json`: scoped source revision, live remote readback and CI status.

Independent GPT-6.1 Sol/Medium review found no concrete data, navigation,
Git-boundary or source-preservation defect. Its closeout finding about stale plan
status was corrected here. The former index and the dirty caption replication
plan are preserved locally without changing their bytes. Source, frontend,
dependencies and application runtime are unchanged; their existing qualification
is reused. No application suite or fresh generation was necessary for this
documentation/filesystem change. Historical absolute-path preflights and creative
quality were not reassessed; earlier Git history remains intact.
