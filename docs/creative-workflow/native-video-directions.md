# Source-bound English video directions

This candidate-only stage drafts English directions for every unique frozen shot.
Read request.json and inputs/video-targets.json completely. Return directions.json:
`{"version":"video-directions.draft.v1","targets":[{"shotId":"...","sourceHash":"...","fields":[{"path":"...","english":"..."}]}]}`.

Copy exact shot IDs, source hashes and source field paths. Translate faithfully,
completely and concisely; do not truncate source or invent story/action. The
reviewedSoundscape supplement can describe only physically grounded ambient/action
sound consistent with the saved shot. Keep dialogue and visible text out of
English direction fields: trusted compilation preserves their authored originals.
Do not add prompt sections/markup, multiline fields or unsupported transformations.
Respect field bounds (2,000 characters, 100 fields/shot). Unsupported sources are
an explicit failure, not permission to omit fields. Never emit reviewedEnglish,
human observations, approval, dispatch, media or new canon. English fidelity remains
creator review. Host validation and deterministic report production are required.
