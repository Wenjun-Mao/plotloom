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

### Nullable observed version review (2026-10-17)

ADR 0165 makes the observed CLI version optional metadata. The reviewed AST
tripwire correctly refused that model change during final qualification.
Root and independent review compared every named dependency: the only changed
member is `cli_version`, now an immutable `str | None` with literal `default=None`.
No factory, validator, mutable container, ambient lookup or I/O was added to
model construction. Credential checks, frozen assignment and profile hashing
remain value-only. The actual subprocess version observation is outside this
construction slot and is never reused by it.

Re-review therefore retains the same reuse boundary and updates its AST pin.
Explicit null and omitted metadata regressions must match fresh validation,
reuse only identical whole policy text, and replace on different policy text
even when the resulting profile values and hashes are equal. No normalized-key,
hash-key or runtime-observation reuse is introduced.

### Optional bounded correction limit review (2026-10-21)

ADR 0202 adds only `text_correction_limit`: an immutable `int | None`, literal
`default=None`, strict numeric bounds of one, and a value-only exclusion of None
from serialization. Root and independent review compared every named AST
dependency; no factory, validator, mutable field, ambient lookup or I/O changed.
The final full gate correctly tripped the old fingerprint. Re-review retains the
same lexical reuse boundary and updates the pin, not the construction mechanism.
Null, omitted and one regressions compare fresh construction/hash results, reuse
only exact whole TEXT, and clear prior success on invalid bool/zero/two replacement.

## Alternatives and guardrails

### Versioned diagnostic capability review (2026-10-22)

ADR 0203 adds only `text_correction_contract`, an immutable optional Literal of
`plotloom.text-correction.v2`, literal None default and value-only omission of
None. Root and independent review confirmed all other named AST dependencies
and `_ProfileConstruction` unchanged: no factories, mutable fields, ambient state
or I/O were introduced. The lexical reuse boundary is retained. Omitted/null/v2
construction/hash and exact whole-TEXT replacement checks, plus invalid literal
and bool replacement clearing, guard the reviewed pin update.

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


### Prospective Script capability value review (2026-10-26)

ADR 0202/0222's delegated Script extension admits the additional immutable literal
`plotloom.text-correction.v3` in the existing optional capability field. The writer
compared named dependencies and the lexical construction owner: only that literal
union changes; default None, scalar immutability, exclusion, validators and all
other dependencies remain value-only, without new state, factory or I/O. Update
the AST tripwire while preserving every shape/replacement assertion. Existing v2
values remain readable with their original three-stage meaning; Script requires v3.
Fresh v3/null/omitted construction and exact-text/hash replacement checks join the
existing guards. Independent review of this pin/assumption update remains part of
the stable Script source checkpoint, before any new native admission.

### Prospective Storyboard capability value review (2026-10-27)

ADR 0222's independently reviewed prospective decision adds only the immutable
`plotloom.text-correction.v4` literal to the same optional field. Full named AST
comparison against `5c60d508` confirms that every other field/default/validator and
every named pool/base/public-value dependency is unchanged. The lexical
`_ProfileConstruction` owner is byte-identical. There is no new factory, mutable
field, ambient state or construction I/O. Keep the same exact whole-TEXT reuse,
replacement/clearing and fresh-validation boundary; update its reviewed AST pin
and extend omitted/null/v2/v3/v4 and invalid replacement tests. Stage authorization
remains outside model construction: v3 retains Script, v4 alone adds Storyboard.
The writer's bounded comparison is retained in
`.local/b37/resumed-integration/storyboard-profile-purity-review.json`; independent
review of this assumption/pin update remains part of the stable source checkpoint.
