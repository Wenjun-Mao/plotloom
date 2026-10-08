# Current-Art authority in the reference gallery — 2026-10-08

Status: **PUBLISHED / ACTIVATED / EXACT-HEAD CI PASSED**.
This closes a demonstrated E22 affordance and wording defect, not the full
Create → Revise → Recover journey or native/creative media acceptance.
Baseline: clean main `4c214c3`, executable `c26920b`; one source writer.
Executable `3ad91e4f76d8551ced3a9de9381280960501c740` is pushed to `origin/main`.
Healthy normal8841 serves its exact qualified static assets. The full unfiltered
[remote CI run](https://github.com/Wenjun-Mao/plotloom/actions/runs/37801077786)
is bound to that executable and completed success: verify and both browser
shards passed, final shard completed at2026-10-08 16:22:54 UTC. This remote
qualification does not close the remaining native/revision acceptance gaps.

## Root cause and owning repair

The [typed-currentness checkpoint](2026-10-08-review-context-diagnostics.md)
recorded an enabled **准备图片生成任务** in retained stale Art. The server correctly
requires current accepted Art; the gallery received lifecycle/refresh ownership
but no explicit Art-head authority. Readability was incorrectly treated as
permission for generation and reference selection.

ArtPanel now explicitly supplies `acceptedArtCurrent = status === "accepted"`.
Preparation, editing, sending, revision and reference selection require both that
authority and the existing owner/busy/refresh eligibility. Individual candidate
currentness and accepted-delivery checks still apply; an older valid candidate
is not rejected merely because a newer task exists. Preparing or delivering a new
Art candidate, reopening Art and upstream staleness all retain readable old Art
without granting current-head authority.

Cancellation and late-delivery checking retain their distinct server eligibility;
they are not disabled merely because Art became stale. Lifecycle/read-only/busy
restrictions still apply. Reading, thumbnails, zoom, comparisons, details and
same-session requirement drafts remain intact. No API, schema, admission rule,
frozen request, compatibility layer or protected setting changed.

The gallery now says **查看保留的参考图片**, with a clear explanation that current
Art must be confirmed before preparing, sending or selecting. Independent pixel
review then found the disabled field still invited editing: **可以用中文补充构图、
光线或细节要求…**. Non-frozen disabled fields now say **图片要求（暂不可编辑）**
and **当前只能查看已有图片要求；暂不能编辑或准备新图片任务。** Frozen task
copy remains accurate; successful revalidation restores editable guidance.

## Actual desktop and operation evidence

Disposable real project-folder/FastAPI fixtures on18991 and matching Vite5178:

| State | Project | Task |
|---|---|---|
| Source changed; stale Art, prepared image task | `d6019151-2721-40af-8b2a-5a5d6bc955d9` | `ij_ff4af0cb16344b1cbf0095b20bf3a252` |
| Cast reopened; stale Art, exported image task | `34be40f4-8443-45a3-85d9-f36570201e40` | `ij_970687f4753640488f48d8f29cb6c977` |
| Art reopened, retained accepted r1 | `4eea8817-9cdd-41b0-8739-32981f276cc0` | retained delivered fixture |
| New Art candidate prepared, retained accepted r1 | `c29c6df9-ebd6-4898-9b87-d062d727f77f` | retained delivered fixture |
| Accepted-current baseline | `6321fc39-eb19-44fb-ab94-bbe6dc3c377c` | current delivered fixture |

Each has one explicit32×24 fixture PNG, not native generation. No provider keys,
real specialist dispatch, author acceptance or owner-data seeding was used.
`output/playwright/art-reference-eligibility-20261008/` retains30 initial captures,
30 final captures and two actual zoom/details frames. All five states were checked
at1280×768,1280×460,1700×900; no phone/1024px tests. Final source/Cast fixtures are
accurately named `*-cancelled` after the successful operations below.

- In every retained-head case, generation/selection is disabled; existing images
  load and the document does not exceed viewport width. Current baseline keeps
  revision and reference-selection controls enabled.
- Actual stale-image zoom, close and expanded provenance/details send zero writes;
  exact Art, proposal and decision GET readbacks remain unchanged.
- Prepared stale task cancellation succeeds and persists `cancelled`.
- Exported stale task **检查图像交付** returns `awaiting_delivery`, not a resend;
  its explicit cancellation then succeeds. Exact Art/decision state remains intact.
- The only three observed POSTs are the exact identified cancel/refresh/cancel.
  Reload keeps generation locked and the retained image loaded.

Independent GPT-6 Luna/Max directly inspected all30 initial PNGs and15 final
controls PNGs, closing the copy finding in actual pixels. Root separately viewed
short Gallery/controls, wide current controls and expanded details. Ordinary
viewport folds are not missing controls; captures deliberately scroll to the
target and keep the Gallery notice below the fixed toolbar. This is finite
fixture/state coverage, not every gallery permutation or full-page acceptance.

After activation, root directly inspected six normal Rain Gallery/controls PNGs
at all three desktop sizes (`normal-rain-*` in the same artifact directory).
The original native environment image loads; selection, preparation and editing
remain disabled with the repaired explanation. No document-width overflow or
API writes were observed. The only console error is the explicitly sandboxed
archived static report's blocked script, not a current application error.

Independent GPT-6.1 Sol/Medium reviewed the action contract and the final copy
delta with no actionable defect. Requested settings were explicit; effective
settings remain unverified. Read-only Relay registration was denied by filesystem
permissions; native agent finals were collected without a workaround.

## Qualification and protection

- Focused frontend:43PASS600ms; final full frontend:737PASS/97files3.81s.
- Application/E2E types and lock/diff checks:PASS.
- Existing backend current-Art regressions:4PASS/20deselected4.31s. The unchanged
  backend's1256-test qualification is reused from `c26920b`, not a new full run.
- Two final deterministic builds:PASS, with identical shipped hashes. Final890 executable/test/build/config/static inputs
  recorded before the gate, SHA256
  `337b81606d8ea3609821dbe0ccae208c1f828da880c24b3009e767da637f5aa0`.
- Fresh wheel/isolated installed smoke:PASS; directory
  `/private/tmp/plotloom-art-eligibility-wheel-20261008.n7ZK9b/`, wheel SHA256
  `5bc37ec9b2fa6828f1d92dd86471417657e94440576d355f08f4ca1e448d395c`.
- Full existing unfiltered236-browser gate:PASS6.6m, default four workers and zero
  local retries. All890 inputs remain unchanged after the gate, repeated build,
  publication and activation. Native-clock probes are offline controls, not genuine
  H3 acceptance. The preserved final gate packet is
  `output/playwright/full-lifecycle-2026-10-07/192-art-eligibility-full-gate/`.

Normal8841 recovered healthy after the reported reboot; known H3 completion is
terminal, not replayed. Before the controlled build stop, while stopped and after
activation and the read-only normal UI audit, the
exact owner database/file/settings aggregate remains
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
Wind17/Rain67 managed files and three protected settings. Only the idle normal
container was stopped for the build and restarted after qualification; its bridge,
dispatches and credentials were untouched. Container health, `/healthz`, the native
bridge check and exact normal served hashes pass:

- JS `c587f4f65d418426f7bcfdadfcc40d4f775e44afd849ff90a4db1c38bd8378fd`.
- Main CSS `000aac5623f5ce4cf63f007979f7e7d1e09f9aa3698a1da3556fe400dbec3b7c`.
- Secondary CSS `99dd1d0435f1373766564583298fb848b6fa8fccae5847181b3d6341dbafd6c4`.

Only owned disposable18991/Vite5178 services and audit browser sessions were
stopped after their checks; fixtures and generated evidence are preserved. No
generation task was replayed. CI requires explicit workflow dispatch rather
than a push trigger; the exact-head unfiltered run above was started once.

The [post-reboot native checkpoint](2026-10-08-native-decoder-recovery.md) now
qualifies the retained opening original and selected segment through VideoToolbox;
the earlier failure's cause is still unknown. All-route/multishot media, supported
post-install revision/rebuild and remaining Outline/Creator/Pro state slices
remain open. The full lifecycle goal remains PARTIAL.
