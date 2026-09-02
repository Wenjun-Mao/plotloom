# ADR 0003: Narrative Forge v2 strangler architecture

**Status:** Superseded for current repository behavior by
[ADR 0010](0010-plotloom-clean-repository.md). This record is retained to
explain the completed extraction strategy.

## Context

The legacy application combines browser-local project state, prompt assembly,
response tolerance, media jobs, and rendering around one mutable `scene` shape.
That makes it difficult to strengthen one contract without changing unrelated
behavior. At the same time, the legacy UI and provider integrations remain
useful and existing projects must stay readable.

## Decision

- Build v2 as an extraction-ready FastAPI and React product in this repository.
  Its Python package, frontend, prompt templates, migrations, tests, and assets
  must be movable to a new repository without taking any legacy source file.
- Keep the legacy server available for existing projects, but freeze it to
  compatibility and security fixes. New projects and features belong to v2.
- Do not dual-write and do not import legacy projects into v2. V2 must not
  import `app.py`, `backend/`, legacy browser modules, or legacy project models.
  Useful provider behavior is re-expressed behind v2-owned ports and adapters;
  parity tests, not runtime imports, protect intended compatibility.
- During development, run legacy and v2 on separate ports. V2 owns `/v2` and
  `/api/v2`; it uses SQLite and a local content-addressed artifact directory.
- Keep the canonical domain free of browser, network, environment-variable,
  provider, and concrete filesystem concerns.

## Consequences and guardrails

The first v2 release supports interactive stories only; the domain retains a
clean place for later linear episode support. V1 regression tests remain release
gates while both products share this repository. An automated dependency-boundary
test rejects legacy imports from v2. A second extraction gate builds and probes a
V2-only wheel in a temporary directory; that wheel must contain the package-owned
prompt contracts, production UI, and migration tree. Even while both source
trees coexist, the root build publishes only the V2 Python package and V2 console
launcher; V1 remains a source-only comparison app. No path may have two
authoritative writers. The intended end state is a separate v2 repository whose
working tree and wheel contain no V1 code.
