# ADR 0226: Optional generated-media quality review

## Status

Accepted for the authorized 2026-10-30 Plotloom E2E delivery.

## Decision

Generated-media viewing, listening, comparison and quality judgments are optional
throughout current Plotloom workflows. Their absence must not block generation,
candidate selection, trimming, same-person/reference use, material adoption or
continuation, currentness, persistence/reopen, playback, snapshot/restore or
export. No QA-project allowlist, opt-out switch, expiry, replacement form or
implied human/agent quality pass is part of the current contract.

Keep a diagnostic introduced for a reported defect in troubleshooting.
Promoting it to a routine production step requires an explicit product
decision. This applies to skills and playbooks as well as runtime gates.

An explicit H3 video-candidate `reject` is a disposition, separate from an optional
failed or uncertain quality observation. Selection must respect that rejection
until the existing explicit reconsideration or replacement operation permits a
new choice, with its actor and CAS checks intact. This requires no viewing,
listening, passing quality judgment or mandatory observation form.

Keep four owners distinct:

1. Authoritative source and explicit adoption own story intent and source-to-final-
   request fidelity. Provider adapters cannot silently rewrite authored content.
2. The actual operator's selection records the exact source-bound candidate bytes
   and playback window. Selection does not claim observation or quality approval.
3. Trusted code owns technical eligibility, provenance, decoding, dimensions,
   duration/window checks, revision/currentness, compare-and-swap and dispatch
   authority.
4. Optional quality judgments record only what was actually reviewed, with a
   truthful actor and scope. Existing judgments, rejections and unreviewed state
   remain facts; removing a prerequisite does not rewrite them.

Use a current selection/handoff contract rather than reinterpreting historical
`whole-pack-video-native-audio.v1` receipts. Preserve current valued assets and
historical observations/rejections. Any narrow data projection must retain
selection, provenance, technical and authorization facts, and fail closed on
stale, conflicting, malformed or unauthorized state. Do not introduce historical
replay authority or weaken unknown-dispatch safety.

## Consequences

Update APIs, schemas, current readers, UI labels, generated instructions, export
and recovery together. Retire tests and docs only where they encode a compulsory
quality gate; preserve tests for technical refusal, source fidelity, truthful
attribution and optional observation accuracy. Earlier ADRs 0030, 0143, 0191,
0193 and 0198 remain historical decision records; this ADR supersedes their
product-owned compulsory-inspection requirements for current workflows. Their
provenance, authority and frozen-grant constraints remain in force.

This decision does not approve creative quality, authorize beauty-driven rerolls,
or claim anyone inspected media. Functional playback and layout checks are not
perceptual media review.

## Context

The original-story MVP requires technically usable generated media without
requiring audiovisual quality review. A QA-only functional exception would leave
ordinary projects, restart/readback paths and export gated. Global optionality is
the smallest truthful product contract that preserves technical integrity and
author-owned fidelity while removing that contradiction.
