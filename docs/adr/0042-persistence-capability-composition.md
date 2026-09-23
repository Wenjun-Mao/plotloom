# 0042: Persistence capability composition

**Status:** accepted

> **Scoped current authority (2026-09-23):** The `legacy_repository.py` facade
> and `SQLiteRepository` references below describe the former shared-runtime
> generation. [ADR 0048](0048-retire-shared-repository-runtime.md) retired that
> facade and its import alias; no current caller may use it. The named,
> project-owned capability composition and explicit lease/transaction ownership
> remain the relevant design. The original correction and migration sequence is
> preserved below as historical evidence, not a compatibility exception today.

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
three named public surfaces: authoring, generation, and media. Its media
composition has no application profile or pilot-accounting object. The retained
facade still composes the Wan accounting path for retained-runtime callers.

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

## Surface-constructor correction

The first project-folder independence extraction overstated the word
"typed": each public surface accepted the full composition root as `Any`,
saved it, and forwarded through its private fields. Generation also put its
process-local provider-admission hash and recovery callbacks on that root. The
legacy facade was no longer inherited, but the three new surfaces were still
service locators in miniature.

The correction gives authoring its six named persistence owners, generation
its named snapshot/plan/attempt/lifecycle/evidence owners and a separate
`ProjectGenerationAdmission` state owner, and media its exact media owners.
The direct video bridge receives the direct-video/currentness ports plus its
named dispatch lease. Direct pipeline, job, work-unit, video, and API imports
now depend on their narrow project surfaces rather than loading the retained
facade just for annotations or eager public exports. Approval value types are
project-owned public values, so they no longer require loading the facade.

Import-blocked regression coverage runs the direct API, four-stage pipeline,
image handoff, H3 video, and snapshot paths while refusing both import and
construction of `legacy_repository`; the installed-wheel smoke applies the
same blocker before direct project composition. This changes no runtime mode,
schema, public route, hash, CAS, transaction boundary, recovery behavior, or
provider behavior. The retained facade remains until its retained callers have
their own approved migration.
