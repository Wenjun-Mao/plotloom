# Native media lifecycle and recovery — October 8

Status: finite native recovery checkpoint PASS; full Create → Revise → Recover
acceptance remains PARTIAL. The two presentation/read-admission defects below
were subsequently repaired and qualified in the
[203 read/lifecycle checkpoint](2026-10-08-load-retained-media-qualification.md).
This original recovery sequence executed on published executable `04a4d02`,
documentation baseline `e760620`; no generation, canon or media selection writes.

## Exact targets and authority

- Original UI-origin QA project `b3a933f7-b6fc-40e3-826f-5162f95a119a`,
  “QA 新全程 灯房两条路 2026-10-07”, in isolated8861/8862.
- Restored same-ID copy in a DIFFERENT outputs/application installation:
  `.local/full-creator-2026-10-07/native-recovery-196/installation`,8873/8874.
  Only this disposable restored home was permanently deleted.
- Original project and exported snapshot remain intact. Owner projects,
  credentials and protected settings were never reset, imported or deleted.
- Evidence below is in `output/playwright/full-lifecycle-2026-10-07/`.
  Native playback proves functional delivery, not artistic/audio approval.

## Executed checks

| Check | Observed evidence |
|---|---|
| Current native routes before lifecycle | `196-current-native-routes.txt`: opening→route-only choice→East and opening→choice→West; real trusted terminal `ended`,5s/120 frames,0 drops/no errors; no writes; jobs unchanged |
| Close/reopen | Actual directory controls and ACKs; second clean loop has valid pre/post six-view readbacks and 15-file asset inventories: `196-native-recovery-readback-open.json`, `196-native-recovery-after-close-reopen.json`; no content differences or byte changes |
| Archive/unarchive | Actual archive/restore controls and ACKs; `196-native-recovery-archived.json` preserves all 15 asset hashes. Archive correctly withdraws current story admission without deleting historical selections. `196-native-recovery-after-unarchive.json` has no content/job differences and identical assets, excluding the explicitly named lifecycle/update fields |
| Snapshot | UI creation of `d1a4d39e-b1d0-49b2-a541-67d3a71dda79`; final status readback complete and visible UI receipt in `196-native-snapshot-receipt.txt`, `196-native-snapshot-complete.png`. No second creation request |
| Operator restore | `196-native-operator-restore.json`, `196-native-restored-inventory.json`: 49 inventoried files/15 managed assets, no size/hash mismatches; recorded snapshot DB hash matches the restored DB BEFORE service startup |
| Restored saved state | `196-native-restored-readback.json`: all six audited API views and asset inventory match. Independent WAL-aware read-only audit matches project/stage heads, three ingested H3 jobs, selection/review/segment rows and hashes. Both recovery records clear with zero operations. Live DB byte hashes may change after startup; this is audited-state preservation, not live DB byte identity |
| Restored browser playback | `196-restored-native-routes.txt`: both terminal endings succeed,5s/120 frames/0 drops/no errors, no writes and unchanged jobs. Route-only choice inspected at1280×768,1280×460,1700×900 (`196-restored-route-only-choice-*.png`) |
| Typed deletion guards | `196-native-delete-guards.txt`, `196-native-delete-wrong-title.png`, `196-native-delete-clean-confirmation.png`: wrong title disables confirmation; cancel sends zero writes; reopened challenge is empty |
| Exact disposable deletion | `196-native-delete-requests.txt`: one POST to8873 exact-ID `/permanent-delete`, documented204 No Content. `196-native-delete-readback.txt`: project and selected-media reads404, directory empty; `196-native-restored-copy-deleted.png` shows completion |
| Erasure/preservation boundary | `196-native-delete-files-and-idle.json`: restored project home absent, original home and snapshot present. Deletion removes the copy's retained media but is recoverable through the independently retained snapshot |
| Owned idle restart | Verified exact owned processes idle (`busy:false`,zero activeTasks), gracefully stopped original35767 and restored48672, restarted same compositions as56164/56165. Original six-view readback and assets unchanged in `196-native-after-idle-restart.json`; restarted8873 directory remains empty |
| Restarted native playback | `197-native-restart-routes.txt`: original opening/East/West complete both routes, trusted terminal events,5s/120 frames/0 drops/no errors, no writes and unchanged jobs; `197-native-restarted-west-ended.png` |

Snapshot remains at
`.local/full-creator-2026-10-07/installation/outputs/.snapshots/b3a933f7-b6fc-40e3-826f-5162f95a119a/20261008T181152279138Z__d1a4d39e-b1d0-49b2-a541-67d3a71dda79`.
It does not copy provider credentials/settings or replay dispatches.

## Dedicated visual/text findings — original diagnosis, subsequently repaired

1. A previously loaded tab reloaded while its project was closed correctly gets
   backend409 `project_closed`, but the UI presents “未命名项目”, “尚未保存的项目草稿”,
   “先保存项目” and a false missing-shot warning. See
   `196-other-tab-closed-snapshot.txt` / `196-other-tab-closed.png`.
   The aggregate loader drops structured availability; the controller renders
   the destination's editor against a fabricated blank snapshot after failure.
   Repair belongs to route-owned load availability, not the shot lookup or backend.
   A matching accepted editor must still survive a failed refresh with writes disabled.
2. Archived clips are retained but guidance calls them “已过期、被拒绝或不再适用”
   and recommends generation; the segment panel falsely reports insufficient
   footage/frame timing. See `196-native-archived-media-snapshot.txt` and
   `196-native-archived-media-guidance-{1280x768,1280x460,1700x900}.png`.
   Operational currentness combines lifecycle with frozen applicability, while
   the UI treats every false value as stale/timing failure. Segment preview also
   unnecessarily requires production currentness. Repair needs named admission
   reasons and a separately owned immutable-evidence read contract; production
   selection/preparation/story playback must remain blocked during archive.

Independent read-only contract review and actual pixels support these diagnoses.
They were not waived. The linked203 checkpoint owns the later repair qualification;
these original failed observations remain historical evidence.

## Method limits and helper failures

- First baseline helper misused native Fetch's `ok` property as a method; a clean
  second close/reopen loop supplies the valid inventory baseline.
- An archived check incorrectly expected a disabled confirmation button; actual
  contract removes it. Subsequent source/DOM checks confirm absent selection,
  disabled preparation and unchanged media. This is not a product defect.
- Snapshot helper expected a period instead of the actual completion colon;
  it timed out after the creation response. Read-only final status and visible
  receipt establish completion; the original response body was not captured.
- Delete helper attempted JSON parsing of the documented204 response and failed
  AFTER the successful mutation. Requests and read-only readback establish the
  actual result; deletion was not repeated.
- No busy shutdown, artificial lease clearing, duplicated delivery, recovery
  overwrite or creative acceptance occurred. Same-node multishot and completed
  production revision remain outside this finite checkpoint and open in the run.

Owner protection rechecked after deletion:
aggregate `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`,
17/67 managed files for the two owners and3 protected files unchanged.
Source qualification remains the linked
[04a4d02 receipt](2026-10-08-native-routes-endframe-qualification.md), not a new
qualification inferred from these native checks. Exact04 CI37820366305 at18:26UTC:
verify PASS; both browser shards still running.
