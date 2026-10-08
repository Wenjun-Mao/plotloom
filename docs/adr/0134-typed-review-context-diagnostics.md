# ADR 0134: Typed Cast/Art currentness diagnostics

Status: Accepted, 2026-10-08.

## Problem

Art delegates shared source/map/graph checks to Cast. Its successful stale-state
read flattened exceptions into strings, losing prerequisite ownership and showing
“before preparing cast” in Art. The preparation-refusal path exposed the same
raw message. A status-only StageGuide could recommend updating Art while the
actual prerequisite belonged to Source or Characters.

## Decision

Cast/Art `staleReasons` is a current-contract list of typed diagnostics: stable
code, preparation owner, exact technical message and optional binding field.
The original string-list contract is replaced, with no compatibility union,
string-matching translation or retained schema adapter. The shared prerequisite
exception carries the same diagnostic through a structured409 refusal.

Cast/Art present Chinese guidance from codes, link to the indicated owner in a
new page so existing dirty drafts remain protected, and keep raw evidence under
technical details. Busy/failed/dirty guidance retains its existing precedence.
Generic HTTP transport and other review-state contracts remain unchanged.

Currentness comparisons, action eligibility, CAS, pins, frozen requests,
report bytes and persistence remain unchanged. A combined prerequisite failure
does not invent which individual prerequisite is missing. Binding differences
retain their exact fields, order and raw text.

## Rejected alternatives and guardrails

Reject per-panel exception-text translation and a second readiness model.
Test successful stale reads and failed preparations, Source versus Characters
ownership, binding/style differences, original evidence/content retention and
unchanged stale refusal boundaries. Directly inspect supported desktop pixels;
the new typed diagnostic is not an approval or automatic regeneration request.
