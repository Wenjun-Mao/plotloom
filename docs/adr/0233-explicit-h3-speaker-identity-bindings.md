# ADR 0233 — Explicit pictured-speaker bindings in H3 directions

Status: accepted for the V2 final-request fidelity repair, 2026-11-01.

The compiler's generic S1/S2 labels alone do not bind two pictured people to
their authored speech. Independent checking caught an ambiguous compiled V2
request before submission. Three earlier unselected requests have the same
gap; their original requests, checks and media stay retained as superseded
evidence, without a claim that they met this stronger explicit binding.

The author owns speaker identities, pictured character facts and speech. The
model's existing English `shot.composition` field may adapt the complete frozen
character/reference context into explicit pictured-speaker aliases. Voice
fields remain voice-only. No new schema field or compiler numbering is added.
Trusted code continues assigning labels in first-encounter order of unique
speaker/voice-over identities among nonempty cues, resetting each shot and
reusing a label for repeated identities. It preserves cue order and exact
dialogue bytes. S1 never implies C01. Off-screen status is preserved.

Drafting binds every visible S label to the authored name and discriminating
pictured features from the frozen keyframe intent or resolved character facts.
It must not guess identity from screen position or invent missing context.
Independent checking verifies every alias against the complete compiled prompt.
An unsupported identity fails before production authorization.

First prove the correction through the existing native English edit/check path
without media. Then use the clarified pinned skill for one source-correct final
continuity chain. Replacing its root requires fresh downstream final-frame
inputs. This repairs request fidelity under existing V2 generation authority;
it creates no beauty-reroll loop, retrospective approval or creative acceptance.
