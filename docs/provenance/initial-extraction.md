# Initial Plotloom extraction provenance

Plotloom began as a clean-room repository extraction of the independently tested V2 product developed beside Narrative Forge.

## Fixed source checkpoint

- Source repository: `https://github.com/Wenjun-Mao/Narrative-Forge.git`
- Verified source commit: `fdbbc5f67783fc1aaa01292b0a2ea58bb5f781d1`
- Extraction date: 2026-09-02
- Destination history: new Git history; no source repository commits were imported

## Imported product surfaces

- `src/narrative_forge_v2/` became `src/plotloom/`.
- `frontend/v2/` became `frontend/`.
- `tests/v2/` became `tests/`.
- V2-only packaging and environment templates became root repository metadata.
- V2 decisions and the authored architecture/research readers were retained as design evidence.

All production identifiers were re-expressed as Plotloom identifiers. The extraction intentionally excludes `app.py`, `backend/`, `src/narrative_forge/`, the legacy root `static/`, legacy project data, installers, and the mixed repository's build metadata.

## Runtime boundary

No Plotloom production module imports or reads Narrative Forge V1 runtime code or project data. Documentation may name the source repositories and frozen paths because it preserves design provenance; those references are not runtime dependencies.

The verified `/api/v2`, `/v2/`, `v2_*` SQLite schema and Alembic revision identifiers remain as explicit protocol-version markers. Their retention is documented in ADR 0010 and does not preserve V1 code.

## Licensing

The Apache License 2.0 `LICENSE` and attribution `NOTICE` travel with the extracted work. The research handbook's `THIRD_PARTY_NOTICES.md` records fixed-revision analysis of shuohao-skills and the boundary between analysis, adaptation, and direct reuse.
