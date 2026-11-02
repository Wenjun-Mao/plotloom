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
not erase a completed discovery. Evidence follows the source dialogue phases:
the initial admission records the heater action, while the later explanation
adds the belief that the fire had gone out. The handover book exposes a deliberate
return to every encountered choice in the current and archived routes, plus the
current unanswered choice; opening, browsing, and closing it never changes the
current path or route archive. Only an explicit return action changes the path.

For V3 playback, a film node with one predetermined successor advances once
after its media ends naturally, including across another film or a reading
passage. A text-only passage waits for `进入下一幕`; decisions hold the preceding
frame and show only their authored choices; endings settle on their existing
card. Native video controls own pause and replay. The HUD does not duplicate
transport or route-history controls; route revisiting stays in the handover
book. A browser autoplay-policy rejection offers one user-start action that
disappears once playback succeeds, while media failures retain their own
diagnostic. Existing finished saves on a single-successor film continue to that
successor when resumed.

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
