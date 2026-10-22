# Normal 8841 cutover and intact demo retirement

Owner authorization on October10: “retire the two older demos from active use
while preserving their files and activate the new version.” This resolves the
last operational gate in the [current E2E run profile](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
It authorizes folder retirement and software activation, not conversion of old
project schemas, a new installed story or a new generation dispatch.

## Published and activated authority

- Normal `main` was clean at `7d79d18b502746ba42642befce8e4510172949c8`.
  Root fast-forwarded it to `868796bfa426fcfd7fa7a44514861e0543c1c6c0`, updated
  the renderer submodule to `4f9b2128c82adf623f594ba714c97d0afcfc16a2`, then pushed
  non-force and read back matching `main`/`origin/main`.
- Executable/test/package/service inputs are exact to qualified `0b71359923a5cbe92ff2c15cf06c30b6b9c175de`.
  Later candidate changes are four documentation files only. Exact hosted
  [CI38024405822](https://github.com/Wenjun-Mao/plotloom/actions/runs/38024405822)
  completed SUCCESS: 1,469 Python, 1,047 frontend and 278 unfiltered browser cases,
  plus types/build/parity/wheel/installed smoke. The [cleanup receipt](2026-10-10-testing-health-cleanup.md)
  owns those executed gates; this cutover does not claim to rerun them.
- While idle, normal was stopped gracefully with the established `manage.py stop`.
  Container readback was `exited`, exit143. Folder moves and the checkout/submodule
  update occurred while it was stopped; no mixed old backend/new frontend service.
- Established `manage.py start` built/recreated the service and exited0 after
  Docker health and native bridge checks. Container start: `2026-10-10T11:12:58.087815841Z`.
  Image: `sha256:f646f81db72d4916ad3efde91fd15372a0f5d341457cec250a1f925bf2f87ee5`.
  `/healthz` and `/v2/` return200; `codex bridge-health` reports available.
- Served, local and container JS SHA256 match:
  `0a4fd0e721b819da4ffec7d946e0af8f7c9ae3a90e9c4d473972951ac3ace160`.
  Container imports the normal checkout's Python package, and its application
  factory and current-schema file hashes match that checkout. Specialists remain
  idle with no active tasks. No task preparation, sending, generation or selection.

## Two intact retired demos

Both homes were moved using exact, preflighted basenames with `mv -n` from
`.local/creator-walkthrough/outputs/` into
`.local/creator-walkthrough/retired-demos/2026-10-10/` in the normal checkout.
No destination existed beforehand. The pair of renames is not a transaction;
both succeeded and were verified before restart.

| Retired demo | Preserved folder basename | Exact files |
|---|---|---:|
| 雨停以后 | `20260926T040847045015Z__ee271b49-f384-414c-9711-452ee6333b84` | 68 |
| 风里的纸飞机 | `20261005T003111705906Z__2f52cf22-3f4a-4f05-8dc3-4f55e76687b9` | 18 |

All relative paths, SHA256 bytes, sizes and file modes match the pre-stop inventory.
The 36-file Rain snapshot stayed in its existing hidden `.snapshots` home. Its first
hash inventory was after the two folder moves but before checkout activation;
comparisons prove it unchanged from that pre-restart point through browser smoke,
not hash-bound across the earlier moves. Retirement is outside active discovery,
not an archive-state rewrite inside
an unsupported database. Both IDs disappear from the catalog and direct project
GET returns404. Files remain recoverable for inspection; they are not silently
made admissible to the breaking current schema. Nothing was deleted or migrated.

The four other prior QA homes remain in `outputs`. They are unsupported by the
exact current-schema admission and therefore not listed; they were not moved or
reset. All of their baseline files remain exact. An initial strict whole-inventory
comparison failed because read-only SQLite discovery created four additional
coordination pairs: 0-byte `project.sqlite3-wal` and 32,768-byte `project.sqlite3-shm`.
The failure was investigated, not relabeled as an exact-folder PASS:
`current_schema.py` explicitly permits SQLite's mode=ro sidecar maintenance and
does not use unsafe immutable reads that could miss committed WAL authority.
The corrected inventory separately records all eight added sidecars, asserts empty
WALs, and still requires every baseline file to match. No rows or schemas were rewritten.

All seven baseline homes (two retired, four prior QA, one snapshot), all 181 original
files and three protected configuration files match their respective baselines
after browser verification. The snapshot interval is the narrower one above.
Deployment configuration, specialist settings and bridge-token bytes/modes remain
exact. The application DB was exact through activation; the later fresh QA project
creation legitimately adds its own application reservation and changes that DB hash.
It is not included in an “all application bytes unchanged” claim.

## Live browser smoke and final readback

Root used a fresh owned headed Chromium CLI session against normal8841, not a fake
transport, at1700×900,1280×768 and1280×460. Eight PNGs were directly inspected.
This is a bounded post-cutover smoke, not another whole-product E22 or native-media run.

1. Landing opens; create a new explicitly named disposable project through Brief.
2. Save one-choice/two-ending Brief and navigate to Source with its synopsis intact.
3. Open Creator's four-node planned skeleton; edit opening title/summary and save its
   graph draft. No content confirmation, route application or production authority.
4. Switch to Pro and return to current-project Brief; settings remain the saved values.
5. Close; directory shows the project closed and neither retired demo.
6. Reopen, reload Creator and assert the saved opening title/summary in the DOM.
   Read-only SQL independently verifies one `story_graph` draft at revision2;
   payload SHA256 `7cd954911c4453b080c297d3d4a18842c58927d4ed15aa3b6e3de9dc4083cf99`.
7. Inspect desktop and short-window page-scrolled graph/detail slices; console has
   zero errors/warnings. Close the disposable project and close only this owned browser.

QA project `69530c91-2154-45cb-85f7-2e0b4078d27e`, titled
`QA · 8841 activation · 2026-10-10`, is left closed with its draft preserved.
It is not a playable installed demo. At11:18:20UTC the catalog contains only this
current-schema closed QA project; both retired IDs return404 and specialists are idle.
A draft endpoint read after closing correctly returned409; it did not reopen the project.

Artifacts are retained in the candidate worktree at
`/private/tmp/plotloom-one-story-rebuild.gfnqlc/output/playwright/normal-cutover-2026-10-10/`:
`before.json`, `stopped.json`, `retired.json`, `retired-with-snapshot.json`,
`activated.json`, `post-browser.json`, `runtime.json`, `post-browser-status.json`,
the verification helper and eight PNGs. The original failing comparison remains
in the task output. Probe corrections for a guessed container path, SQL column and
JSON-escaped text were verification-command errors, not product repairs or waived gates.

## Completion boundary

This closes required main publication and normal activation. The qualified named
Create → same-project Revise → Recover journey, finite whole-product visual/text
E22 pass and focused test-health cleanup are owned by their existing receipts.
No executable inputs changed during this operational step. Independent read-only
cutover review found no in-scope source/runtime/data blocker and directly inspected
the same eight PNGs, not a renewed E22 pass. Its snapshot-baseline precision finding
is incorporated above; it made no product, service, test or data writes.

Creative/audible/perceptual media quality and owner walkthrough acceptance remain
separate. Scene/Prop downstream consumption is a new capability boundary,
configured API intent is unconfigured (not a native fallback), and optional populated
native Cast relationships remain an unexercised variant. Normal service provider
configuration was not changed to adopt isolated QA's process-only H3 configuration.
There is no backward-compatibility layer, adapter, retained acceptance-receipt rewrite
or duplicate job.
