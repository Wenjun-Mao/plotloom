# Persistence project-authoring extraction receipt

## Checkpoint

- **Baseline:** `6872dd622f81b911f2507318e0d2c019250297fd`, clean before work.
- **Outcome:** extracted the project catalog/lifecycle and authoring draft,
  canonical-stage, gate, and approval bodies from the retained persistence
  facade into named project collaborators without an API, schema, migration,
  provider, frontend, or runtime-cutover change.
- **Scope:** `src/plotloom/persistence/`, targeted regression tests, this
  receipt, and the modularization roadmap.

## Ownership result

`legacy_repository.py` retains public `SQLiteRepository` and
`ProjectSQLiteRepository` signatures and explicit compatibility forwarding.
`project/catalog.py`, `lifecycle.py`, `drafts.py`, `gates.py`, `approvals.py`,
and `canonical.py` now own their capability bodies. `workflow.py` owns the
single lifecycle lease for canonical-stage save plus exact draft consumption;
it passes the one private session to the draft and canonical collaborators and
commits or rolls back once. Collaborators call named collaborators or narrow
session internals directly, never back through the public facade.

The extracted modules are 338/123/305/299/386/197/59 lines respectively; the
retained legacy facade is 8,014 lines. Remaining owned legacy responsibility is
generation snapshots/plans/attempts/work units/repair/recovery/canonical
commit, project media/still/image/review facts, and installation
profiles/settings/video-pilot accounting. This is not persistence completion.

## Characterization and review

The regression contract preserves both repository constructor signatures,
metadata/table selection and named leases, and now freezes the parameter names
of every moved public facade method. It also proves the project-bound repository
rejects a mismatched project ID. Focused lifecycle, repository, storyboard,
API, folder-authoring, and image workflow tests cover idempotent creation and
duplication, lifecycle CAS/busy/delete guards, canonical revision conflicts and
rollback, gate/approval identity and revocation, exact draft CAS consumption,
and project-folder restart isolation.

An attended read-only Terra review found facade bounce-backs, an approval
projection annotation drift, and missing signature/bound-ID characterization.
The candidate now calls collaborators directly, restores the tuple annotation,
uses the named workflow transaction owner, and adds the focused contract; the
reviewer rechecked and reported no unresolved P1 findings.

## Verification

| Command | Result |
| --- | --- |
| focused persistence/lifecycle/authoring/API/folder suite | 85 passed |
| `uv run --locked pytest -q` | 669 passed, 9 skipped |
| `cd frontend && npm run typecheck && npm test && npm run build` | typecheck passed; 132 unit tests passed; build passed; static assets unchanged |
| `cd frontend && npm run test:e2e` | 30 passed |
| fresh `uv build --wheel` and `scripts/smoke_installed_wheel.py` | passed; wheel SHA-256 `65f7f829d8ceedc50f7e5e2e80a6de4db1696892480b510d6723f8ea3d270243` |

Expected existing warnings remained: SQLite datetime adapter, historical
Pydantic serialization fixtures, TestClient deprecation, browser `NO_COLOR`,
and the frontend large-chunk advisory. No live provider was contacted.
