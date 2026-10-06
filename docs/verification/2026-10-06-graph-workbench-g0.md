# Graph workbench G0 contract qualification

Qualified on 2026-10-06, on retained local `main`, based on
`e542f49c4e815d797f17e0a83c0631c54f9f6ea3`. This is the G0 source candidate,
not the G1–G5 UI or release receipt. Source/frontend/tests aggregate SHA-256:
`84b674a92890e9b3fed77856c7b26b6a78d4ad6226f7f57f0653a7271a75f75c`.
The local per-file manifest is `.local/graph-workbench/g0-source-manifest.json`.

## Contract and positive evidence

ADRs 0120 and 0121 bind explicit footage membership and the sole current
source-bound `story_graph/root` draft/admission contract. A current three-option
map with an inserted scene, join, retained source/outline bindings and typed edge
effects round-trips into canonical schema 2. Blank/pending drafts recover but fail
complete admission. Exact draft revision, canonical base and content are checked
and consumed atomically; generic manual graph writers reject.

`test_graph_authoring_contract.py` covers these seams, immutable seed provenance,
ordered footage membership, non-root draft rejection and the scene-owned state
boundary. `test_graph_authoring_production.py` executes F1–F5, review and bridge
installation with fake transport: route-only controls produce six footage episodes
and 54 shots; explicit footage inclusion produces eight episodes and 72 shots.
Both retain three complete routes. No upstream empty screenplay placeholders or
inferred node modes are used. Frontend playback checks require real scene/shot
coverage for every footage node and traverse explicitly state-free controls.

## Confirmed retirements

- Binary SectionMap models, execution and frontend recovery; current typed
  topology, ordered choices and explicit planner/author provenance replace them.
- Generic manual canonical graph save/consume; current generation and initial-stage
  bootstrap retain their supported validation and transaction guards.
- V1 canonical classes/read selection/validation and missing snapshot schema
  defaults; current rows reject missing/retired versions before payload decoding.
- Historical bridge intent reconstruction; stored current packages are required.
- Old timing/capacity replay, topology projections and obsolete correction
  witnesses; current frozen membership and complete contract identities are required.

Provider version-like names, snapshot/restore, current CAS, media selection,
credentials and unknown-dispatch guards were preserved. The fail-closed unsealed
evidence diagnostic is not an old-contract executor.

## Executed verification and review

- Full Python: **1,162 passed**, one existing Starlette deprecation warning,
  340.91 seconds (`g0-final-python-suite.txt`).
- Full frontend: **512 passed**, 70 files (`g0-final-frontend-suite.txt`).
- Typecheck, deterministic frontend/static build, `uv lock --check`, configured
  API F401 lint and Python compilation passed. Build retains the existing chunk-size
  warning. The bundled static asset was rebuilt.
- Independent read-only GPT-6.1 Sol / Medium route review and Sol / High current
  contract review were attended. The latter's two concrete findings (footage
  provenance and non-root draft identity) were fixed; follow-up confirmed both
  closed with 16 Python and six frontend checks and no new concrete regression.
- The retained coverage inventory's four live assertion references were refreshed
  with a dated amendment. Its historical baseline and review receipts remain intact.

No real provider dispatch, database reset, service activation, commit or push was
performed. Tests used disposable stores and fake transports. Installed productions
remain first-install-only; any later disposable demo rebuild must identify the
exact project and prove no queued, dispatched or outcome-unknown work before reset.

## Gate and remaining work

G0 is qualified for G1. The separate source editor buffer and professional graph
UI still need the shared draft/command integration. G1–G5, native desktop exercise,
full E2E, wheel/installed smoke, final independent review, runtime preservation and
activation remain outstanding. Engineering evidence does not establish owner UI
or creative/media acceptance.
