# ADR 0010: Plotloom clean repository and identity boundary

## Context

The new product was proven as an extraction-ready V2 beside Narrative Forge so that behavior could be compared cheaply. Keeping the temporary product/package identity or copying the mixed repository history would make the new repository look coupled to the application it is replacing. Renaming every protocol and database identifier during extraction, however, would combine a repository move with an unrelated compatibility rewrite and invalidate existing evidence.

## Decision

- The independent product is **Plotloom · 叙织**. Its Python distribution, import package, console command, frontend package, configuration prefix, browser storage key, user-data directory, database filename, application title, prompt personas, and worker names use Plotloom identity.
- The repository starts with fresh Git history. The exact verified source commit and imported surfaces are recorded in `docs/provenance/initial-extraction.md`.
- Narrative Forge V1 runtime code, project data, installers, build metadata, and compatibility aliases are absent. Plotloom does not read or migrate V1 projects.
- Existing product-prefixed environment variables and the session-key header are replaced, not aliased: `PLOTLOOM_*` and `X-Plotloom-Session-API-Key` are the only Plotloom contracts.
- The versioned HTTP paths `/api/v2` and `/v2/`, API semantic version `2.0.0`, `v2_*` SQLite tables, and existing Alembic revision IDs remain unchanged for the first independent baseline. They identify the already-tested API/schema generation, not the old product.
- Source checkouts store generated state under ignored `data/`; installed releases use the OS-appropriate Plotloom user-data directory.
- Historical architecture and handbook documents may retain fixed-revision source names and paths as evidence. They are explicitly non-runtime material.

## Rejected alternatives

- Preserving the old Git history would import unrelated V1 implementation and obscure the extraction boundary.
- Keeping `narrative_forge_v2` aliases would create two product identities and an indefinite compatibility surface before Plotloom's first independent release.
- Renumbering API routes and persistence objects during the move would add risk without improving the extraction outcome.
- Removing the research archive would discard the reasoning behind adopted, adapted, deferred, and rejected capabilities.

## Consequences and guardrails

Boundary tests inspect tracked runtime paths and Python imports, while distribution tests build and probe an isolated wheel. Documentation scans are intentionally separate so provenance is not mistaken for a dependency. Any future change to `/api/v2`, `/v2/`, or the database schema prefix requires its own migration/compatibility decision and regression evidence.
