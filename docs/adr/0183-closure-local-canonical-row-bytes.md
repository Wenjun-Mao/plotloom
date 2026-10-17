# ADR 0183: Closure-local canonical row bytes

Status: bounded trial statically accepted by Root, October 17, 2026. Current-source
integration passed the initial 41-case focused check and one separately released
96-case affected-owner union. Performance, broader qualification and product
acceptance remain separate. Root chose to retain this bounded mechanism after
the two natural-case screening orders below; the local checkpoint records scoped
correctness and screening, not full/current native or product qualification.

## Problem and decision

Material closure encodes each freshly normalized row for its SHA-256 sort key,
then serializes it again in the aggregate. Receipt construction repeats the
protected rows in both protected and full aggregates. Retaining sort digests
alone cannot remove aggregate serialization.

Keep canonical row bytes in a private immutable table-array wrapper inside
`autopilot_closure.py`; the aggregate consumes those bytes directly. The lifetime
is one fresh closure construction, including its protected/full receipt hashes.
No bytes or rows survive into another invocation or command segment. Generic
hashing, persisted bytes, SQL, transaction/admission authority and filesystem
checks stay unchanged. Reject a generic serializer, digest-only aggregate or
cross-call cache.

Consume and datetime-normalize every row of a table before encoding any of its
sort keys. Encode/hash in original row order, stable-sort by digest alone, then
finish the table before the next SELECT. Preserve flush, selected columns and
predicates, duplicate/subset/empty tables and protected comparison before
managed-assets/extras reads. Geometry sorting and cancellation queries retain
their existing owner and order.

Ordinary extras finish stdlib JSON serialization before aggregate UTF-8 encoding.
Only on UnicodeEncodeError, reconstruct complete JSON text and encode it as one
stream, preserving the original exception input/offsets and JSON-error priority.
The healthy path directly joins already-encoded row bytes.

## Provenance and guardrails

This ports the bounded proposal from Python HEAD
`91871f4b01b0742aa99e0b3fb2b4e0aeb53f49ef`, candidate diff SHA
`efb4c5c69775b74a378a414ecbf1b9a8b961a0a569096beba6fbd55801361c7f`,
onto accepted CLI docs base `e3dc802cef837e1f0a2f3f5071ecff7fcb140ef8`.
The old proposal and evidence remain unchanged. Its other optimizations and ADR
identities are not transplanted or represented as current-source acceptance.

Independent stdlib complete-byte oracles cover numeric/Unicode/escape/datetime
behavior, table subsets/duplicates, digest ties, phase/error ordering and fresh
receipt calls. Existing receipt output, SQL, refusal, pending-write and rollback
assertions remain; aggregate failure injection follows the private hash owner.
First run only these two owners. A byte/error/read mismatch requires diagnosis;
fewer encodings alone establish no useful end-to-end gain. Measure separately
only after correctness, using unchanged natural workflows and a current matched
baseline. The 151.73295-second whole-Python target remains unproved.

## Executed focused checkpoint

The initial 25 byte guards and 16 receipt-projection cases passed through locked,
no-sync `verify.py focused`. Root verified original session 8318's natural exit0
and collected an independent source review accepting the bounded current contract.
The unchanged executable candidate then passed the complete authority, claim,
geometry, image-safety, late-receipts and module-ownership files: 96 cases, one
Starlette/httpx deprecation warning, original session 37431, natural exit0 within
the 1,200-second deadline. Both launched groups were absent at immediate terminal;
selected source hashes stayed unchanged. The first 41 cases were reused.

The [affected result](../../.local/remaining-cost/canonical-row-bytes-current-20261017/affected-union-result.json)
has SHA `8c77a281361ad53d730a514305b3ca26842c4d50fdf682714783afb961d11bc2`;
its sibling original native receipt and log retain exact commands and pins.
Fixed QA metadata, explicit environment/PYTHONPATH and source hashes bind this
focused evidence; same-pytest-child module attestation and global host/process
silence are not established. This successor documentation does not change tested
executable bytes or retarget earlier manifests. No further runtime ran for docs.
No full gate, benchmark, provider execution, release or product acceptance follows.

## Retention screening and decision

The unchanged natural complete-pack case retained all 8 text, 29 image, 27 frame,
two-route, human-fact and registry assertions, with its existing fake host.
One control-first pair and one separately released reversed pair passed:

| Order | Control whole / pytest seconds | Candidate whole / pytest seconds |
| --- | --- | --- |
| Control then candidate | 49.71917320904322 / 46.89 | 46.9363840839942 / 44.16 |
| Candidate then control | 49.107580375042744 / 46.36 | 46.68832533399109 / 43.77 |

Whole-command clocks include the focused runner and immediate owned-group
settlement. Preparation, source/QA probes, extraction and final parent removal
are outside; copies and parents remain retained. Exact source/QA endpoints
matched in all four natural passes. The observed direction survives reversal;
the two modest differences do not establish attribution, variance or whole-suite
savings. Cache history, roots and generated IDs remain limits; no same-pytest-child
or global silence guarantee is added. Root retains the mechanism as an incremental
optimization; no more one-case repetitions are selected. The fixed target stays open.

The [first pair](../../.local/remaining-cost/canonical-row-bytes-screen-20261017/pair-result.json)
has SHA `4b254e56cc49123bb053094e6bb53f52c0fdb4c85e0c5214fa696465aae198c2`;
the [reversed pair](../../.local/remaining-cost/canonical-row-bytes-reversed-screen-20261017/pair-result.json)
has SHA `b4b7285a6222b36152db76c6eb3cbc5f11b783fcca533af4162c1cad67b39527`.
Their original receipts, logs, commands, pins and earlier manifests remain sealed
at their actual sources. A local checkpoint commit does not upgrade that evidence.
