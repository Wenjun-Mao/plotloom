# ADR 0083 — H3 single-image prompt contract

Date: 2026-09-23

Status: the 2026-09-23 v2 decision below is historical; the 2026-09-24
amendment at the end is the current preparation contract.

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
Canonical shot and resolved context remain the owners of image, action,
camera, speaker, dialogue, and sound facts. The keyframe owns visual style;
the compiler does not assume a live-action medium. Each dialogue cue appears once in a
language-tagged `<d>` block with a stable speaker ID. Only a speaker listed in
the shot's authoritative on-screen `characterIds` is described as visible;
other speakers remain off-screen. Dialogue appearing in
another authored description is rejected before dispatch. Ambient and physical
sound events go only to `overall_soundscape`; `diegetic_sound` and
`diegetic_music` go in the shot description; `score` goes to
`non_diegetic_music`. An empty soundscape gets a neutral environmental
instruction, and absent music is `N/A`. The v2 prompt asked for no captions or
new visible text. Jobs prepared under that decision identified the contract as
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

## 2026-09-24 amendment: reviewed English provider directions

The prior verbatim-source rule missed the [official H3 prompt-writing skill's
English rewrite rule](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/SKILL.md).
In the first retained take, the director heard unclear extra speech before the
intended line. In the second, the director identified the extra utterance as the
Chinese canonical action sentence. The stronger soundscape prohibition did not
resolve that failure. Both exact prompts and media
remain historical evidence; the vocal-control condition is closed for new jobs.

New H3 preparation exposes the exact non-dialogue source fields to be rendered
as English provider directions. A reviewed direction package binds to their
source coordinates and hash. Trusted code places those field renderings in the
I2VA template and freezes the original sources, reviewed renderings, and final
prompt together. The package is refused if any source changed, a field is
missing or extra, a rendering is blank, or the exact compiled prompt hash
differs from the read-only preview. `plotloom.h3-i2va.v3-reviewed-en` is the
new compiler version. Dialogue, lyrics, and authored
visible text remain in their original language in their designated H3 roles.
This is a provider-facing rendering of source facts, not a canonical rewrite or
a general raw-prompt override. The reviewer owns semantic faithfulness and
language judgment; mechanical checks do not certify translation quality.

The H3 preparation surface offers a read-only prompt preview, then explicit
freeze of the same reviewed package. Existing frozen jobs continue to dispatch
their stored bytes; this amendment does not relabel prior takes as compliant.
The [living playbook](../operations/h3-prompt-writing-playbook.md) records
official rules separately from observations and hypotheses.
