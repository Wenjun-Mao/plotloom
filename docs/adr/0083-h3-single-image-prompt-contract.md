# ADR 0083 — H3 single-image prompt contract

Date: 2026-09-23

## Problem

The video job compiler sent flat `Action`, `Motion`, `Dialogue`, and `Sound`
lines to the single-image H3 gateway. It omitted the image-alignment sentence
and sound-role fields in MiniMax's current I2VA guide. A prior F6 source also
repeated its spoken line in action and dialogue; its extra speech and subtitles
were observed, but their cause was not established. The flat compiler made
this ambiguity possible for future source shots.

## Decision

Use one versioned I2VA compiler for new H3 jobs. Trusted code writes the
first-frame alignment sentence, `[Shot 1]` and the three named fields.
Canonical shot and resolved context remain the only owners of image, action,
camera, speaker, dialogue, and sound facts. The keyframe owns visual style;
the compiler does not assume a live-action medium. Source-language facts are
retained verbatim rather than machine-translated. Each dialogue cue appears once in a
language-tagged `<d>` block with a stable speaker ID. Only a speaker listed in
the shot's authoritative on-screen `characterIds` is described as visible;
other speakers remain off-screen. Dialogue appearing in
another authored description is rejected before dispatch. Ambient and physical
sound events go only to `overall_soundscape`; `diegetic_sound` and
`diegetic_music` go in the shot description; `score` goes to
`non_diegetic_music`. An empty soundscape gets a neutral environmental
instruction, and absent music is `N/A`. The prompt asks for no captions or
new visible text. New prepared jobs identify the corrected contract as
`plotloom.h3-i2va.v2` and store the exact compiled prompt in the frozen
snapshot, so later code edits cannot change their dispatch text.

Previously prepared jobs continue to use the flat compiler recorded by their
older `compilerVersion`, including Wan jobs. This preserves the request they
were prepared to dispatch; it does not offer the old format for new H3 jobs.
The one live trial prepared under provisional v1 before independent review
retains its exact v1 formatter and submitted-prompt hash in the trial receipt.

## Alternatives and consequences

An author-supplied raw provider prompt would bypass canonical ownership and
currentness. A separate text-model rewrite would add another unreviewed model
and provenance boundary. Neither is part of this bounded shot trial.

This is formatting and role separation, not evidence that H3 will obey the
dialogue or subtitle instruction. Regressions verify role assignment and
duplicate-line refusal; each resulting clip still needs independent visual and
auditory review before selection.
