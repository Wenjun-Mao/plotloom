# ADR 0203: Visible text failures and explicit additional corrections

Status: owner-approved source implementation, 2026-10-22.

## Problem and decision

ADR 0202 retains trustworthy content rejection but hides its explanation and
hardcodes one correction throughout lineage. Its profile limit also conflates
host capability with the launch's generation authority.

New profiles declare `textCorrectionContract: plotloom.text-correction.v2`.
This versioned host capability produces typed diagnostics; it grants no work.
New launches freeze a finite `textCorrectionLimit` (default 1, zero disables
automatic correction). Existing frozen profiles/policies are never rewritten.
The retained profile limit remains a historical field, not the new capability.

Each immutable corrective request links its immediate failed parent and advances
the stage ordinal. Automatic consumption counts automatic requests throughout
the chain, including before/after manual requests. An explicit creator command
grants exactly one extra request, binding run revision, failed attempt, rejection
hash, command identity and optional directions. Atomic creation and deterministic
identity make duplicate/lost acknowledgements idempotent; stale commands fail.
Directions belong to retry metadata and cannot replace Brief, style or upstream
authority. Successful stages retain their adopted requests and outputs.

The named `text_retry_command` atomically owns this creator grant and its exact
candidate-head replacement. Ordinary manual commands still force takeover.
Only successful new-grant creation updates the expected material closure;
duplicate acknowledgement reading cannot rebase a changed project.

Outline adoption also invokes lifecycle/rebuild quiescence. Those guards now use
the same exact per-candidate terminal-content-rejection proof as publication and
snapshot guards: retained failed ancestors cannot still publish, while manual,
unstarted, runtime and UNKNOWN candidates remain blocking. The ordinal-ten
Outline journey exposed the prior duplicated prepared-row interpretation.

The failure card reads exact source validation diagnostics and bounded candidate
field excerpts. Source API normal-return explanations are display-only literal
data; allowlisted issue codes/paths/facts remain the sole retry classification.
Generic issues do not invent field precision or repeated-problem certainty.
Diagnostics reaching the source's display bounds yield unknown comparison,
because equal retained prefixes cannot establish equal complete explanations.
Runtime/parser/refusal/cancel/UNKNOWN/stale outcomes never grant corrections.
Currentness, frozen execution, lifetime budgets, process ownership and restore
dispatch refusal remain enforced. Images and video acquire no retries.

## Alternatives and guardrails

Reject stderr-derived authority, quota resets after a manual click, mutable failed
jobs, downstream prompt repair, and silent expansion of frozen authority.
Focused checks cover multi-attempt exhaustion, zero/manual, duplicates/staleness,
budget/UNKNOWN/restart/restore and preserved upstream/adopted stages. The paid
Outline parser admits capability metadata without expanding its zero-retry grant.
ADR 0184's value-only profile construction pin requires explicit dependency review.
