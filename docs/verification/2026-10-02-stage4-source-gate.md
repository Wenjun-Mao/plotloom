# Stage 4 source gate: reviewed production presentation

Assignment: bounded Stage 4 in the [approved walkthrough](../roadmap/2026-10-02-unattended-creator-walkthrough.md). Source owner works on retained `main`, base `b845caf903a310161d06511125d1a1d02e16b4ed`. This receipt covers implementation and disposable fixture verification only. Manager owns independent reviews, commit/push, matching static promotion and release of live continuation.

## Root causes and contract changes

1. The bridge/provenance boundary required integer seconds despite canonical integer milliseconds. Shared exact decimal-number conversion accepts positive finite JSON int/float values only when milliseconds are integral; it never rounds or truncates. Raw F5 admission stays unchanged. Tests prove 2.5-second cuts install as 2500 ms with exact scene sums/provenance, while accepted submillisecond F5 produces an explicit production conflict. Frame-grid, request capacity and segment gates remain separate.
2. The bridge used only the first covered beat and active image context reintroduced mixed UI/action prose. A complete, explicitly reviewed presentation package partitions every F4 action/dialogue and F5 frame into exhaustive contiguous spans. Trusted source hashes/coordinates/raw evidence stay immutable; the reviewer owns faithful physical rendering and exclusions. Ordered covered actions project into shots; dialogue stays exclusively cue-owned, including dialogue-only cuts. Exact diegetic text gets a separate nonspoken field. Narrative objectives/purposes do not reenter active media input. The typed compiler places exact visible text in its nonspoken role; semantic package review owns separation without inferring roles from generic substring overlap. ADR 0100 names these ownership boundaries.
3. SectionMap question was absent from video playback. The accepted current production bridge now exposes its exact source-bound question/outcomes; the player confirms exact edge/target/label agreement and waits until opening completion. Failed/stale/unavailable ownership closes branch choice. Native canonical playback stays source-independent. Correct prompt text does not certify rendered phone text; real media review remains required and no compositor is claimed.
4. Fresh preparation checked newly derived binding against itself, allowing stale accepted F5 to pair with edited F4. It now validates the retained accepted binding and its frozen max-cut policy before deriving/freezing inputs. Reopen/edit refusal occurs before proposal/head writes; the longer-cut policy has a direct regression.
5. Isolated composition lacked supported H3 enablement. Explicit default-off `--enable-h3` uses the shared trusted H3-only builder. Provider-only `VideoProviderSettings` shares the trusted dotenv/exported-environment boundary with `PlotloomSettings`; isolated setup never validates unrelated normal storage or runtime fields; all outputs/application/static paths come from RuntimeConfig. Tests use a genuinely unexported dotenv credential and verify precedence/isolated paths/default-off without printing credentials or contacting a gateway. The current trusted dotenv contains an obsolete v5 catalog; manager authorizes a scoped current v7 environment override for the later isolated launch. Accepted catalogs are not widened and normal settings are not rewritten.
6. Health inputModes equality rejected compatible extra modes. It now requires typed, unique, nonblank string entries containing image/text, ignoring unused extras. Closed job grammar still admits image only; voice is never enabled. Other catalog/profile checks stay strict.

New production image snapshots freeze `physical-visible-runtime.v1`, a presentation-specific compiler and pinned package v5. Existing frozen package projection bytes remain unchanged; reference proposals retain current v4. Pin provenance includes presentation/timing/canonical schema source owners. New H3 jobs freeze `plotloom.h3-reviewed-frame.v5-presentation`; retained job prompt bytes are not relabelled.

## Verification

- Focused bridge, presentation, prompt, video/segment/image currentness and delivery checks passed during edits; final exact gate results are appended below.
- Complete frontend unit run: 292 passed in 44 files. App and E2E TypeScript checks passed.
- Whole presentation browser journey: explicit span ownership, complete-package confirmation, saved evidence/reload, independent intent gate and explicit installation in disposable fixture roots.
- Existing H3 browser tests were stale to the current English-review/catalog/segment workflow. They now use explicit fixture translations, prompt preview/freeze and segment confirmation; no product guards were relaxed. Synthetic offline gateway reports the submitted quality instead of a hardcoded value.
- Both-route native browser playback/episode reset/reopen passes with reviewed synthetic segments. This demonstrates browser lifecycle, not real media or dialogue/text fidelity.
- Production Vite build staged at `.local/unattended-2026-10-02/stage4-static`; normal/copy served assets were not promoted. Build has the existing large-chunk advisory. `git diff --check` passed.

## Live boundary and remaining work

No actual project mutation, canonical installation, fresh native keyframe package, H3 dispatch, normal service restart, source commit or push occurred during this source gate. Actual current copy source remains Cast r3 / Art r2 / Script r3 / Storyboard r2 with all provisional reference decisions and quarantined evidence retained.

Owned isolated PID 83040 was last directly observed by manager at 10:10 UTC; GET at 10:44:38 found it offline and its previous session unavailable. This source owner did not signal/stop it; cause is unestablished. Normal `/healthz` still responded. No restart was attempted. After independent source review/push, manager must authorize/start the same isolated runtime with explicit current ownership, inspect currentness/reservations, and release live installation/keyframe/H3 work. Image/H3 output still requires factual, visual and audiovisual inspection before provisional selection; owner creative acceptance remains separate. No usage/cost delta is available from this source verification.

## Frozen gate results, 11:05 UTC

- `uv run pytest -q`: 954 passed / 1 failure solely in the hash-bound retained coverage inventory after a current package-version assertion changed. The replacement catalog/hash and mapping note were updated (three lines); baseline assertion records remain untouched. Full-suite rerun was not repeated after that receipt-only edit.
- `uv run pytest -q tests/test_retained_runtime_coverage_inventory.py tests/test_production_presentation.py`: **30 passed**, closing that inventory failure and covering all 29 presentation regressions, including the separately added retained longer-cut-policy test.
- `PYTHONPATH=src:. uv run pytest -q services/creator_workbench/test_isolated.py tests/test_production_bridge.py tests/test_production_bridge_intent.py tests/test_pin_image_specialist.py`: **50 passed**. The explicit PYTHONPATH is needed when collecting service tests outside the configured `tests` testpath.
- `npm test`: **292 passed / 44 files**; `npm run typecheck` and `npm run typecheck:e2e` passed; external-output Vite build passed.
- Whole presentation browser + H3 prompt-freeze/segment/restart browser: **2 passed** in the final targeted run. H3 current controls: **1 passed**. Complete native-ended both-route/restart/reopen browser: **1 passed** in its updated run.
- `git diff --check` passed. Source stays dirty/uncommitted on `main`, base `b845caf903a310161d06511125d1a1d02e16b4ed`. Independent source reviews and matching checked static promotion are pending with manager; no product/media acceptance is implied.


## Independent review closure candidate, 11:15 UTC

The implementation reopened only for four demonstrated contract findings and five newly unused imports. Playback now derives bridge ownership from current manifest-admitted media, with positive canonical playback regressions for stale bridge history and current-but-foreign-shot history; active bridge source failure still closes choice. A provider-only settings model shares dotenv/env precedence with normal settings, but validates no normal storage/runtime fields; invalid equal/nested/obsolete normal storage does not veto isolated setup, while missing credential/catalog drift still fail closed. Typed exact visible text no longer uses canonical human-text whitespace normalization; projected → canonical → H3 prompt tests preserve spaces/tabs/newlines and reject whitespace-only fields. Visible-text substring matching was removed because ordinary physical English can overlap diegetic labels; compiler-owned nonspoken placement and explicit semantic review remain, with ordinary "In"/single-letter overlaps covered. Existing dialogue duplication guards are unchanged. ADR 0100 states these mechanical/semantic boundaries.

Executed after these fixes: **89 passed** across isolated service, normal config/runtime boundary, H3 prompt and presentation tests; **25 playback frontend tests passed** and app typecheck passed. Focused new/extracted-owner F401 and `git diff --check` pass; the separate pre-existing runtime TextProviderProfileSnapshot warning remains unchanged. Final frontend unit/typecheck/staged rebuild results follow. No live actions occurred. Manager reported the prior frozen candidate full Python **956 passed**, all41 service/bridge/manage checks and292 frontend/typechecks passed; those are prior-candidate gates, not verification of reopened source. Targeted independent closure and manager final gate remain pending.

Refrozen at 11:16 UTC: complete frontend **294 passed / 44 files**, both app/E2E typechecks pass, external-output Vite build passes (existing chunk-size advisory only). Updated staged assets remain at `.local/unattended-2026-10-02/stage4-static`; no served assets promoted. F401 checks for config/new/extracted owners and `git diff --check` pass. Source remains uncommitted on the same `main` base. Sole source owner stops edits for targeted reviewer closure and manager final gate/commit/release.

## Manager release gate, 11:22 UTC

Both independent reviewers reproduced and closed all four findings with no
remaining scoped findings. The playback reviewer reran the original historical-job
reproduction: current canonical decisions remain available and perform zero bridge
reads, while admitted bridge media still fails closed. The exact-text checks retain
spaces, tabs and newlines through canonical validation and prompt construction.
The runtime reviewer reran 89 focused tests; the presentation reviewer reran 35
backend and 25 frontend tests. These overlapping counts are not additional suites.

Manager independently ran the final source: **964 Python tests passed** (259.44 s),
**46 service/bridge/manage tests passed** (11.13 s), **294 frontend tests passed**,
and both app/E2E typechecks passed. Scoped new/extracted-owner F401 and diff checks
passed. The existing Starlette/httpx deprecation and Vite chunk-size advisory remain.
A fresh independent production build matches the staged build byte-for-byte.

Original seven API projections, 73 tables and 67 files remain byte-identical to
launch in `evidence/manager-stage4-before-deploy-original.json`. Normal specialists
have no active tasks or reservations; both native chats are inactive. The sole
changed generated asset, `workbench.js`, was promoted to source and copy static
roots at that idle boundary; both trees match the reviewed build. Its SHA-256 is
`40693097bdc4e0be3a0b1027addac4d64b5ec979f162c7c54c8a4e9ffa6f4cae`.
The actual-config provider-only constructor also passed with a process-scoped
current v7 catalog, unexported credential loaded from trusted dotenv, and default-off
behavior; it made no network call. Commit/push, backend deployment and live media
continuation follow this gate and are not implied by these tests.
