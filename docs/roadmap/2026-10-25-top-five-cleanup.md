# Top-five historical storage cleanup — 2026-10-25

Status: owner-approved cleanup completed on 2026-10-25. All seven worktrees,
four historical roots and obsolete loose helpers in the approved batch are
removed. Product implementation, provider calls and service changes were outside
this storage-only scope.
The earlier cross-shot cleanup is complete and separate.

Source review began at main `016552e63c0304b79a64fd76b351d1648579fc18`;
execution source preflight used main `206a6c70`.
The owner subsequently rejected preservation based on uniqueness or hypothetical
future reuse. This revision replaces the earlier media/source-library proposal.

Aliases:

- `R`: `/Users/wjmao/.codex/worktrees/b30f/plotloom` (retained source).
- `P`: `/Users/wjmao/projects/HU/plotloom` (installed checkout).
- `W`: `/Users/wjmao/projects/HU/plotloom-worktrees`.

The existing [storage inventory](../../.local/cleanup-inventory-20261025.json)
records pre-cleanup allocations, not current availability. This plan resolves its first five review groups;
it does not replace the earlier approximately 4.2 GiB disposable-batch proposal.

## Owner's preservation rule

Preserve an item only when deletion would break a named current function, lose
owner-valued work, or prevent a concrete necessary recovery operation. State its
consumer, the actual loss caused by deletion, and its long-term practical use.

Uniqueness, original generation, money already spent, irreproducibility,
authorship, small size, audit history and unspecified possible reuse are not
sufficient. If no necessity is established, recommend disposal rather than
inventing a preservation library, archive or permanent decision hold.

A temporary engineering hold needs a specific resolution action and end
condition. It is not permission for indefinite retention. An unexpected current
dependency found during execution is investigated narrowly; it does not hold the
whole batch or justify keeping an entire historical directory.

## Approved dispositions (executed)

| Group | Allocated KiB | Main-source conclusion | Recommended disposition |
| --- | ---: | --- | --- |
| Five parked checkouts under `W` | 3,451,240 | One useful committed reader proposal; remaining dirty product changes incorporated or superseded | Remove checkouts through Git lifecycle after exact source disposition; no original-image or census archive |
| `R/.local/native-proof` | 1,945,772 | Production fixes already on main; old source copies add no missing feature | Retire isolated proof envelopes and all unused QA media, provenance, derivatives, environments and logs |
| `R/.local/remaining-cost` | 590,932 | Three optimization families incorporated; private census is defective and unaccepted | Discard the private prototype, helper copies, fixtures, profiles and historical decisions; keep the performance requirement already on main |
| `P/.local/relay` | 289,048 | No missing production source or skill; Lighthouse material is agent-authored development data | Delete obsolete media, task folders and fixture DBs; no creative-source export prerequisite |
| `R/.local/specialist-integration-20261022-preserved` | 213,760 | Specialist source already merged; archive semantically matches main | Remove old media, container images, duplicate source, browser captures and build output |

Total allocation is approximately **6.19 GiB**, without double-counting the two
linked worktrees inside `remaining-cost`. Nearly all is a retirement candidate;
there is no longer a proposed 243 MiB media collection or 0.6 MB prototype archive.
The execution result below reports actual removed allocation; it makes no
filesystem free-space claim.

## Rejected preservation proposals and why

| Previous proposal | Necessity test | Revised recommendation |
| --- | --- | --- |
| 89 native ImageGen originals and their provenance | Historical QA outputs; no current project or tracked-media dependency, selected reuse or recovery requirement was established | Delete with their proof environments |
| Other 20 historical development originals | Paid/unique source bytes do not establish a current consumer or an intended future use | Delete; leave existing current/tracked owning copies outside scope |
| 598,089-byte census/timer/helper/decision set | No current function depends on it; fault-sink control flow is defective, assumptions are superseded, and no concrete reuse plan justifies carrying it forward | Discard; do not create a preservation Git ref or archive |
| Lighthouse source and ten proposed JSON exports | Agent-authored development material, not user-supplied work or a currently adopted story; no demonstrated consumer | Delete old fixture families without exporting them |
| New plain-text UNKNOWN no-retry record | No software reads or enforces it; calling it a functional guard would be incorrect | Do not create it or retain per-attempt archives |
| Old one-shot cutback operators and copied source packets | Pinned to obsolete deployments and allowlists; no current recovery dependency was established | Delete obsolete copies/instructions; keep current functional recovery outside scope |

Discarding the private census prototype abandons that implementation. It does
not cancel the performance goal documented on main or claim the target was met.
Any future optimization should start from current contracts and measured needs.
No new private experiment, prototype resume or benchmark campaign is part of cleanup.

## What actually stays, with practical justification

| Item outside deletion scope | Current consumer / consequence of deletion | Practical use |
| --- | --- | --- |
| Current eight projects and their media/settings, plus owner-valued installations and work | Workbench/player and the owner's projects; deletion loses working content or edits | Continue viewing, playing and editing actual projects |
| Current source, validator environments and active dependencies | Running bridge/workbench, validators and development tools | Operate and maintain the current application |
| Single functional current recovery package | Current source/wheel recovery path | Rebuild or recover the working installation after a real failure |
| Five current project-revocation tombstones | Actual admission/publication guards query them | Continue refusing revoked-project work and unsafe late publication |
| Current architecture/design requirements and unresolved performance requirement already on main | Maintainers implementing supported behavior | Prevent regression and guide concrete product work without raw historical evidence |

These are functional exclusions, not permission to retain every capture, source
copy or receipt stored near them. Do not expand this cleanup into deleting live
projects, actual valued work, current guards or the only usable recovery package.

## The one useful product change: separate from cleanup

Current `autopilot_materials.initial_inventory()` still calls
`production_bridge_state().installation`, constructing proposal, presentation,
preparation and job views along the way. Main's context reuse does not eliminate
that unrelated projection work.

The committed installation-only reader proposal `11b7ad65` on existing
`refs/heads/codex/python85-release` (`76d6a916`) offers a concrete separation of
responsibilities. Recommend adapting it through the existing read lease,
project/head checks and `installation_in_session()`, adding the small store
facade and changing only the inventory caller. No speed benefit is established.

Keep only that existing ref temporarily for an explicit accept/reject decision;
create no new source archive or checkout. The resolution action is to adapt and
validate the narrow change, or reject it. End the hold when its code is on main
or the proposal is rejected. This hold does not preserve the large old checkout
and does not block storage cleanup.

If implementing, port the installation-read guards, adapt readiness stubs and
test ownership, and document the decision in the current ADR/spec indexes. Prove
missing/current/outdated installation, canonical/upstream drift, corrupt evidence,
missing project/head and fresh successive reads without review projection. Use a
disposable installed-story fixture first, then affected Bridge/rebuild/readiness
owners, independent review and one stable final local full gate before merging
product code. No live project/provider work or GitHub CI is needed. Implementation
is separately optional; approval of storage cleanup alone does not authorize it.

## Reviewed parked source dispositions

| Checkout | Evidence | Disposition before removal |
| --- | --- | --- |
| `W/autopilot-ux-release` | Dirty encoded-row/material-byte/hash/receipt mechanisms and tests are incorporated; main has later processed-Result and snapshot-scoped reuse | Discard superseded dirty proposal |
| `W/pre-video-autopilot` | 185 of 188 added nonblank plan lines already on main; remaining three call completed work unapproved | Discard stale plan delta and unused development media |
| `W/python85-baseline-timing` | Clean; revision reachable from main | Remove checkout |
| `W/python85-profiling` | Three commits patch-equivalent; `e4948ac3` executable changes incorporated by `da4bf5b3` and later owners | Remove checkout; no source merge |
| `W/python85-release` | Only the committed reader proposal is useful; dirty command-transaction optimization and authority tests are incorporated | Retain temporary proposal ref; discard superseded dirty changes |

Recheck exact tracked/untracked status before forced worktree removal. If a new
change appears, identify its actual owner/value before deleting it; investigate
that path without creating a blanket archive of the checkout.

## Historical UNKNOWN envelopes

The three private historical UNKNOWN supervisors are absent from installed host
attempts/revocations. Installed state at inspection was 85 attempts (82 completed,
3 settled), zero UNKNOWN, queues, slots and validators. The five actual current
revocation tombstones are a separate functional dependency and remain intact.

Verify the private target envelopes still have no process, open handle, mount,
publication consumer or resumable owner. Retire those isolated execution roots
and their obsolete helper/replay paths together. Do not initialize or migrate old
supervisors, inject their rows into current accounting, retry old jobs, or claim
remote outcomes became known merely because their local data was deleted.

No new ledger, tombstone catalog or per-attempt no-retry document is needed when
no current mechanism consumes it. Existing narrative can truthfully say the old
QA envelopes were retired with remote outcomes unknown. If execution discovers
an actual live consumer, defer only that concrete dependency and resolve it
through the supported lifecycle; do not fabricate settlement or clear a live hold.

## Approved batch order and acceptance

1. Owner approval received for the explicit revised scope, including discard of
   unused development media and the defective private census implementation.
   Investigation and proposal revision themselves performed no deletion.
2. Take a fresh current-project/settings/host/runtime baseline and recheck exact
   target identity, source status, consumers, quiescence and no-follow boundaries.
   Existing current dependencies stay excluded. Do not create new preservation
   collections, bulk archives, creative exports or census preservation commits.
3. Verify the reader proposal remains reachable by its existing temporary ref;
   remove registered linked worktrees with Git's lifecycle after reviewed dirty
   disposition. Handle embedded repositories and zero-byte uv cache markers
   according to their actual ownership, not their `.git` name alone.
4. Prove a small ordinary disposable-fixture removal, then retire isolated proof
   envelopes, old helpers and the rest of the five groups. The 24 loose paths in
   the inventory's `source-proof-helpers` group are finite external candidates;
   remove those whose consumers are wholly retired here. Keep current snapshot
   tools, validator setup and any demonstrated live consumer.
5. Retire stale artifact links and obsolete launch/cutback instructions. Preserve
   useful current contracts/decisions and truthful outcomes in existing docs;
   remove redundant historical detail rather than creating a new audit store.
6. Verify current project/media/settings and actual host guards against baseline;
   verify validator identities, runtime configuration/consumers, HTTPS health and
   functional recovery. Classify legitimate user edits or unrelated restarts;
   never overwrite newer user data or restart healthy services just for a check.
7. Report actual removed allocation and any narrowly justified exception. Every
   exception must name a practical consumer, deletion consequence and resolution
   action. No indefinite “might be useful” hold or repeated milestone approval.

No generation, paid provider operation, prototype resumption, deployment, push or
GitHub CI is part of this cleanup. Storage-only deletion does not require product
release tests; run checks appropriate to any actual code change separately.

Independent necessity review (requested GPT-6.1 Sol / Medium; effective settings
unverified) confirmed that the former media/source/export proposals had no
established preservation case and that a plain-text no-retry note was not an
enforced safety mechanism. The revised plan removes those prerequisites.

## Execution result — 2026-10-25

The manager removed all five parked checkouts and both nested linked worktrees
through Git's worktree lifecycle. All four approved historical roots are absent:
`R/.local/native-proof`, `R/.local/remaining-cost`, `P/.local/relay` and
`R/.local/specialist-integration-20261022-preserved`. The 24 obsolete loose helper
paths and one associated `exec_validator_sandbox_probe.pyc` cache were removed.
The target/helper/cache census covered 137,501 regular files, 911 symlinks,
6,232,827,567 logical bytes and **6,491,076 allocated KiB (approximately 6.19 GiB)**.
This is removed-file allocation, not a promise of filesystem free-space gain.
The earlier approximately 4.2 GiB disposable batch is separate and unexecuted.

The smallest ordinary disposable-fixture removal passed preservation checks
before the full batch. Fresh checks after full removal matched the baseline
exactly: eight current projects, 672 project tables, 263 persistent files, all
application/host tables, 15 protected fingerprints, both checked validator
environment identities, runtime/bridge identities and functional recovery files.
Host accounting remains **85 attempts: 82 completed, three settled, zero UNKNOWN**;
queues, slots and validators are zero. All five functional revocation tombstones
remain unchanged. No healthy service was restarted and no newer user data was
overwritten.

The three isolated historical UNKNOWN envelopes were retired locally with their
remote outcomes still unknown. They were not installed host attempts, and no
settlement, current reservation release, replay or provider outcome is inferred.
No QA images/provenance, private census prototype, Lighthouse exports, new UNKNOWN
record, archive, library, preservation commit or new ref was created. The sole
temporary source exception is the existing `codex/python85-release` ref at
`76d6a916`, with reader proposal `11b7ad65` still an ancestor, for the bounded
accept/reject action above. It does not retain a checkout or establish a speedup.

Documentation retirement removes artifact links and obsolete operational holds,
while retaining current ADR/API contracts, useful performance requirements and
truthful historical pass/failure limits. Repeated raw log/hash inventories and
one unconsumed process snapshot were removed. Remaining old path identities are
explicitly historical, not available artifact links or current launch procedures.
Independent read-only review found no current-contract, failure-limit or design
loss; its present-tense evidence/hold wording findings were corrected. Changed
local links and the diff were checked. No product, test, build, provider, hosted
CI or push operation occurred; storage-only cleanup required no product test run.
The manager owns the subsequent functional-recovery refresh and installed-doc
synchronization, separately from this tracked documentation checkpoint.
