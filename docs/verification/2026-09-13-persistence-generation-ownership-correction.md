# Generation persistence ownership correction

## Why this correction was necessary

The original generation-extraction receipt for `aabb563` was inaccurate. It
moved public methods to named collaborators, but retained the corresponding
repair validation, immutable-evidence, recovery, and atomic-install policy in
`legacy_repository.py`. Those collaborator calls still bounced back through
the facade, so the ownership claim was not true. This correction retains the
passing baseline behavior and moves the policy; it does not change a generation
algorithm, schema, hash representation, transaction lease, or public API.

## Corrected ownership

- `generation_access.py` supplies only named leases, project-bound row access,
  codecs, and profile admission; it contains no facade reference.
- `generation_integrity.py` owns work-unit sealing and exact producer evidence.
- `generation_repair_eligibility.py` owns stale/hash/rejection eligibility and
  frozen reusable-source evidence; `generation_repair_scope.py` owns the exact
  repair scope, dependencies, timing provenance, and reused candidate checks.
- Planning owns normal frozen dependencies; lifecycle owns atomic parsed/sealed
  install and cancellation state; recovery owns obsolete-contract and restart
  classification.

The retained facade now only composes those owners and delegates public APIs.
The structural regression rejects the former policy bodies and a collaborator
reference back to the facade. Project-bound run and project lookup callbacks
remain in the narrow access contract, so `ProjectSQLiteRepository` preserves
its bound-ID and admitted-profile guards.

## Verification

Focused repair, work-unit, planning, recovery, and persistence contract suites
were run throughout the extraction. The stable candidate passed:

- locked Python suite: **671 passed, 9 skipped**;
- independent attended Terra ownership review: no P0--P2 findings; its one P3
  unused-import observation was removed, then its 131 targeted tests passed;
- frontend typecheck, **132** unit tests, production build, and static-freshness
  check;
- browser E2E: **30 passed**;
- fresh wheel build and installed-wheel smoke, including Alembic package and
  migration checks.
