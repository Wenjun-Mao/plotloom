# Original source entry and separate V1 reference

Status: scoped implementation complete, reviewed, published and activated;
all local and full remote gates passed. Not creator
usability or creative acceptance. Scope: the owner's request to remove repeated
Source work before continuing the new-project walkthrough, with the Chinese
manual explicitly deferred. Contract: [ADR 0112](../adr/0112-original-source-direction-and-outline-settings.md).

## Delivered boundary

An original `synopsis` carries forward from Brief and can be confirmed unchanged
with empty additional direction. The form calls that field
“补充创作要求（可选）”; imported text and existing works still require
“改编目标”. Changing type retains entered story and direction.

Trusted code freezes the saved Brief's non-story settings in
`inputs/outline-settings.json`. Confirmed Source owns story/title; Brief owns
language, genre, style, aspect, route-duration target and production scope.
Preparation, delivery and explicit acceptance compare this projection inside
the owning transaction. A Brief edit cannot admit an unfinished stale candidate.
Already accepted Source/outline remain author-confirmed evidence; existing
field-specific owners handle later production-setting changes.

The first full backend run exposed an overbroad accepted-outline cascade:
shot-policy edits incorrectly staled the source graph, and route-duration edits
blocked replacement Script preparation through Art. That new cascade was removed
at its originating Brief dependency layer, not bypassed downstream. The original
bridge/Script regressions and new accepted-evidence checks now pass. Outline-only
terminal fixtures publish the new artifact rather than weakening admission.
The Git-bound recovery test was rerun after committing the modified specialist
instructions; it passes without relaxing execution-pin checks.

## Executed verification

Runtime candidate: `9ab34d30064e98b11c06a87a5f5e73e055bc624c`, published to
`origin/main`. Independent, attended GPT-6.1 Sol / Medium review found no
actionable issues after the concrete invalidation-boundary correction; it passed
93 settings/bridge/review/terminal cases and 10 source-outline cases, with no
source writes or live-data interaction.

| Check | Result |
| --- | --- |
| Full locked Python suite | 1,082 passed in 338.72 seconds; existing Starlette/httpx warning |
| Frontend unit suite | 452 passed across 60 files |
| Frontend types/build and checked assets | Passed; existing large-chunk warning |
| API F401 and bounded new-module imports | Passed |
| Archived prompt reader | Passed |
| Wheel build and installed-wheel smoke | Passed |
| Focused creator/source browser checks | 33 passed |
| Full unfiltered local browser run | 140 passed in 15.1 minutes, one worker |
| Full remote CI | [Run 37222001076](https://github.com/Wenjun-Mao/plotloom/actions/runs/37222001076), completed successfully on the exact runtime candidate, `browser_grep=.*` |
| Whitespace | Passed |

## Normal activation and preservation

The supported `services/creator_workbench/manage.py start --data-root
.local/creator-walkthrough` command successfully recreated normal 8841. Just
before restart, both projects had no generation, image or video jobs and the
native specialist registry had no active tasks. The recreated container is
healthy; `/healthz` is `ok`, the native bridge is available and H3 remains
disabled. No schema migration, data copy, creative confirmation, generation,
provider testing or credential replacement was performed.

- Container: `1dfc7327d3768db471fb427527f292ad05b77556b8c96a87032dbd668b965506`.
- Image: `sha256:b8b3e84a12c28d2c7127349872ef34b652b2b7c7b7d08dfecfd8446f5b817949`.
- Start: `2026-10-04T17:50:38.979178313Z` (October 4, 13:50 Toronto).
- Served/checked `workbench.js`: `c8c54cdf0115eb5501bca488f4a21099c30378ef754be2495447039498e9c805`.

The read-only capture in `.local/source-entry-2026-10-04/` records both normal
projects, not only the older walkthrough project:

| Project | Preserved evidence |
| --- | --- |
| 风里的纸飞机, `49b74b80-a31b-4aed-8423-00b8d9de56dd` | All 74 table projections, 2 managed file hashes and 7 API projections unchanged |
| 雨停以后, `ee271b49-f384-414c-9711-452ee6333b84` | All 74 table projections, 67 managed file hashes and 7 API projections unchanged |

`before.json`, `before-activation.json` and `after.json` match byte-for-byte
(`cmp` passed): SHA-256 `086d881719da44ec2dd8978ad67dc76fb7de9a08453ce7f7d69a74a201930210`.
The final `after-browser.json` capture also matches after the live read-only UI
check. The browser command was `npm --prefix frontend run test:e2e -- --workers=1`,
with no filter, skips, weakened assertions or timeout increases.
Specialist settings and the existing bridge credential hash are unchanged.
This is equality of captured rows/projections/managed files, not a claim of
whole-SQLite-file byte equality. The retained 8851 copy was not used or changed.

The freshly loaded normal Source page shows the owner's unconfirmed
《风里的纸飞机》 synopsis intact, blank optional direction and enabled
confirmation. No save, prepare, dispatch or acceptance control was used there.
Screenshot: `normal-source.png`, SHA-256
`4267066c864d08b8e83e76aa7989d351d1471db6955579ce7939f81971ba2ba9`.

## V1 and deferred manual

Narrative Forge V1 runs separately at `http://127.0.0.1:8775/`, using its own
legacy checkout/project directory. Port 8765 belongs to an unrelated service
and was left alone. The existing V1 `src/narrative_forge/__init__.py` edit was
left untouched. Its first page visibly loads; no V1 save, generation, provider
test or file import was performed. Production does not read V1 source/data.
Screenshot: `v1-reference.png`, SHA-256
`f5dc17dca5356be86cd9834a75ee61d51ef46a2ab7841c555be9f32315769753`.

`docs/creator/` has no diff against pre-change `b306820`; the Chinese manual
remains SHA-256 `c44adfddba45a4db4a3e5e5d0a9fcc376278a3baeaed502f9b8259c934e30db8`.
It is deliberately not synchronized yet, per the owner's instruction to wait
until today's changes settle. The next product step is the owner's continued
walkthrough and selection of useful V1 references, not automatic V1 copying.
