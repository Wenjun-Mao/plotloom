# 0161 — Specialist presentation suggestions remain separate from approval

Status: accepted

## Problem

The dramatic-intent specialist owns goals and purposes, not source presentation.
The presentation editor consequently starts unassigned and asks the author to
classify every source. A whole-review checkbox adds ceremony without an
additional domain transition. Guessing defaults by source kind would silently
classify mixed physical, literal-text, runtime-choice and review instructions.

## Decision

Add a separate frozen `bridge-presentation` native stage. Trusted code owns the
proposal revision/hash, source hashes, coordinates, exact text and runtime
choices. The specialist proposes exhaustive ordered Unicode-codepoint spans,
their ownership, faithful physical rendering and necessary reasons. The shared
structural binder validates coverage; it cannot establish semantic faithfulness.

Validated suggestions and immutable delivery evidence stay on the bridge job,
not in the proposal or canonical payload. Only an exactly current candidate is
exposed for editable prefill, visibly marked `助手建议`. Authored local buffers
are never overwritten by delivery. An intervening proposal/source/target change
withdraws candidate eligibility but retains its report.

Reuse the durable bridge job table without changing its SQL layout: its existing
`native_request.stage` is the native discriminator; API jobs remain intent-only.
The physical table retains its intent-era name. This is shared current-contract
storage, not a historical adapter. No existing frozen intent request, report,
saved intent, project schema or media is rewritten.

Replace the checkbox with one explicit `确认并保存呈现方式` action. The existing
CAS-guarded presentation PUT, with `reviewedComplete:true`, is still the sole
author approval and projection boundary. It rejects incomplete spans. Model
delivery cannot mark review complete, accept production, or dispatch media.
`确认投产提案` remains a separate action.

Group the editor by scene, use human-readable source labels, and disclose raw
source/splitting tools on demand. Do not duplicate long source prompts in the
default view or hide unavailable assignments. All source fragments and frozen
evidence remain readable; a visible save bar reports unresolved entries.
Already-saved dramatic intent is collapsed by default, with an explicit saved
summary and an expandable edit entry; unsaved intent remains open.

## Alternatives and guardrails

Do not widen frozen intent output, infer dropdowns from regex/source kind, add a
schema-breaking job table, or auto-save model output. Tests cover exact binding,
dispatch-once/unknown outcomes, late cancelled/stale evidence, read-only report
reopening, preservation of saved intent, dirty editor retention and explicit
unchanged-suggestion confirmation followed by separate production acceptance.
