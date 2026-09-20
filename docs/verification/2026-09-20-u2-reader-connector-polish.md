# U2 reader connector polish receipt

Date: 2026-09-20. Scope: the read-only `story-prototype` branch-map layout,
its focused browser evidence, and usability records only.

## Attended usability acceptance

The user approved the storyboard reader as usable after the attended review,
with one exception: wide-screen connector strokes were detached from the branch
cards. This records usability feedback only. It is not creative acceptance,
generated-media acceptance, F5A production acceptance, M2 acceptance, or
approval for U3, F7, or a language change.

## Root cause and correction

The old connector was split across destination-card pseudo-elements and used
viewport-relative offsets. The cards own their own height and position, so at
wide widths the offsets no longer described the branch layout and left detached
strokes near the heading.

The branch canvas now owns a single decorative connector in its dedicated grid
track. One trunk leaves the opening and two arms terminate at the centers of the
two equal choice rows. The connector is hidden with the decorative wide-screen
layout at the narrow single-column breakpoint. The canonical graph still owns
the opening, choices, consequences, routes, and selected focus; the connector
has no interaction or semantic role.

## Verification

`npm run typecheck` passed in `frontend/`. `npm run test:e2e --
story-prototype.spec.ts` passed all 3 production-browser tests (and its E2E
typecheck). The focused run covers the retained F4-only multi-scene screenplay,
valid F5A storyboard route, local stale-storyboard refusal, route focus, and
GET-only reading. `npm run build:deterministic` passed and refreshed
`src/plotloom/static/workbench.{js,css}`.

The run retains full-page storyboard captures at 1440 px, 1920 px, and 768 px,
plus map-only captures at 1920 px, 768 px, and the 720 px narrow breakpoint.
Visual inspection verifies that the 1920 px connector is continuous from the
opening to both endings without heading overlap. At 720 px, the opening and its
two choices are clear in stacked reading order and no decorative stroke remains.

## Independent review and exclusions

The requested independent, attended Terra read-only stable-delta review is
recorded below after the final checks. No backend, persistence, prompt/schema,
provider, generation, media, production, report sandbox, or accepted content
behavior is changed. No preview project or service is modified by this slice.
