# ADR 0054: editable storyboard continuation resolves only downstream currentness

## Decision

Checkpoint 3A continues a reviewed, current Story Bible and Story Graph through
the existing Scene Beats and Storyboard owners. At the explicit continuation
action, the browser rereads canonical stage heads: a missing or stale Scene
Beats stage requests the contiguous `scene_beats` plus `storyboard` range; a
current Scene Beats stage with missing or stale Storyboard requests
`storyboard` alone; when both are ready it creates no run. A non-current Bible
or Graph is rejected with a proposal-regeneration instruction.

The action does not save the Brief, Bible, Graph, or any unchanged editor
buffer. It uses the normal pipeline run, progress projection, quarantine, and
server-issued exact-repair/rebuild facilities. Generated scenes and storyboard
remain editable only in their existing editors. This action is not Storyboard
Approval, a new job type, or media authorization.

## Consequences

The continuation cannot silently replace current downstream material and keeps
the server stage-head contract as the single currentness authority. Downstream
recovery remains governed by the existing frozen run evidence and eligibility
rules; no automatic retry or new repair semantics are added.
