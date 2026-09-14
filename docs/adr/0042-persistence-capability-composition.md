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

## Correction (director accepted)

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
signature, or storage ownership. The director accepted and pushed the corrected
implementation at the persistence checkpoint. The 1,538-line retained facade remains a
documented compatibility exception while runtime callers still import it; a
caller-migration proposal must define its retirement.

## Project-folder independence correction

`ProjectSQLiteRepository` no longer subclasses or constructs the retained
`SQLiteRepository`. It is an independent project-table composition root with
three named, typed surfaces: authoring, generation, and media. The project
generation surface is the exact adapter consumed by the direct pipeline; media
and authoring routes select their owners directly. Its media composition has
no application profile or pilot-accounting object. The retained facade still
composes the Wan accounting path for retained-runtime callers.

The project-video bridge receives explicit direct-video, currentness, and
project-dispatch transaction contracts instead of reaching through `_media` or
private leases. Shared row codecs, bound-ID lookups, and lifecycle guards live
in project-only support code. Package exports load the compatibility facade
lazily, so importing a project repository cannot initialize it as a side
effect.

This preserves tables, schema bytes, hashing, named transaction leases, CAS,
atomic install, and recovery/no-replay semantics. It is not runtime cutover:
the retained facade can be deleted only after its remaining runtime callers
move to their appropriate explicit owners.
