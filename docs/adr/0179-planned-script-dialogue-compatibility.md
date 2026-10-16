# ADR 0179: Optional prospective Script dialogue compatibility

## Problem

The consumed `ed0d3624` pair passed real F4 native validation and adopted its
unchanged Script, then correctly failed F5 preparation. Its opening VO contains
27 codepoints: upstream estimates 6.0 seconds at 4.5 characters/second, whereas
saved zh-CN/natural canonical timing requires 8,910 ms and the selected F5 maximum
is 8,000 ms. F4's route estimates fit the unchanged 20-second Brief. ADR 0173
deliberately left F4's upstream estimator unchanged, so valid F4 did not promise
compatibility with a prospective F5 choice.

The same failed arm reconciled all ten original project/host attempts but ended
unresolved: its runner skipped pause for a blocked project while the strict
cleanup contract requires paused/awaiting_review. Both failures remain evidence;
neither is permission to edit, replay or reclassify that allocation.

## Decision and ownership

Shared F4 preparation accepts optional `plannedStoryboardMaxCutSeconds` (integer
2–15). None/null is a supported standalone intent and keeps bodyless manual F4
behavior. Explicit manual selection and autopilot use the same operation and
receiving checks. The F5 owner defines its existing eight-second default once;
autopilot explicitly passes that same selection at F4 and F5. A prospective
assertion grants no dispatch/adoption authority and does not fix a later manual
F5 choice, which stays configurable and independently validated.

Trusted code freezes a typed requirement in Script binding/admission: saved
spoken language, the canonical profile's version/identity/rules, normalization
identity and selected maximum. Do not freeze future Script identity or line
coordinates before the candidate exists. The author owns language and route
maximum; the caller selects an optional intended maximum; the model authors
content/performance notes, never trusted rates/minima. Keep current normalization,
upstream schema/creative gates/estimator and canonical rates unchanged.

Expose the requirement in the primary prompt and hashed inputs. One shared
canonical receiving check governs opted-in native validate/render and project
delivery/acceptance/section edits, alongside upstream gates and route checks.
Require every indivisible line to fit the selected maximum and each complete
route's canonical dialogue-only lower bound to fit its authored maximum. These
are necessary constraints, not proof of a future complete F5 schedule. F5 still
owns actual beat/cut coverage, grouping, cut/segment limits and route durations;
Bridge retains its independent production and integer-millisecond requirements.

Every read/currentness/admit/accept/save/reopen comparison recomputes current
language/profile within the exact stored optional selection. None must not turn
into eight or another default. Caller bindings cannot override stored intent.
Profile/language drift stales bound work; selecting another limit requires new
preparation. F5 context resolution preserves inherited F4 intent separately from
its own actual selected limit. Retained requests and deliveries stay unchanged.

The fixed opted-in native adapter uses checked Python plus explicitly pinned
Node/read roots, absolute frozen paths, existing offline/private runtime settings
and exactly the existing validate/render steps and ownership deadlines. Render
stdout contains report bytes only. Standalone F4 retains its existing resources.

Separately correct the runner's explicit pauseable states to include blocked,
using the existing revision-CAS command and inactive nonadopting reconciliation.
Preserve strict classification, failure and `material_qualified=False`: settled
incomplete material can never become complete_success. Pause/CAS failure remains
unresolved. Do not mutate the consumed run to demonstrate the repair.

## Alternatives and guardrails

Reject prompt-only advice, model-selected trusted timing, automatic shortening or
splitting, accelerated speech, relaxed F5 limits, an implicit global eight-second
manual cap, caller-specific validation and a speculative general scheduler.

Regress the exact retained VO as a new fixture, boundaries/Unicode/pace/language,
optional and explicit modes, forged or drifted intent and all currentness paths.
Use real provider-free F4→F5 composition and the changed sandbox command path,
including both pinned toolchains and uncontaminated render stdout. Test blocked
CAS pause, late original receipt-only collection and strict incomplete settlement.
Both failed allocations remain frozen; another paid pair requires separate review
and a fresh finite release. Source and fixture success are not native generation,
full release qualification or product acceptance.
