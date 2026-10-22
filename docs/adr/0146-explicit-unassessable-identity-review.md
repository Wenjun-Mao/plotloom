# ADR 0146: Explicit unassessable identity review

Status: accepted by the owner, 2026-10-09; implemented and independently source/
pixel reviewed in the retained candidate; isolated served-build qualified;
native HOLD → explicit AUTHORIZE → exact frozen H3 → original/segment and revised
route playback qualified in the disposable Board3 run. Creative/audio acceptance
remains separate.

## Problem

The revised Opening2 shot intentionally shows only hands. Its frozen framing
must not be changed merely to make identity assessable. The existing PASS/FAIL
contract correctly refuses production after its failed review, but offers no
truthful way to accept the uncertainty of intentional nonidentifying framing.

## Decision

Allow a distinct explicit reviewer judgment, `unassessable`, alongside `pass` and `fail`.
Unassessable is not PASS. It requires an explicit separate choice to hold or
authorize production, plus a nonblank explanation of the intended framing and
accepted identity uncertainty. Untouched controls or missing fields never
authorize anything. Bind the decision to the existing exact selected image,
frozen shot composition, character references and current source dependencies;
do not infer observability from model prose, shot size or character membership.
Record the actual reviewer. A Codex functional or visual check is not a human
author's creative acceptance and must not be attributed to one.

Separate source currentness from production eligibility. Every involved
character must have either PASS or explicitly authorized unassessable judgment.
FAIL and HOLD block still preview and H3. Use the latest applicable decision for
the exact binding, never search backwards for an older PASS after a newer refusal.
New previews/videos freeze the immutable review ID and subsequently check both
currentness and eligibility. UI wording must identify uncertainty and explicit
authorization, not claim that identity passed.

Preserve original review and media bytes. Existing PASS/FAIL judgments retain
their meanings without an adapter. Opening2 needs a fresh explicit review; its
old FAIL cannot be converted automatically. This supersedes the unresolved
policy boundary in ADR0143 and extends ADR0030, without granting artistic
acceptance, changing the requested crop or weakening other production checks.

## Guardrails

Reject missing authorization/reason, untouched forms and mixed-character
FAIL/HOLD. Test latest-decision supersession, stale Cast/reference/image/binding
dependencies and frozen review IDs. Native acceptance must demonstrate the
actual refused-to-explicitly-authorized transition, one exact frozen H3 request
and playback; automated tests alone do not close that journey.

## Implementation

Each unassessable comparison records `productionDecision` (`hold`/`authorize`)
and nonblank `uncertaintyReason`; PASS/FAIL retain their existing comparison
shape. The API and repository validate the same domain contract. No database
schema migration or historical rewriting is needed: comparisons remain immutable
JSON facts, and existing FAIL remains FAIL.

Review `current` means exact source dependencies match, including candidate
original hash, binding/intent/approval, Cast and references. `latest` identifies
the latest applicable exact-binding decision; `productionEligible` additionally
requires every character to pass or explicitly authorize uncertainty. Frozen
previews/videos retain their exact review ID and require that ID to remain the
latest eligible review. A newer refusal disables older media without changing
its receipt; video `inputStatus` can remain current while production eligibility
is false. A fresh approval creates fresh media rather than rebinding history.

UI judgments and uncertainty decisions start unselected. A successful unchanged
GET preserves authored fields; temporary read withdrawal cannot reset them or
authorize operations. Exact changed targets reset the comparisons. Source
qualification and remaining native boundaries are recorded in the
[scoped receipt](../verification/2026-10-09-explicit-unassessable-identity-review.md).
The actual hand-only transition and native chain are recorded in the
[Board3 continuation](../verification/2026-10-09-review-bound-bridge-and-board3-media.md).
