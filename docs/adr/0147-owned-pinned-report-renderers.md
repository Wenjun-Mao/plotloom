# ADR 0147: Narrow owned pinned report renderers

Status: accepted by the owner, 2026-10-09; fork implemented, independently reviewed
and published; current parent integration and software qualification complete.
Board3 dependency rebuild and native playback are qualified, but its immutable
Storyboard report remains frozen at the earlier266af294 pin, not native execution
evidence for4f9b2128. The later [current-pin native report check](../verification/2026-10-09-current-pin-native-report.md)
qualifies one real4f9b2128 delivery and its read-only presentation, then cancels
that optional replacement without changing accepted content or media.

## Problem and ownership

Art validation receives Cast context, but its report renderer does not, so the
report can falsely describe contextual checks as skipped. Storyboard copy uses
hardcoded duration limits and describes proposed downstream work as executed.
Outline's raw fractional-minute display becomes awkward at supported desktop
widths. These defects belong to the report-generation source, not HTML overlays.

## Decision

Own a narrow Apache-2.0 fork of `eternityspring/shuohao-skills`, based on the
currently qualified pin `4322897e6d2bdaf66365534fd40194360c75a85f`.
The verified owned destination is `Wenjun-Mao/shuohao-skills`, a fork of the
expected upstream. Initial published pin `266af294da035324139202235430ffd68f5b877d`
is on `codex/plotloom-report-context`. The evaluated/skip correction is published
at `4f9b2128c82adf623f594ba714c97d0afcfc16a2` on
`codex/plotloom-evaluated-report-gates`; no later breaking release was adopted.
Keep an exact published commit as the parent submodule gitlink. Preserve legal
notices and prominently identify modified files and fork provenance.

The bounded delta is:

- Art: an explicit Cast-bearing render context, shared with validation. Keep
  structural gates and original candidate JSON; no report-string replacement.
- Storyboard: derive displayed limits from frozen parameters and distinguish
  proposed segments/batches/reference use from actual Plotloom execution.
- Outline: readable duration formatting and wrapping, without changing raw
  numeric parameters, exported JSON, aggregate-estimate meaning or gate results.

Update current callers/CLI/selftests together; do not add a legacy-signature
adapter. This intentionally supersedes ADR0094's no-vendor-edit restriction for
these owned changes only. ADR0057/0065/0086 still govern frozen source, delivery
provenance and explicit review. Retained reports remain historical originals;
fixes apply to newly generated reports. A new pin or adapter hash must not be
silently substituted into old requests, accepted content or media bindings.

## Guardrails and consequences

The subsequent E22 audit reproduced a presentation-contract defect: `ok`
represented non-blocking admission, so skipped checks appeared as executed passes.
Each gate now also carries required boolean `evaluated` metadata from its owning
applicability condition; `!evaluated` requires `ok`. Reports and CLI summaries
count executed/pass/failure/skip independently, with neutral skipped-row markers.
Admission rules, gate IDs, candidate JSON and historical logs remain unchanged.
Missing optional inputs are not inferred from localized detail strings; supplied
empty inputs are evaluated. Historical log statistics describe no recorded
failures, not execution of every gate. Storyboard's duration KPI explicitly sums
all entries and does not imply one complete playback route.

Presentation helpers stay local to independently copyable skills, rather than
introducing cross-skill imports. A byte-parity regression protects their common
contract. There is no old-result adapter or automatic accepted-report rewrite.
The correction requires a new published pin for future frozen deliveries;
earlier reports keep their original pin, bytes and truthful audit limitations.

Verify fork ownership/parent, clean submodule HEAD equal to the parent gitlink,
license attribution, affected upstream selftests and Plotloom context/style/pin
checks. Test Cast contamination and valid contextual gates, alternate duration
limits, truthful execution wording, unchanged JSON and all three desktop sizes.
Requalify new execution pins and explicitly rebuild affected dependencies where
their existing hash contracts require it. No provider dispatch or creative
acceptance follows automatically from a renderer correction.
