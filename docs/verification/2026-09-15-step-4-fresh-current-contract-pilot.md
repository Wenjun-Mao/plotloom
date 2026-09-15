# Step 4 fresh current-contract pilot — media preflight block

Captured 2026-09-15 from one attended local run. This is a secret-free
operational receipt. It is neither Step 4 completion, audiovisual acceptance,
human/product acceptance, Alpha qualification, nor release evidence.

## Fresh lineage and preservation

- New project: `失物站台 · Step 4 新试点`
  (`fef96fc8-86f8-4132-91bd-32d58f5bb504`), created through the normal blank
  project workflow. Only the retained project's author brief was copied; no
  retained graph, generated content, plan, parent, or child was copied.
- The old project `ae4595cf-2bcc-480a-839b-af3a8901240c` remains unchanged:
  `project.json` is
  `eeaa80fa1e81a7fdbfa65fc3ee05a68146232cc94b8af25f1a289b9d45bb865b`, its
  SQLite database is
  `ebf76f289580064cca26fa3439b1876fd5ee8082f6b6b0ed53eef20677636227`, and
  the retained parent artifact is
  `03e8673a2a1f6592c4059be2fa12e3032c1f390317acc58f6fa90153fb699454`.
- The fresh run `135343bf-349e-4bf9-aaf3-cfee8a723314` installed all four
  stages atomically: Story Bible 1/1, Story Graph 1/1, Scene Beats 8/8, and
  Storyboard 8/8. A Codex-attributed routine engineering review approved
  storyboard revision 1; it explicitly did not assert human/product approval.

## Current continuity evidence

- The current sealed Story Graph is revision 1,
  `86a345b9d91e7f5daea1470028c000fe401523bcf6ee2dcd37b39e0e32e329c1`.
  It contains explicit typed `entity_state_effects`, including `char_linche /
  等待中` and `loc_station / 安静等待`, separately from opaque
  `state_effects`.
- The one Story Graph unit used the current correction identities:
  `m1.13`, `bounded_correction.v23`, `correction_directives.v5`,
  `correction_evidence_projection.v3`, and `correction_response_schema.v5`.
  Its primary and first correction were rejected for the bounded
  `semantic.join_state_effect_conflict` vocabulary (`watch_opened`); the
  second correction accepted. Scene Beat #7, previously quarantined in the
  retained lineage, accepted on its first attempt in this new run.

## Media stop condition

The approved storyboard was used to prepare and copy one exploratory,
identity-only character-reference assignment
`ij_5cd19d01283246b4b3dc501b048eadc2`. Its request had no input references and
did not approve or select a character reference. Before ImageGen, the required
specialist preflight ran once and refused:

```text
Unsupported checkout: pinned specialist source is not committed at HEAD.
```

No ImageGen invocation, output, completion manifest, staging cleanup,
character-reference decision, reviewed keyframe, H3 preparation, H3 dispatch,
video review, playback, snapshot, close/reopen, or isolated restore was
performed. Counts for this pilot therefore remain ImageGen **0** and H3 **0**.
The owned local server was stopped. The exported package and preflight failure
remain in the ignored project output; this receipt does not repair, replay, or
weaken that boundary.

## Verification

- Read-only SHA-256 checks matched all three retained-evidence values above.
- `git diff --check` passed before this docs-only receipt was added.
- No full suite was necessary for a documentation result; no application source
  was changed.

## Disposition

Step 4 is partial. The generation-contract objective is demonstrated in a new
lineage, but media admission is blocked by the specialist pin preflight. A
future, separately authorized attempt must start from the preserved new project
state and resolve the pin authority before creating any media; it must not
replay this exported assignment blindly.
