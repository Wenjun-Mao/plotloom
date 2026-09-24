# ADR 0084 — One-variable H3 v1 vocal-control comparison

Date: 2026-09-24

## Problem

The director heard the intended line in the retained first H3 take, plus
additional unclear speech before it. The actual dispatched v1 prompt has one
dialogue block; its cause is unknown. Switching the next job to the corrected
general v2 compiler would change several prompt dimensions at once.

## Decision

Admit one narrowly versioned comparison condition through ordinary video-job
preparation. The caller names a current, ingested v1 baseline job in the same
project. Preparation reconstructs that baseline's v1 prompt and requires
exact equality of every newly resolved source, keyframe, provider-binding,
and request field. The sole treatment is a replacement of the v1 empty
`overall_soundscape` sentence with an explicit instruction that S1's quoted
line be the only vocal utterance. The condition requires one S1 dialogue cue
and an empty audio plan. Its compiler version, baseline job ID, prompt hashes,
and exact treatment prompt are frozen in the new job snapshot before durable
dispatch. Subsequent submission uses the stored prompt and the existing
single-claim, no-retry H3 transport; selection remains an independent review.

The comparison is retained in a separate project-folder copy. No canonical
shot or dialogue is revised, and no general raw-prompt override is offered.

## Alternatives and limits

A v2-versus-v1 comparison would confound soundscape, speaker, visual and music
formatting. A raw request override would evade currentness and accounting.
Neither is used. A matched seed and profile do not make generation
deterministic or prove causation; one pair only screens whether this instruction
is promising. Both full original takes and any six-second derivatives remain
unselected until listened-with-sound director review.
