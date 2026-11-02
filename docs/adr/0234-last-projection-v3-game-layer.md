# ADR 0234: Last Projection V3 game layer

## Status

Accepted for the V3 delivery on 2026-11-02.

## Context

The delivered V2 story and media already contain six authored routes and three
endings. V3 needs a film-first presentation and player records while leaving the
V2 package, authoring selections, media and saves intact. Reauthoring or
re-exporting the story would create avoidable provenance and preservation risk.

## Decision

Build a separate V3 standalone package from the byte-pinned V2 ZIP. Change only
the exported game identity and presentation-layer title/intro; retain its story
graph and media bytes. V3 saves use a distinct game-ID namespace. Evidence-book
facts are source-owned and reveal only after the corresponding route beat is
entered or completed. Encountered and completed beats persist independently
from the current route and ending archive, so unfinished route abandonment does
not erase a completed discovery. The handover book reads explicit route choices and
archived endings; opening or browsing it never forks a route. Only a deliberate
route-return action changes the current path.

Use V2's mixed audio track through native video audio and present one `声音`
control. Do not imply independent music control without a separable music stem.
Generate the embedded player assets deterministically from `frontend/src/player/`
and reject a V2 source archive that fails its pinned SHA-256 check.

## Consequences

- V2 remains the source of story/media truth and is never modified by V3.
- V3 has independent progression, route archive and audio preference storage.
- Standalone V3 releases must include the story, CSS/JS and every referenced
  media file in one directory; the loopback launcher is optional but supported.
- The player books remain presentation-layer features; no backend or source
  authoring contract is added.
- V2's mixed soundtrack is controlled as a whole.

## Verification

The V3 plan at [`../roadmap/2026-11-02-last-projection-v3.md`](../roadmap/2026-11-02-last-projection-v3.md)
owns functional, package, preservation and local qualification evidence.
