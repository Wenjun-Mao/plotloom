# ADR 0184: Validation-invocation-local profile construction

Status: Root-authorized bounded current-source implementation, October 17, 2026.
Candidate over `19793455446b327a9a2cc47146fa607e8ede22bc`; correctness and
independent review remain separate. [Scope and evidence](../roadmap/2026-10-17-profile-construction.md).

## Problem and decision

The retained current complete-pack profile records 499 assert_autopilot_contracts
calls and 26,115 direct retained checkpoint binding calls. Explicit profile
construction repeats at the attempt and creative binding sites. The expected-red
current natural-request guard validates successfully, then observes four explicit
constructions instead of one. Generic model_validate costs include other models;
these counts do not price attainable or whole-suite savings.

One assert_autopilot_contracts invocation owns one private successful-profile slot,
passed only to its direct checkpoint and decision bodies. Both retain the CURRENT
retained historical Outline callback; standalone strict and retained public helpers
stay fresh with unchanged signatures. Frames, bridges, geometry/lineage and nested
or independent invocations receive no slot. No ambient/current-context mechanism.

Reuse only for exact built-in str equality of the WHOLE freshly selected policy.
At each existing construction site keep its SELECT, JSON decode, attempt/request
reconstruction and binding extraction in their original order. Clear the slot before
binding extraction/replacement; save only a successfully validated profile. Non-TEXT
inputs construct afresh and clear prior success. A/A constructs once; A/B/A three
times. Extraction/validation failures leave no success; a malformed JSON aborts
the owning validation invocation and discards its lexical slot.

Reuse PURE CodexExecProfile construction only: frozen assignment, extra-forbidden
scalar/immutable-tuple fields and value-only validators justify sharing. A named
shape/default/validator guard and reviewed AST dependency fingerprint force a
fresh review if those assumptions change. Future mutable/ambient validation must
disable reuse or receive a revised reviewed contract. Assignment freezing alone
is insufficient.

All SQL/order/visibility, JSON decoding, binding extraction, comparison/hash calls,
receipt/attempt snapshot revalidation, filesystem/owner checks and exception
priority remain fresh. The later policy SELECT remains a distinct observation.
Do not retain validation plans, parsed requests, rows or admission authority.

## Alternatives and guardrails

Reject run/job-ID, normalized binding, profile-hash and global/session/connection
caches; eager priming from the outer parsed LaunchPolicy; and propagation into
nested consumers. The old db021699 proposal is read-only design/guard input, not
a wholesale cherry-pick; historical ADR 0177 and evidence remain unchanged.

Adapt substantive SQL/error-order, receipt, exact-text/replacement, non-TEXT,
all profile-version and transaction guards to current natural fixtures. Preserve
strict live-plan refusal versus passive retained Outline projection. Compare
independent WAL observations without forcing cursor or transaction visibility.
Keep original expected failures and native receipts. Stop with an uncommitted
scoped correctness packet for Root/independent review. Performance, full/whole
qualification, providers, commit/push/merge and product acceptance are excluded.
