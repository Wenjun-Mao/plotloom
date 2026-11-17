# Local story projects

Story projects live in `.local/stories/<title>/`, outside Git. Keep manuscripts,
outline/script/cast JSON, art and character references, staging, storyboards,
production records and final media together there. New clones do not include
these local projects. Product plans stay in `docs/roadmap/`; reusable skills and
application code remain versioned.

The local catalog is `.local/stories/README.md`. Current projects include
《别叫我的名字》, 《凡人修仙传》 and the manuscript for 《放映室最后一夜》.
The first project's completed three-episode viewer is under
`别叫我的名字-shuohao-production/exports/three-episode-baseline-v1/index.html`
inside its story directory.

Each project keeps its original filenames and sibling relationships. For the
completed three-episode run, `current-selection.json` identifies the relocated
70 selected clip folders. `project.json` identifies its current entrypoints and
the original selection used by the retained delivery evidence. The exact move
manifest and readback live in `.local/roadmap-organization-20261116/`.

Frozen inputs, receipts and review/assembly records retain their original bytes.
Absolute paths inside them describe the original run. Older project-specific
execution helpers may still use those paths; relocation does not reactivate
their spent grants or establish a fresh validation pass. Use the current project
index and relocation record to locate the retained files. Future authoring still
follows the owner's manual skill-invocation preference.

VS Code's Source Control count includes modified and untracked files. It is
separate from commits ahead of GitHub. Files under `.local/` are intentionally
ignored and should not appear in that count. See
[ADR 0243](../adr/0243-local-story-projects-and-roadmap-boundary.md).
