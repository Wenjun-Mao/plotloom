# ADR 0141 — Explicit character render direction

Status: accepted, 2026-10-09

## Evidence and ownership

The native revised Cast job `ch_39ba9445a043441ab2c289934e5fb441`
correctly disclosed an impossible instruction combination: the story requested
live-action photography, but pinned `novel-characters` required its painterly
`realistic` preset. Editing image prompts downstream would conceal the same
generation-contract defect already encountered in the baseline run.

The author chooses the character render style; the saved Brief owns additional
visual direction. The specialist proposes character identity and image prose.
Trusted code freezes the choice, preset and direction and checks currentness.
Neither a preset nor a validator constitutes creative acceptance.

## Decision

Cast preparation requires an explicit `live-action`, `realistic` (半写实厚涂),
or `ghibli` choice, without guessing from free text. Freeze
`cast-style-contract.json` in the request and Cast binding. Include the selected
preset, current Brief visual direction and implementation hash. The same style
rules apply at delivery, acceptance and reopened save. A missing or changed
contract is not current and cannot be consumed; retained evidence stays readable.

`scripts/cast-style.mjs` is the current character-style owner. It composes the
pinned character validator/renderer with an explicit live-action preset, on the
original candidate shape. It never translates candidates, edits vendor files,
redefines upstream `realistic`, or supports a legacy execution path. Generation
validation retains upstream structure, language and verbatim-source checks;
author edits retain Plotloom's existing minimum-design gate plus style checks.

The frozen preset overrides upstream style defaults, not source facts or stable
character IDs. Its render sentence belongs in positive prompt and sheet; a
live-action candidate must not prescribe illustration or prohibit photography.
Brief direction remains visible creative guidance: prose conflicts require
review, not a keyword-based inference of the author's desired medium.

## Consequences and guardrails

Preparation UI has no implicit selection and displays the frozen choice while
reviewing. Currentness checks reject changed Brief direction or implementation;
no accepted style is silently migrated. The previous delivered files are immutable
evidence and must be replaced by a newly prepared task, not repaired in place.
Tests cover three styles, contradictory directions, source/structure validation,
required preparation input, stale bindings and author-edit refusal.
