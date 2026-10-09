# ADR 0147: Narrow owned pinned report renderers

Status: accepted by the owner, 2026-10-09; fork adoption and qualification pending.

## Problem and ownership

Art validation receives Cast context, but its report renderer does not, so the
report can falsely describe contextual checks as skipped. Storyboard copy uses
hardcoded duration limits and describes proposed downstream work as executed.
Outline's raw fractional-minute display becomes awkward at supported desktop
widths. These defects belong to the report-generation source, not HTML overlays.

## Decision

Own a narrow Apache-2.0 fork of `eternityspring/shuohao-skills`, based on the
currently qualified pin `4322897e6d2bdaf66365534fd40194360c75a85f`.
The authenticated owned destination is `Wenjun-Mao/shuohao-skills`; it has not
yet been created. Do not adopt upstream's later breaking release in this repair.
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

Verify fork ownership/parent, clean submodule HEAD equal to the parent gitlink,
license attribution, affected upstream selftests and Plotloom context/style/pin
checks. Test Cast contamination and valid contextual gates, alternate duration
limits, truthful execution wording, unchanged JSON and all three desktop sizes.
Requalify new execution pins and explicitly rebuild affected dependencies where
their existing hash contracts require it. No provider dispatch or creative
acceptance follows automatically from a renderer correction.
