# Native routes and end-frame qualification — 2026-10-08

Status: **FINITE NATIVE ROUTES PASS / REPAIR QUALIFIED LOCALLY**.
The full Create → Revise → Recover goal remains PARTIAL. This continues the
[approved run](../roadmap/2026-10-07-full-creator-e2e-repeat.md), the single
[playbook](../creative-workflow/graph-workbench-acceptance.md), and the
[opening native checkpoint](2026-10-08-native-decoder-recovery.md).
Baseline main is `d5dd723`; executable Python is unchanged from qualified
`3ad91e4`. The current frontend repair is uncommitted, not a published candidate.

## Exact native baseline and bounded actions

Disposable project `b3a933f7-b6fc-40e3-826f-5162f95a119a` retains approved
Storyboard r1, proposal r3 and the same physical无人灯房 scene contract. The
route directions/outcomes remain review-only; no visible east/west mechanism,
person, rescue, text or equipment was invented to fill that creative gap.

| Shot | Native job | Selected segment | Selection revision |
|---|---|---|---|
| Opening | `vj_c121f94f27dc4704ac27dbc3cbdd2b8d` | `d5c45979-286b-4e62-8a3d-1b28369c49e3` | 1 |
| East | `vj_49b734e207e043d7a11bd1fc8666876e` | `84969bb2-d629-4e74-a26f-ecf2d17d9d9a` | 1 |
| West | `vj_11130145950b4ebda1d45636e8cdf687` | `78ff680f-322f-40e6-8111-39aacda5b0fc` | 2 |

East/West were each prepared and submitted once through the actual UI and
retrieved once. Both use quality8 landscape832×480, five seconds, explicit
centre crop, native audio, seed20261007 and no endframe. Frozen snapshots are
`2de5f043849e7cae8938a3d1f1eeace9831223ec7d1f08bcb855045bff11a5c3`
and `a9e5e70275e462138cc8b8c0b45b306c58253e54c958f2f38cea71bff4498fa6`.
An independent source/probe review found no frozen-authority mismatch. The
shared still and intent r1 remain exact; no completed job was resubmitted.

Original East/West files are290,551 bytes, with distinct SHA256 values:
`f02dc20791c6cedb8b49cfceefb2037f311be22e5fb41ae9909dab0beb0d27f3`
and `c29eb7333a9ee4805b58250d85762299633dd310a1c4f8cf7783f4dfac199f23`.
Both probe as H.264/AAC,124 frames at24fps and5.167 seconds. Their explicit
0–120 derivatives are264,125 bytes/five seconds and share SHA256
`d9be8c4c842418aaea2a6efcc181cdc5b6f697cc90b912c5dcfcccf0e8c9d9fd`.
Original hashes differ while derivative hashes agree; the cause is not diagnosed.
Opening original/derivative identities are recorded in the prior checkpoint.

Actual original and prepared-segment controls reached trusted native `ended`.
West's first original play recorded three dropped frames; a subsequent play
added zero drops. That first result remains retained, not rewritten as smooth
playback. Segment and story-route plays recorded no dropped frames/media errors.
Browser cumulative counters and encoded-frame probes remain separate measures.

West rejection Cancel sent no mutation. Explicit rejection revoked its selection;
explicit reasoned reopening retained the rejection history, then preparation,
preview and selection produced current selection r2. No regeneration occurred.
All QA review notes exclude creative/media-quality approval. Fresh API readback
and independent WAL-aware read-only DB queries confirm all three selected,
current segment rows; an initial `immutable=1` DB observation ignored WAL and
was retracted, not patched as a product defect.

## Actual all-route playback

At17:27:53 UTC the actual Play UI completed East, restarted, played the opening
again and completed West. Each complete route has one opening clip, a paused
route-only choice with zero video elements, and one ending clip. Each ending
reached trusted `ended` at5 seconds,120 browser frames, zero drops and no media
error. The selected route history and exact East/West playback URLs differ.
The last frame stays visible and **从头开始** is available. Writes were empty
and complete job readbacks were identical before/after.

Installed headed Chrome154.0.8037.97 used VideoToolbox/Metal on Apple M5 Pro.
Returned CDP records, native events, API identity checks and actual pixels are
retained, not inferred from screenshots alone. Root inspected terminal views
and the West full-page1280×460 capture. No document-width overflow was observed
at1280×768,1280×460 or1700×900. Lower controls require ordinary page scrolling
where the viewport is short; this is not clipping or phone support.

Artifacts live under `output/playwright/full-lifecycle-2026-10-07/`:
`195-native-story-start-diagnostic.txt`, `195-native-story-routes-diagnostic.txt`,
East/West original/segment diagnostics and terminal/selected captures,
`195-native-route-{east,west}-terminal.png`, and
`195-native-route-west-{1280x768,1280x460,1700x900}.png`.

This closes finite E17 minimal all-route playback, not same-scene still preview,
within-node multi-shot advancement, audible acceptance, visual continuity or
visually distinct ending acceptance. Environment/Prop reference consumption by
downstream shot generation is still unproved. Visible generated exterior detail
is not promoted to approved story canon.

## Demonstrated repair and root cause

End-frame UI treated unread null, known revision-zero default and persisted empty
selection alike. Failed refresh retained H3 preparation authority; owner identity
omitted Storyboard revision, and an already-running prompt callback could survive
button disabling. [ADR0135](../adr/0135-end-frame-read-qualification.md) records
the owning read-qualification and prompt-authority repair, without changing the
server's approval/revision admission or adding compatibility inference.

Paired setting/catalog reads now qualify the current owner. Pending/error/save
uncertainty withdraw preparation and in-flight H3 source/prompt authority. Last
known decision and author input stay readable, explicitly unverified. Unknown
save outcome requires rereading, not automatic mutation retry. Revision zero
says **当前设置：不使用末帧画面。**; persisted settings retain their true revision.
Reopen feedback describes the action boundary rather than assuming nothing was
subsequently prepared. Route-only copy explains that no footage is required.
Frozen quality comes only from its explicit current field; old profile-name
inference was removed.

Native expanded synthetic503 details exposed a second root cause: shared notice
row layout squeezed Chinese guidance and unwrapped raw JSON widened a1280 page
to6198px. Scoped stacked layout and wrapping raw details repair that container;
no evidence is truncated and page overflow is not hidden. Actual post-fix native
GET-only fault/retry at all supported sizes reports document widths1280/1700,
zero writes and recovered default. Root and independent reviewer inspected all
three actual after captures; at1280×460 lower diagnostics use ordinary scrolling.

Evidence: `195-endframe-long-error-before.png`,
`195-endframe-long-error-diagnostic.txt`,
`195-endframe-long-error-after-{1280x768,1280x460,1700x900}.png`, and
`195-endframe-long-error-after-diagnostic.txt`. Formal pending/error/recovered
fixture captures were preserved in `195-read-state-long-error-after/` before
the broader gate replaced its working output. Fixtures are offline controls,
not additional native media generation.

## Current qualification and remaining work

- Focused29 tests and fresh full762 frontend tests/99 files:PASS.
- Application/E2E typechecks, lock/API F401 and diff checks:PASS.
- Two deterministic builds:PASS, with identical shipped bytes; fresh unfiltered
 239-browser gate:PASS7.1m, with four workers and zero local retries. All893
  executable/test/build inputs stayed unchanged through the gate and repeat build;
  SHA256 is
  `a2cf7857fe18ca124f69cf95dada391e5406739559488f6273ff9327cdc3162f`.
- Fresh wheel/isolated installed smoke:PASS. Wheel
  `/private/tmp/plotloom-endframe-wheel-20261008.39zWuU/plotloom-0.1.0-py3-none-any.whl`
  SHA256 is `347c607bdc16f2e21734ffe372ff98b44dd4a0b0cbf5ec20735755472c5966cd`.
  Backend1256-test qualification is reused from unchanged `c26920b`, not rerun.
  Final browser artifacts remain in `195-endframe-full-gate/`.
- New three-desktop fault checks:PASS13.4s. The first fixture accidentally reduced
  shot duration below its authored audio events; the fixture was corrected, not
  the product validator. Failed evidence remains in `195-read-state-fixture-failure/`.
- Independent GPT-6.1 Sol/Medium reviewed source, ownership/races, tests, ADR and
  final layout pixels with no blocker; effective model settings are unverified.
- Protected owners/settings still match
  `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
  Normal8841 is healthy and its checkout mount serves the checked JS
  `262c56acd8b578a784fa75942a777da14f73981f31d1ea8e00b795ab4806f558`
  and CSS `34b731750d6d1d49173223961b9f586f3f2525d67bd3e675aff82987fdd3edac`.
  No backend or bridge restart, credential write or owner-data mutation was needed.

Native multi-shot, revised installed production, configured model intent,
video-bearing lifecycle/recovery and remaining E22 states stay open. The reported
computer crash and previous decoder failure's cause remain unknown. The next
safe run slice is reversible lifecycle/recovery on this exact native baseline;
post-install rebuilding needs its own approved contract rather than an adapter.
