# ADR 0227: Source-bound standalone player export

## Status

Accepted for the Last Projection MVP.

## Decision

Export the current installed production and its technically eligible selected
playback segments as a self-contained static ZIP. Capture the full source,
canonical and selection identity under one database transaction; read and hash
the media outside that transaction; recheck the same complete identity before
publishing. Missing, stale, changed or undecodable media refuse export.

Canonical graph edges, installed runtime questions, cue-owned dialogue and
authored visible text remain authoritative. Export does not synthesize story
text, execute arbitrary graph state effects, or infer quality approval. The MVP
player accepts only structural graphs without executable state effects or join
contracts. The source graph writer's exact three `sourceMap*` provenance facts
are validated against the installed choices and never executed as player state.

An explicit export presentation request supplies a stable game ID, intro,
ending cards and logical node/edge/slot names, bound to the exact admission.
The request and private source/asset binding map are retained as an immutable
content-addressed build receipt in the project. A dedicated immutable inventory
table binds receipt and archive hashes, so snapshots and reopen retain them.
The exact prior layout has an explicit idle preserving upgrade; existing assets
and source rows remain unchanged. They do not mutate canon. Reopening with that receipt supports another
export against the same source; changing assets changes the asset version while
story revision remains independently identified. New production must be rebound
explicitly. This seam does not implement the later M2 update workflow.

The public archive contains only public text, relative opaque media addresses,
classic JavaScript, CSS and HTML. Private source paths, jobs, prompts, accounts,
dispatch grants and credentials remain outside it. The player works from file
and an isolated HTTP server, without Plotloom, remote services or module fetches.
Local Continue is best effort and validates stored routes against this story
revision. Denied storage must still permit play. Choices are untimed; replay
truncates abandoned route history.

The standalone game starts with sound enabled unless the player has saved a
different preference. Native and game controls share one video element across
clips. Mute and volume are remembered per game when browser storage is
available. The player can still change both during a storage-denied session.

When a scene ends at a decision, hold its final frame and place the untimed
choice buttons over it. A sole continuation directly into a footage-free choice
opens that choice as the clip ends. On Continue or backtracking, use the most
recent footage on the player's saved path to restore the decision's backdrop.

## Consequences

Under the [whole-take amendment to ADR 0082](0082-proposed-production-playback-timing.md#whole-take-playback-amendment-2026-10-31),
the player uses the selected media's measured playback length for resume and
plays through its natural end. The private source binding retains the storyboard
target separately. A pacing deviation carries no export restriction.

Provider-free export and real-browser playback precede fresh story generation.
Selection remains a technical use decision under ADR 0226. Final qualification
also checks the exact installed package, all authored routes, browser requests,
desktop/mobile layout and preservation/recovery of the current project.
