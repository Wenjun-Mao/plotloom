# ADR 0173: Freeze canonical dialogue minima at F5 admission

Status: accepted for the bounded serial-executor repair, 2026-10-14.

## Problem and evidence

The stopped `596c2213` proof delivered eight valid text candidates but could
not install its Bridge. After the exact VO projection correction (ADR 0172),
read-only projection still rejects a 6,500 ms shot containing a 24-character
VO line whose canonical estimate is 7,920 ms. Retained bytes and budgets remain
unchanged.

Pinned F4 `sceneSeconds` and F5 `expandScript` count non-whitespace characters,
including punctuation, at Script `params.charsPerSecond` (default 4.5), rounded
to tenths of a second. Neither selects spoken language or delivery pace. The
retained line therefore occupies 5.3 upstream seconds; F4's two action beats
bring its estimate to 10.3 seconds against target 10.5, and F5's 6.5-second cut
passes upstream dialogue fit. Report `lang: en` controls report labels.

Canonical timing instead uses saved story language `zh-CN`, the versioned
`dialogue.default.v1` profile and `natural` pace for free-form performance
notes. It counts stripped Unicode codepoints, including internal whitespace,
at 330 ms each. Bridge preserves exact F5 milliseconds and correctly refuses
the undersized shot. The missing requirement belongs to F5 receiving admission.

## Decision and ownership

One trusted Python helper owns F4-to-canonical delivery normalization and
timing estimation, shared by Bridge and fresh F5 preparation. Fresh F5 binds
a versioned timing contract to accepted Script identity and saved spoken
language, with exact source episode/scene/flow coordinates, source text hashes,
selected pace and integer-millisecond minima. The model authors cuts and H3
directions; it does not author these minima or rewrite source dialogue.

F5 instructions expose this contract. Both saved-Brief and preset/manual
validate/render paths enforce it alongside every original upstream gate,
frozen cut/segment limits and complete-route maximum. Every dialogue flow
item must have exactly one cut owning its beat; a cut must fit the sum of its
owned dialogue minima, matching canonical cue assignment. Missing, changed
or malformed timing inputs fail closed. An individual line that cannot fit
the chosen maximum is rejected before fresh F5 dispatch.

F4's upstream JSON, configurable estimator and independent creative validation
remain unchanged. Their estimate does not replace the canonical receiving
minimum. Canonical rates, pace rules, exact source text, timings and route
ceilings remain unchanged. New F5 bindings stale earlier review bindings;
retained revisions/jobs remain readable evidence, never silently upgraded or
replayed. A new review is required to execute the current receiving contract.

## Alternatives and guardrails

Changing canonical rates to match upstream defaults changes existing production
semantics. Rewriting narration, stretching retained cuts/budgets, excluding VO,
or weakening timing checks destroys source or evidence integrity. Prompt-only
guidance does not enforce the receiving requirement. These are rejected.

Regression coverage includes VO and mapped speakers, report versus spoken
language, supported pace versus free-form notes, Unicode and whitespace,
multiple dialogue beats in one cut, exact boundaries, missing/drifted contracts,
both validator routes and real proposal/install/reopen admission. Qualify the
changed F5 command plans in the actual provider-free sandbox before a new
disposable provider proof. Preserve the stopped proof and old native evidence
under their original pins.

## Raw F5 precision clarification — 2026-10-15

The owner explicitly chose to preserve ADR 0100's raw-review precision boundary.
The initial receiving implementation converted every source cut to integer
milliseconds, including action-only cuts; the retained submillisecond integration
regression exposed that unintended restriction. Integer-ms dialogue minima
constrain a comparison, not the precision of the model-authored cut duration.

Both receiving routes interpret each finite JSON number's decimal value exactly,
including exponent notation, and use decimal integer coefficients/scales for
cut/segment/route sums and comparisons against frozen limits and canonical
minima. No rounding, binary floating-point summation, epsilon or empty-dialogue
bypass establishes receiving acceptance. All original upstream gates, binding,
source ownership and exactly-once dialogue assignment checks remain required.
Raw source bytes are not rewritten. Exact conversion to positive integer
milliseconds remains a separate, unchanged Bridge/provenance requirement under
[ADR 0100](0100-reviewed-production-presentation.md): raw F5 may accept `2.5001`
seconds, then Bridge must expose `cut_duration_invalid` and refuse installation.

Moving representability rejection into F5 would change the preserved review
contract and is rejected for this repair. Retained failed observations, jobs and
packages remain under their original source identities; this clarification does
not relabel them as satisfying the corrected receiving contract.
