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

Canonical dialogue minima are integer milliseconds; raw F5 cut durations retain
their exact decimal value, including fractions of a millisecond. Receiving
compares cuts and complete-route sums using decimal coefficient/scale arithmetic,
without rounding, per-cut flooring or tolerance. ADR 0100 continues to own the
later Bridge requirement that production cuts be exactly representable as integer
milliseconds. Raw review admission must not import that production restriction.

F4's upstream JSON, configurable estimator and independent creative validation
remain unchanged. Their estimate does not replace the canonical receiving
minimum. Canonical rates, pace rules, exact source text, timings and route
ceilings remain unchanged. New F5 bindings stale earlier review bindings;
retained revisions/jobs remain readable evidence, never silently upgraded or
replayed. A new review is required to execute the current receiving contract.

The later optional prospective F4 requirement is governed by
[ADR 0179](0179-planned-script-dialogue-compatibility.md). It adds necessary
canonical feasibility checks only when explicitly selected, preserving this F5
gate and standalone F4's upstream estimator. It does not retrofit retained jobs
or promise a complete future F5 schedule.

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

Regressions preserve raw submillisecond acceptance followed by an explicit Bridge
conflict, exact minima and route boundaries on both receiving routes, and unsafe
numeric-input refusal.
