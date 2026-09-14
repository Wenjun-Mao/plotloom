# 0042: Persistence capability composition

**Status:** accepted

## Context

The package move left `SQLiteRepository` as both the retained runtime surface
and a service locator for authoring, media, and application-control policy.

## Decision

`SQLiteRepository` composes explicit project access contracts, project media,
application profile, and pilot-accounting capabilities. Authoring collaborators
receive named leases, row guards, and codecs rather than the repository. Media
owns project facts; application control owns provider profiles/settings and the
Wan pilot ledger. Accounting receives the caller's lifecycle transaction so a
project video job and its reservation still commit atomically.

`ProjectSQLiteRepository` is defined in `persistence/project/repository.py`;
its ID and admitted-profile guards and the public import remain unchanged.

## Consequences

No table, migration, hash, transaction lease, public signature, or storage
ownership changes. `legacy_repository.py` is now compatibility composition.
The cohesive media lineage capability is 2,500 lines because its still, review,
reference, production, and video operations share currentness/admission
predicates. The 668-line application profile/control capability likewise keeps
the active-profile/settings projection atomic. Split either only on those
proven transaction boundaries in a separately approved change, without
reintroducing facade bounce-backs. The 1,529-line retained facade is an
intentional compatibility surface while runtime callers still import it; a
caller-migration proposal must define its retirement before further line-count
work is attempted.
