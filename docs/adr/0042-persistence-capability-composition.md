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

## Correction (pending director review)

The earlier consequence text treated the 2,500-line media capability and the
668-line profile/control capability as accepted exceptions. The director
rejected that exception: sharing currentness predicates or a transaction is not
enough to combine unrelated policy owners.

The correction keeps `legacy_repository.py` as the sole retained runtime
compatibility composition surface. It delegates directly to fixed, typed media
owners for managed assets, visual intent, keyframe admission, reviewed
selection/preview, character-reference decisions, reference proposals/delivery,
same-person reviews, image-job currentness/preparation/delivery, video
currentness/lifecycle, and generic media tasks. `project/media.py` is now only
the 72-line typed construction root for those owners; it carries no public
delegation or policy. Application control is divided into pure value conversion,
bootstrap, profile catalog, profile admission, and the settings projection
owner. The settings projection remains one transaction; video accounting
continues to receive the video's existing lifecycle session. No cross-capability
owner opens a second lease.

This correction changes no table, migration, hash, transaction lease, public
signature, or storage ownership. It is an implementation candidate and does
not itself claim director acceptance. The 1,538-line retained facade remains a
documented compatibility exception while runtime callers still import it; a
caller-migration proposal must define its retirement.
