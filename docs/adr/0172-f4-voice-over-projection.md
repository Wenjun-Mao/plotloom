# ADR 0172: Preserve F4 voice-over in canonical dialogue

Status: accepted for the bounded serial-executor repair, 2026-10-14.

## Problem and evidence

The fresh production-supervisor proof at `596c2213` completed and adopted all
eight text deliveries, then stopped at Bridge installation. Its final proposal
retained `dialogue_speaker_unknown` for episode 1, scene 1. The accepted F4
Script used the exact reserved `speaker: "VO"` marker for narration. The pinned
Shuohao Script validator explicitly permits `VO` outside the scene's Cast.
Bridge projection instead required every speaker to map to a Cast character.
The canonical `DialogueCue` already supports exactly one of `speakerId` and
`voiceOver`; the projection omitted the supported voice-over branch.

## Decision and ownership

The author/model owns F4 speaker choice, line text and delivery notes. F4 owns
the exact, case-sensitive `VO` marker. Trusted Bridge code maps that marker to
`speakerId: null`, `voiceOver: "VO"`, preserving the original line, performance
notes, language, duration estimate, beat identity and shot cue association.
All other speaker values still require an exact accepted Cast-to-canonical
mapping. No arbitrary unknown speaker becomes narration.

This changes source projection, not the generation schema, timing policy,
presentation partition, voice casting, provider or image admission. No narrator
character or visible character reference is invented. Character dialogue keeps
its existing mapping and `voiceOver: null` semantics.

## Alternatives and guardrails

Forbidding valid `VO` in a prompt creates a narrower downstream dialect.
Adding a fabricated Cast character or dropping the line loses source meaning.
Treating every unmapped speaker as voice-over weakens the identity contract.
These alternatives are rejected.

Regression checks cover exact VO, ordinary mapped speakers, unknown speakers,
case/whitespace near-misses, unchanged text/delivery/timing and cue ownership,
and reviewed installation followed by ordinary current-state validation.
The stopped proof, accepted source candidates and original proposal remain
unchanged; they are evidence of the old contract. Any new native proof uses a
new disposable run with current source pins.
