# Draft, credential and lifecycle reading states — 2026-10-08

Status: **SCOPED QUALIFIED CHECKPOINT**. Included in the current full
E2E run and [whole-product visual/text audit](2026-10-08-whole-product-ui-audit.md).
This is not full lifecycle, native generation, all-route playback or artistic
acceptance. Reusable checks are in
[E22](../creative-workflow/graph-workbench-acceptance.md#e22-全产品视觉与文案专门检查);
stable decisions are in [ADR0132](../adr/0132-creator-ui-reading-boundaries.md).

## Root causes and owned repairs

| Observed failure | Cause and durable repair |
|---|---|
| Dirty Archive consent said 保存并切换 | A close boolean could not express archive intent. Shared consent now carries navigate/archive/close intent, with action-specific wording and unchanged callbacks. |
| A server-saved draft was called 未保存 | Recovery copy ignored its persistence source. Project-saved, session-only and reconciliation drafts now have distinct truthful guidance. |
| Frozen-key guidance mixed Profile/Key jargon and assumed continuation | Shared repair/continuation credential admission now uses action-neutral Chinese guidance, retaining the exact frozen profile as secondary evidence. Saving a key does not automatically run work. |
| The missing-key Inspector hint did not appear in a durable project journey | Loader read the profile catalog behind its state owner's back. Refresh now goes through the catalog owner used by both admission and Inspector. Missing profile, missing key and failed read remain distinct. |
| Obsolete profile/key response adapters remained | Current server contracts require readiness/trusted adapters and per-profile keys. Removed retired settings fallback, inferred readiness, single-key migration/default alias and hardcoded adapter fallback; exact-current-contract regressions replace obsolete expectations. This is not a claim that every legacy path elsewhere is removed. |
| A successful snapshot receipt disappeared above the viewport when 服务状态 opened | Opening intentionally returned the toolbar to document flow, but did not reveal its reading entrance. Open-only nearest scrolling reveals the summary anchor while preserving unbounded normal-flow diagnostics. No snapshot, focus, generation or selection behavior changes. |

## Actual entry points and semantics

- Successful durable navigation can flush its draft and proceed directly. The
  consent capture deliberately fails the disposable draft PUT; it does not
  pretend every navigation opens a dialog.
- Directory Archive and Close consent require unacknowledged local input.
  A held first draft PUT establishes that state; an acknowledged server draft
  alone is not dirty local consent. Topbar 保存并关闭项目 directly saves/closes,
  rather than opening the directory disposition dialog.
- Navigation/archive discard removes unacknowledged local edits while retaining
  already-saved drafts. Directory close-discard handles the exact current-stage
  draft after quiescence; close-save preserves recoverable drafts without
  confirming formal creative content.
- Restoring a server draft changes the editor, not canonical content. Saving
  an unchanged Brief consumes its exact draft with DELETE, not a canonical PATCH.
- Frozen credentials require the exact current catalog profile. No active-key
  borrowing, unrelated settings form, automatic model change or automatic run
  after key save is introduced. No-auth work needs no credential read.

## Direct viewport and operating checks

Owned headed Chromium session: `creator-ui-dialogs-qualified`. Disposable project
`af69488d-e0eb-4ddc-be5b-5c8b33fbb07d` on isolated8861; canonical Brief r2.
Only 1700×900,1280×768,1280×460; phone/1024 support remains retired.
Artifacts: `output/playwright/full-lifecycle-2026-10-07/143-ui-dialog-audit/`.

- Nine consent cases: navigate, directory Archive, directory Close ×three sizes.
  Exact headings/actions, non-overlapping heading/body/footer, viewport bounds
  and actual control hit targets checked. Each was cancelled; no archive/close/
  generation write occurred, canonical title remained intact. Held draft writes
  settled before routes were removed; exact draft cleanup used normal Save.
- Three project-saved recovery cases: correct persistence wording and reachable
  Restore/Discard controls. Actual Restore returned the exact saved payload;
  canonical Brief/revision remained unchanged. Normal unchanged Save consumed
  only its current draft; no lifecycle/provider dispatch occurred.
- Root directly inspected all twelve dialog frames. Independent Luna/Max review
  identified redundant recovery wording; final detail is 此草稿已保存在项目中；恢复后可继续修改。
  All three changed recovery frames were recaptured and directly re-reviewed.
  The nine unchanged consent geometries were freshly re-exercised; do not imply
  a second independent inspection of those unchanged pixels.
- Actual disposable snapshot POST returned201/complete. Before repair, all three
  receipt captures had status bounds y=-179.5,bottom=-24: successful data, failed
  reading position. After repair, opening from scrollY500 reveals summary0–32
  and receipt152–182.5 at every size, without page-width overflow or API writes
  during toggles. Root and independent Luna/Max inspected all three status-after
  frames; the short viewport's ordinary lower fold is not an obscured receipt.
- Oversized diagnostics regression uses the real Settings catalog read, then
  Cancel. It asserts actual stress text reached the status surface, summary
  visibility from a genuinely scrolled sticky state, normal document flow,
  content taller than every viewport, receipt scroll reachability, unobscured
  authoring-field hit target, close/reopen and zero API writes after the deliberate
  snapshot. Existing snapshot/restore media/draft/lineage journey remains intact.
- Nine permanent-delete challenge states: blank, incorrect and exact title ×three
  sizes. Blank/incorrect remained disabled, exact enabled; actual button hit
  targets and viewport bounds passed. Root inspected the three exact-title
  frames, and independent Luna/Max directly inspected all nine. Irreversibility,
  project identity, task guards and exclusions remain readable. Cancel preserved
  the entire project readback and sent zero API writes; no deletion occurred.

Frozen-profile and recovery session/reconciliation branches have functional
tests, not separate pixel qualification here. The challenge check does not qualify
every actual deletion, busy-refusal or uncertain lifecycle result state.

## Preserved failures and exclusions

- Initial full browser gate exposed the catalog-owner defect; later focused
  exact frozen-profile journey passed without weakening its settings/run guards.
  Two intermediate217 browser gates passed before the status repair and do not
  qualify that later change.
- Initial stress suite:1PASS/3FAIL, because no-run projects do not eagerly load
  profiles; retained in `status-regression-setup-failure`. Corrected real Settings
  read then Cancel established the intended state.
- Next stress suite:3PASS/1FAIL; actual wide diagnostic height592px did not exceed
  900px. After two failing setups, method was reassessed: stress payload increased
  from500 to2000 repetitions, not a smaller required height or product tolerance.
  This second failure's PNG was overwritten by a prematurely started full gate
  before copying; its command/error record remains, but no saved PNG is claimed.
- That premature full gate was deliberately interrupted:6PASS,4 interrupted,
  210 not run, exit130. Interrupted tests are not classified as product failures
  or a release gate. Corrected focused snapshot/status suite4PASS19.4s.
- Manual harness false assumptions remain excluded: refilling an already-restored
  identical title cannot require a new PUT; unchanged Save is DELETE, not PATCH;
  topbar Close is not directory consent; reload with beforeunload yields control
  and must be split into explicit CLI steps. Wrong initial/stale captures do not
  count as completed state cases.

## Qualification and remaining work

Final stable source/test/config/static fingerprint:863 files,
`3b9ec9930f44ac7d2e32b5b1e75b06bb9a277f2adec43ae2694a32c2c192cfa3`.
It is identical before and after the unfiltered220 browser gate:220PASS6.1m,
default4 workers and0 local retries. Earlier native playback failures remain
unexplained; this PASS is not a decoder repair. Frontend683PASS90 files;
application/E2E types, deterministic build,
lock/API-unused-import checks and installed-wheel smoke PASS. Wheel is in
`/private/tmp/plotloom-ui-dialog-audit.TSmzBh/wheel/`. Existing build chunk and
test environment warnings remain visible. Backend1245PASS is earlier unchanged
Python evidence from this same audit chain, not a newly rerun backend gate.

Fresh owner readback remains exact:
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`;
Wind17/Rain67 files, both database/schema sets and three protected settings files.
No owner/native media job/settings were changed by this bounded audit.
Independent Sol/Medium source/receipt review and Luna/Max pixel review are closed
with no remaining concrete finding in this bounded checkpoint. Publication and
exact-head remote CI are recorded below; local PASS is not remote CI success.
Normal8841 returns200 and serves the exact current JavaScript hash
`fe0f346fff571621959fefbf3995d4548550dca962b46526b456be6db3bc1ab4`,
base CSS `3b0c81ad3f5e2d92a455826ba114d269fedb3ddbf192ffed70c5381bbe1ea35d`
and product CSS `42beb639a4681beb6bea3a3b04916ee1eb63481a821eb42994f152de7e2d6850`.
All match local files; no service restart or protected-setting write was required.

Remaining whole-product state slices are kept in the linked register, including
dirty/upstream-stale review combinations, structural hover/focus, immutable
report permutations, session/reconciliation recovery pixels and frozen-key
failure pixels. Native decoder/all-route/multi-shot and post-install revision
capabilities remain separate open lifecycle prerequisites. A software gate or
readable failure state does not qualify successful native execution or playback.
