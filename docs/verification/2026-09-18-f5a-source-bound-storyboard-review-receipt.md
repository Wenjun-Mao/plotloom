# F5A source-bound storyboard-review lifecycle receipt

Date: 2026-09-18. This receipt records implementation and focused automated
verification of the F5A lifecycle. It is not a new specialist delivery, human
creative review, production admission, or media proof.

## Delivered boundary

F5A adds a distinct `storyboard-source-review` lifecycle. It starts only from a
current accepted F4 script and freezes that script revision/hash, its inherited
source/outline/section-map/graph/cast/art/timing binding, and the exact ordered
section-to-episode mapping. Its F0 manual package provides the accepted raw
`script.json`, execution-only upstream `outline.json`, cast/art context, and a
small trusted admission artifact.

The receiving owner runs the pinned `novel-storyboard` validator and accepts
only the raw `storyboard.json` plus unmodified derived `report.html` as a
source-bound **review revision**. A changed F4 script or any inherited input
makes preparation/admission/acceptance stale. Prepared publication blocks
project lifecycle transitions and explicit cancellation rejects late delivery.

F5A deliberately uses a separate route/table/API surface from the existing
canonical-shot `/storyboard-review` contract. It creates no V2 Bible or
SceneBeats projection, canonical shot, player content, selection, media prompt,
dispatch control, reference, H3 timing change, or approval.

## Verification

- `uv run --locked pytest -q tests/test_project_storage_art.py` — 17 passed.
  The F5A cases cover F4 identity/mapping freeze, lifecycle blocking and late
  delivery refusal, mapping rejection before upstream validation, accepted-review
  staleness following an F4 edit, and restart-compatible project storage.
- `npm run typecheck` — passed.
- `npm run build:deterministic` — passed; refreshed the committed static bundle.

The focused lifecycle test stubs the upstream validator only for an artificial
accept/reopen state transition; production admission always invokes the pinned
validator. No gateway, ImageGen, H3, provider, database fixture, retained
project, upstream/submodule, or human creative artifact was changed.

An independent attended Terra/high read-only review found and the coordinator
resolved two material lifecycle defects before this receipt: F5A acceptance no
longer permits client JSON to differ from the admitted candidate/report bytes,
and a ready candidate must be explicitly accepted or cancelled before another
can be prepared. The regression suite covers both guards. The follow-up review
found no remaining material issue.

## Remaining proof

The historical F5 candidate hash
`50165863d45e678c28bcf794c6f9f5444b6aa45eef2caa446595dd638313578a` remains
historical evidence and was not rewritten or promoted. A fresh F5A package run,
independent attended review of its actual output, and human creative acceptance
are separate next proofs. Production integration and any variable-duration H3
decision remain out of scope.
