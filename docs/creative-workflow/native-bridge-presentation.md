# Native presentation suggestion contract v1

`source.proposal` freezes proposal revision/hash, inputs and replacement target.
`inputs/presentation-source.json` freezes every source's ID, coordinates, raw
text/hash and exact runtime choices. These are trusted bindings, not editable
output. Brief/scenes and saved dramatic intent provide context, not new facts.

Return `presentation.json` shaped exactly by `presentation-schema.json`:
`{"entries":[{"id":"exact-source","spans":[{"start":0,"end":12,"role":"physical","rendering":"忠实画面描述","reason":""}]}]}`.
Every source appears exactly once. Spans cover its entire raw text in order,
without gaps/overlap, using Unicode codepoints (Python string indices, not UTF-16
offsets). Split mixed prose semantically; never classify a whole field merely
because it came from action or composition. Every span has an explicit role.

- `physical`: visible action/composition, including negative physical constraints
  such as no readable phone text. Provide faithful rendering preserving all
  entities, action order, continuity, composition/style/portrait constraints;
  remove only wording separately assigned to another role. Do not invent facts.
- `visible_text`: actual diegetic written words. Exact raw substring is the
  text; rendering must be empty, and it is not spoken. “No readable text” is a
  constraint, not a visible-text string to display.
- `dialogue`: only frozen dialogue-source words, exclusively cue-owned; empty
  rendering. Other kinds cannot become dialogue.
- `runtime_choice`: directions belonging to the frozen player's authored choice.
  Empty rendering, explicit reason referencing that choice. Do not rewrite
  questions/options or film a runtime choice as an actor's speech.
- `review_only`: non-media review directions, empty rendering and explicit reason
  explaining why the source is not a physical fact. Do not discard restrictions
  or uncomfortable ambiguity by labeling it review-only.

If a faithful complete assignment cannot be made, stop and report the concrete
blocker rather than inventing ownership. Semantic limitations belong in the
completion manifest. At most 256 sources, 64 spans per source and 180,000 bytes
of source/context. The validator proves structural coverage, not semantic truth.

Validate then derive the inert report with `scripts/native_bridge_presentation.py`.
Publish the completion template last with actual hashes. Output has no source
replacement, reviewed flag, proposal/canonical fields or approval. The author
can edit suggestions, explicitly confirm/save presentation, then independently
confirm production. Late or stale output remains read-only evidence.
