# ADR 0149: Accepted evidence has independent review authority

Status: implementation in progress, 2026-10-09.

## Problem

Fresh candidate status correctly owns dispatch/acceptance, but Script/Art UI
reused it for retained accepted content. After Art r3, preparing current Script
r3 hid the accepted r2 diagnostics, called r2 current and enabled Reopen. Candidate
admission refused that write; without a candidate, stale Script/Art Reopen could
still change the head before save refused. This is a read/admission contract gap,
not a reason to weaken stale checks or compare upstream hashes in the UI.

## Decision

Cast/Art/Script/Storyboard read models require `acceptedReviewState`: status
missing/current/reopened/retained plus diagnostics against the accepted binding.
An active candidate or accepted-binding mismatch means retained; missing means
no accepted evidence. Clean accepted/reopened heads have their respective authority.
Unexpected lifecycle combinations remain retained. Candidate `status` and
`staleReasons` keep their existing active-seam meaning. No persistence migration,
default compatibility field, adapter, new cache or frozen-evidence rewrite.

Accepted labels/editing/continuation use this projection. Candidate preparation,
dispatch and acceptance remain independent, so a current replacement can complete
over outdated retained evidence. Script/Art Reopen enforce accepted binding
currentness before mutation, like Cast. Dirty draft revision/hash/owner checks
remain additional requirements; invalidated text is retained for explicit disposal.

## Guardrails

Four-stage stale/current retained heads under prepared/ready replacement; cancel
restores current or retained authority; accept installs the replacement. Refuse
direct stale Reopen without head mutation. Current reopen/save and dirty-text
recovery remain valid. Verify graph Story detail parity and conservative media/
production eligibility. Binding inequality never alone proves an author changed
story/style; see ADR0134. Later qualification must identify its own revision.
