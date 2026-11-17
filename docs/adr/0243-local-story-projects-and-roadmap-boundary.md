# ADR 0243 — Local story projects and the roadmap boundary

Accepted: 2026-11-16, following the owner's explicit choice to keep all story
project files local and outside Git.

## Decision

`docs/roadmap/` contains product plans, the plan template and their index/archive.
Creative manuscripts, authoring JSON, character/art assets, story-derived study
protocols/prompts, production records and exported media belong under ignored
`.local/stories/<title>/`. This includes small source/record files as well as
large generated assets. Existing `.local/` ignore policy provides the boundary;
do not hide arbitrary JSON/Markdown or generated files repository-wide.

Reusable skills, product code/test fixtures, engineering plans and product
qualification remain versioned with their owners. Completed general engineering
receipts belong in `docs/verification/`. The former mixed roadmap index is
retained locally as historical notes, with a compact plan index taking its place.

Preserve each story's sibling layout and all frozen evidence bytes when moving
it. Record exact old/new file locations and identities. Supply an explicitly
relocated selection derivative for current navigation; preserve the original
selection and its pinned delivery evidence. Old absolute paths in historical
records are historical provenance, not promises of executable legacy tooling.
Do not add symlink compatibility paths, rewrite old receipts or regenerate media.

Git synchronization concerns committed history. Untracked source-control badges
also include local files that have never been committed. Local story projects
are deliberately excluded from future commits and pushes; earlier committed
history is retained. This is a storage/documentation change, not application or
provider activation, production deletion, creative acceptance or a CI request.
