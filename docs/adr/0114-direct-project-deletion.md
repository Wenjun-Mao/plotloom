# 0114 Direct project deletion

Status: Accepted, 2026-10-04.

## Problem and evidence

The directory exposes permanent deletion only after Archive; a closed project
must even reopen before reaching it. The production folder registry also
retains a media-free guard from the earlier conservative deletion contract.
Current production media, run evidence, drafts and canonical content are owned
inside one manifest-resolved project home. Erasing that complete home does not
require row-by-row deletion or removal of shared media. See ADRs 0040 and 0047.

## Decision

Expose **永久删除** directly on every supported directory row, independently of
Archive and Close. Require explicit DOM consent and exact full-title entry.
Freeze the target identity, canonical project revision and lifecycle revision;
the server checks both revisions and the title under the exclusive project
lease. A changed Brief or lifecycle needs fresh inspection and consent. The
project revision is not a global revision of every draft or media record.

The project-folder layer owns whole-project erasure. It can erase an active,
archived or closed home only after the existing quiescence scan proves no
active or uncertain external publication remains. Media-bearing homes are
eligible because all their bytes and history are confined to that home.
Validate the exact outputs-root child, unchanged manifest and held lock before
removal. Recursive removal must not follow links into external originals or
other projects. Withdraw the manifest before recursive removal can unlink the
operation lock; late openers must not admit a partially erased home.
Application-side disposable indexes and lifecycle reservations
are removed together; provider settings and financial accounting stay intact.

The consent warning includes authored text, drafts, images, videos and generation
history, irreversibility, and the exclusion of external originals and exported
snapshots. No implicit archive, reopen, generation, job cancellation or creator
acceptance precedes deletion. Failed admission retains local input. Successful
erasure abandons only the deleted project's local writers; a different current
workspace remains untouched. Project-scoped cache erasure is independent of
writer registration, and notifies every live media-cache consumer: an editor
for another project must not rewrite erased entries from a stale whole-cache
snapshot. Errors never promise that irreversible filesystem
work rolled back or that an unknown outcome is complete.

This supersedes ADR 0047's archive-first/media-free public deletion restriction.
The row-only persistence primitive is not a whole-folder eraser and retains its
own media protection; production deletion does not use it. No compatibility
mode, shared-media garbage collector, automatic backup or automatic purge of
unrelated copies is introduced. Filesystem erasure remains intentionally
irreversible, not a cross-database/filesystem rollback transaction.

## Guardrails and follow up

Regressions cover active/archived/closed deletion, media and identical bytes in
another home, external originals, snapshots, stale revisions/title, held leases,
prepared/uncertain jobs, consent cancellation and workspace isolation. Test
mutation uses disposable fixtures only; the creator's two projects are preserved.
The Chinese manual stays deferred. A broader read-only review of older contracts
against the current runtime is a proposed follow-up, not authority for this slice.
