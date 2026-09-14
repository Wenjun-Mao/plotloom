# P2 selected-sequence playback correction

Captured 2026-09-13. This receipt records an offline product correction from
the clean baseline `4e2cfc385a25ee7bd217abddd03cad5fe4af0901`. It does not
review, select, alter, or make claims about any live Wan candidate.

> Historical runtime note: this record's legacy FastAPI/Wan fixture and
> synthetic terminal-event assertion were retired on 2026-09-14. The retained
> browser journey now uses production project-folder composition, typed offline
> H3, and only real native completion for its sequence transition. See
> `docs/verification/2026-09-14-production-browser-parity.md`.

## Diagnosis and contract repair

The original player stored only a numeric selected-sequence position. A project
or scene refresh could retain that position while replacing the sequence that
gave it meaning. Its `ended` continuation then advanced whatever replacement
occupied that number; `play()` rejections were intentionally discarded. This
was a client lifecycle defect: the API already returns project-scoped jobs and
the server already limits selection to current, reviewed, ingested candidates.

The repaired frontend makes a playback identity the pair
`projectId:videoJobId`, and derives the sequence scope from the ordered selected
job identities. It filters locally retained asynchronous state by the active
project before producing player URLs. A scope/membership change resets to the
first surviving selection without autoplay. Keyed native video elements and
identity checks prevent stale `ended` events and late `play()` failures from
affecting a replacement source. Rejections now appear in the panel; the final
clip still holds its decoded final frame until the reviewer explicitly seeks or
restarts it.

## Offline evidence

The DOM regression suite covers project and scene transitions, an in-place
selected-membership addition for the same project/scene, automatic advance,
final-frame hold, and both surfaced current-source rejection and ignored late
rejection from a superseded source.
The real browser path uses the existing FastAPI/file-SQLite fixture runtime and
its `OfflineWanFake`; it does not configure or call a live provider. It creates
two normal reviewed-keyframe selections for adjoining `shot_01` and `shot_02`,
then separately ingests and explicitly selects their synthetic H.264/AAC video
candidates through the ordinary UI/API flows.

In the browser, the first real locally served MP4 is started through the user
visible control and observed with `currentTime > 0`. Its native five-second
`ended` event automatically replaces it with the ordered second source, whose
`currentTime > 0` is also observed. The second rendered source is asserted to
be the second selected job's project-scoped URL. Previous/next navigation, a
native seek, explicit restart (seek-to-zero and resumed play), final-frame hold,
range responses for both sources, and a
same-storage backend restart plus page reload are asserted. The final-hold
assertion dispatches a synthetic terminal event only after the actual first-to-
second media transition; it is not evidence for that transition.

## Commands and results

One attended independent Terra read-only review found missing same-scope
membership and stale-continuation regressions plus incomplete second-source and
restart assertions. The tests and this receipt were corrected before the final
full-suite runs below; no implementation defect was identified.

- `uv run --locked pytest -q` — 595 passed, 9 skipped (272 existing warnings).
- `npm --prefix frontend run test` — 129 passed.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run typecheck:e2e` — passed.
- `npm --prefix frontend run test:e2e` — 27 passed, including the selected-pair real FastAPI/file-SQLite browser journey.
- `npm --prefix frontend run build` — passed and refreshed `src/plotloom/static/workbench.js`.
- `uv build --wheel --out-dir <temporary directory>` followed by `uv run --locked python scripts/smoke_installed_wheel.py <temporary directory>` — passed for an isolated installed wheel.

The existing Vite bundle-size warning remains informational. This checkpoint
does not establish creative quality, real-provider behavior, cross-shot audio
continuity, or a general browser autoplay guarantee outside the reviewed local
sequence interaction.
