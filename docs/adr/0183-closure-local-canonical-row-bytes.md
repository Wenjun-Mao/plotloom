# ADR 0183: Closure-local canonical row bytes

> Local QA artifact references below are historical; the [2026-10-25 cleanup](../roadmap/2026-10-25-top-five-cleanup.md)
> retires their storage, replay/launch/cutback instructions and preservation holds.
> Recorded outcomes and limits remain; current ADR/API contracts still apply.

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

The affected result (retired local artifact)
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

The first pair (retired local artifact)
has SHA `4b254e56cc49123bb053094e6bb53f52c0fdb4c85e0c5214fa696465aae198c2`;
the reversed pair (retired local artifact)
has SHA `b4b7285a6222b36152db76c6eb3cbc5f11b783fcca533af4162c1cad67b39527`.
Their original receipts, logs, commands, pins and earlier manifests were sealed
at their actual sources at that checkpoint and subsequently retired by the
approved cleanup. A local checkpoint commit does not upgrade those outcomes.

## Fresh Result row adapter — October 17, 2026

Root separately released a bounded adapter candidate on clean `4a61133f`.
Installed SQLAlchemy 2.0.52's Result iterator already creates processed Row
values; MappingResult adds RowMapping, whose items() allocates a list/view and
does per-key lookups. In _material_payload only, capture each fresh Result's
ordered keys once and pair them with its ordered processed Row values. The
single-Table projection has named unique columns and fixed-width rows; strict
pairing asserts that existing shape. General ambiguous projections are excluded.

This changes local adapter allocations, not the database observation contract.
Keep every fresh execute/SELECT/table/predicate, flush and cursor consumption,
datetime normalization and complete-values-list-before-encoding phase. Keep
canonical JSON/UTF-8/errors, digest-only stable ties, protected-before-extras and
subsequent call/command freshness. No cross-row/call value memoization, prepared
query/schema cache, serialization deduplication, alternate snapshot or public
signature change. B remains unapproved and separate.

ByteSession/ProjectionSession now expose Result.keys()/ordered values. Synthetic
byte-grammar rows have explicit complete result columns, with explicit nulls
where an earlier fake omitted a column. Those artificial result fields are not
claimed to be production schemas; real-database old-mappings versus new-row
byte/SELECT parity covers every actual material table and empty result metadata.
Keep all earlier Unicode/nested JSON/null/number/datetime/tie/unsupported-value and
phase/error assertions. Add fresh result-owned metadata, no mapping/key-lookup,
metadata failure, and nested independent pending-write guards. No production
fallback accommodates an obsolete fake protocol.

Correctness closeout: six new guards and 41 complete byte/receipt owner cases
passed (47 prior focused cases), followed by the exact retained six-file affected union: authority, claim
transactions, geometry, image safety, late receipts and verification ownership.
That union passed 96 cases, for 143 distinct focused cases across nine files.
Scoped F/I, syntax, static ownership and diff checks passed. The
union receipt (retired local artifact)
retains exact full IDs, original native terminal and unchanged source/QA pins.

One separately released natural complete-pack pair passed the unchanged case
once per arm: control 43.038875542s, candidate 42.129494000s for the whole pytest
command plus immediate owned settlement. The observed 0.909381542s / 2.11293%
shorter candidate is a modest screen, with fixed control-first order, shared
OS/dependency caches and host-load limits. Both used fresh roots/UV caches and
disabled pytest cacheprovider. Separate import probes do not establish loaded
module origin in the pytest child. The
pair receipt (retired local artifact)
does not establish causal/statistical or whole-suite savings, an 85-percent goal,
full release qualification or product acceptance. No repeat/reversed pair ran.

The accepted base `4a61133f` whole observation remains historical evidence:
2,985 cases / 257 files in 814.730342s against the unchanged 151.73295s target,
which remains OPEN. This adapter candidate has no whole/full or hosted CI
qualification. Root retained it as a modest idiomatic increment after independent
source/method review; the doc-closeout successor remains uncommitted pending Root
review. No further run, provider work, commit/push/merge or cleanup is released.
B remains Park; publication C3 is excluded and still requires separate authority.
