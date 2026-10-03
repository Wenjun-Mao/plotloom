# E2E-first real-media continuation

Owner authority: [eight-hour continuation](../roadmap/2026-10-03-e2e-first-continuation.md),
starting 2026-10-03 18:43:28 UTC. The outcome is a usable complete creator/player
journey with acceptable media, not final-film approval. The owner expressly
authorized labeled provisional selections in the isolated copy and kept new
sound acceptance pending personal listening. This receipt supplements the
earlier [reference/script/storyboard loop](2026-10-02-stage23-live-completion.md).

Source candidate starts at `e65830033edf248d22e7a6d8286f0c65e1c29698` on retained
`main`. Root is the sole live/UI/provider writer. Source handoffs were serial;
Sol/Medium implemented presentation ownership, Luna/Max implemented explicit
reopening, and root integrated and independently reviewed both. Actual native
finals were collected; no worker identity or Stop was synthesized.

## Durable implementation and observed usability repairs

- [ADR 0107](../adr/0107-shot-production-presentation.md): append-only,
  source-hash/CAS-bound shot presentation review. Exact nonspoken Chinese is
  selected from current-shot or immediate same-scene predecessor authority,
  never typed into a provider-only override. Image/H3 use one effective
  projection. Only the amended shot is invalidated; unaffected selections and
  immutable historical requests remain intact. Additive schema admission is
  limited to the exact predecessor layout.
- [ADR 0108](../adr/0108-explicit-h3-rejected-take-reconsideration.md): an
  attributed explicit reopening preserves rejection history, requires current
  H3 output and revision CAS, and does not generate, prepare or select media.
  A2 was reopened through that UI and selected only after normal playback.
- Independent review found a nonspoken/spoken ownership conflict in a synthetic
  case. The shared presentation boundary now rejects exact literals contained
  in canonical dialogue before appending a decision. It preserves unrelated
  dialogue rather than silently deleting cues. Focused and independent tests
  cover all presentation modes, contained literals and source immutability.
- Loading/failed media reads are unknown, not confirmed missing configuration,
  references, jobs or previews. Mutations remain withdrawn until authoritative
  reads recover. Current unbound image deliveries no longer appear falsely
  stale. Image history defaults to the selected shot; full-project history is
  explicit and every card retains its originating shot label.
- Bounded display-only shot titles avoid paragraph-sized selectors/cards without
  changing source IDs or frozen narrative text. Candidate controls now say
  `用此图审阅关键帧` / `当前待审关键帧候选`, and selection says
  `审核为当前镜头关键帧`. Rejected-take wording explains reopening explicitly.
- The real reader exposed raw `path-a` / `path-b` history. Display now maps
  authored choice labels and excludes automatic continuation edges; routing
  history still stores the original IDs. Reader labels use `当前段落` and
  `本段镜头`. This is presentation only, not a new branch state machine.

The two worker [presentation](2026-10-03-shot-presentation-contract.md) and
[reopening](2026-10-03-h3-rejected-take-reopen.md) receipts retain their own
earlier source checkpoints. They are not substituted for root's live evidence.

## Twelve current selected real-media segments

All cuts are 60 frames / 2.5 seconds at 24 fps, with 80,000 decoded native
audio samples at 32 kHz. Selection and currentness were independently read
after final isolated backend activation: **12 selected / 12 current**.

| Cut | Video job | Selected segment | Acceptance boundary |
| --- | --- | --- | --- |
| C1 | `vj_4d259d91e0c049f985aedcfbd12ac469` | `7b204194-18a8-4758-bcb3-b7eb714f6ea1` | Prior owner visual/sound review |
| C2 | `vj_9d1efcc0a49349c4b2500b1b5cb05d91` | `9f324db4-aa18-4e1a-adc0-bc5e08165e06` | Prior owner visual/sound review |
| C3 | `vj_bcbe9aa2672c4a76800dc3df7c6ec649` | `4e9a6989-b094-46ce-8a68-ae93ca44a428` | Prior owner visual/sound review |
| C4 | `vj_dd35c39fd80241c08c5d772e913427cd` | `8a7d7670-05f9-4bb5-8a11-f6f5918573ea` | Prior owner visual/sound review |
| C5 | `vj_76a72a982acb44058115e67aa963d523` | `4d75aa82-2929-4a09-9bfa-499c5da00413` | Prior owner visual/sound review |
| A1 | `vj_177a64801d574581b42698d2308b19a6` | `9c0561ab-f133-412b-8682-476a9c420f14` | Prior owner visual/sound review |
| A2 | `vj_c30ca3742a6f4d9ab4a4f60c0e91ad08` | `e65d7e1d-138a-494e-bdb1-4bd780d7e26a` | Owner accepts following camera; provisional selection, new sound pending |
| A3 | `vj_ded2a1acb90e4ebfadc20ba58ba6d265` | `27256d30-7715-429d-aa78-61ef6a540bae` | Provisional visual/technical selection; new sound pending |
| B1 | `vj_4c0cb2112d6f4e82b4bba18fb75e50af` | `819da93e-0851-4451-b756-86e991cdf0c2` | Owner accepts wider geography; provisional selection, new sound pending |
| B2 | `vj_4f61075ac4de4f26abf8d55c8de6ec69` | `2ad3b943-569d-4e74-ad73-f3da1b4bb944` | New canonical popped-out draft; provisional, new sound pending |
| B3 | `vj_8498e30b3ae44f34a9c81c9b5bc9b2a2` | `61168c76-ecdf-497b-95d5-9bdca3edc7a8` | New canonical send state; provisional, new sound pending |
| B4 | `vj_4946a84ef11043fc985da24237fc6489` | `062d8f5d-48f1-4f1c-be9a-588348c0f0e6` | Provisional visual/technical selection; new sound pending |

Five fresh H3 jobs were submitted once each: B1, A3, B2, B4, B3. A2 reused
its retained owner-viewed retry without changing original bytes. All five
requested quality 8, 832×480, five seconds / 124 frames; measured outputs are
5.167 seconds, H.264/AAC. Explicit no-end-frame decisions and reviewed prompt
previews were saved before submission. B1/B2 use reviewed center crop for
1672×941 input; A3/B3/B4 use matching 832×480 input with mismatch refusal.
No fresh ImageGen call or alternate provider was used. No measured financial
cost delta is available.

| New cut | Seed | Request SHA-256 | Original SHA-256 | Segment SHA-256 |
| --- | --- | --- | --- | --- |
| B1 | `7540316614097988` | `6e2e21cb904b95e58dbd89545672f7ae2c99ce66732042ba93705306be7450ff` | `5db42efc4dd7f9cba7f2ec6aeaa9452ef1c8f0bc0242b4d67547ce9324946176` | `a7c422ba891c1f08aeffad121a3797af31cac979f2b98bae933ecea0234815a2` |
| A3 | `261169646671148` | `c86adaccc0866ad3b6d8f67bf645743b6150a03d905afc943a8bd8a1af59d5d5` | `a6cd13162a45fef672777dba4c862c79f115b305be455a961608e33cb3094964` | `db5e36dd1e12651dba8d62b000c739e5fb3906181ae724881fca12b253ff39d5` |
| B2 | `2363661064327674` | `f0e145c2a403f305fe28b49a1dc9a6217ab14ca6f6109110cfda14831cf13272` | `6afbe72c299dd8a3853cd2ebc4d71d9f7e08cb482914704250914d1b56640d7d` | `f093a2f5e3c92907f398e548ae27d3760813a11a8c74651a1259e9413e89d26f` |
| B3 | `1611691850115216` | `ab71d45c82cd84605e807ab877db19cd14f6ac6ebd0eac45bd14edc49c588b08` | `78ed626ceb52b42a5b22dd94d377a0516ae1136807377d13f42bded1f3424ef3` | `37b805f733241a1125f18868f69dcf6945b686bdc2012f1819f6a46536b37aaa` |
| B4 | `7170378655818814` | `0b70743a5eff94be988d6fa2e70770574c010e54d371aab86e19ecbba7835a01` | `bc34ed14b8229a16959f31b9aa10dbe4489bed64a89a03f9a160742506fc2c7d` | `b56041c6a6553cba51bb68fbdec236930b4814c3f385b1b8c8069b71d3d44393` |

B2 presentation r1 is `0476c3ef-63dc-4371-af40-8384714618a3`; B3 r1 is
`51b1be49-274a-427c-a5b5-52f6324cb9e3`. B3 inherits the exact nonspoken literal
`今晚不去了，明天见。` from adjacent B2. Its first frame is an unedited decode
of B2 selected frame59, hash
`99d3dee28bb235de4e91611dfd671fb5f81fc40b5fc72d15b78ddf60336179de`.
Its reviewed compiled prompt hash is
`d47ac957734fbb8ca8a3f2331313ddeef1e8b8589298f987586d5fed336dd8d0`.
Normal playback shows a white unsent draft becoming pale cyan-blue, with the
keyboard closing and sent state present by the 2.5-second segment end. The
large original message remains intelligible; no new reply is shown.

Output limits remain explicit: B2 has incidental tiny phone marks. B3 also
generates a smaller same-message bubble and UI marks on the phone, contrary
to the no-readable-phone-text direction. These are not new narrative facts,
and the copy review records this as an acceptable E2E imperfection, not full
instruction compliance or pixel-perfect/final-film approval. Camera/geography
polishing is deferred under the owner's revised criterion. The bounded popped-out
method is captured in the [H3 playbook](../operations/h3-prompt-writing-playbook.md).

## Actual UI and route evidence

CUA drove the real Codex in-app browser and the shipped static workbench on
8851. Read-only DOM media observations verified natural playback; no seeking,
synthetic `ended` event, fixture substitution or hidden application-state edit
was used for the real routes.

The creator flow exercised managed imports, intent/review binding, authored
presentation review, H3 quality/dimension/end-frame controls, six source-bound
English fields, complete prompt preview, one-shot submit/retrieve, 60-frame
segment preparation and attributed provisional selection. A2 rejection →
explicit reopen → playback → select preserves its history and selection r2.
Missing B3/B4 route warnings and return-to-review links were visible before
selection; they disappeared only when actual current segments were selected.

The standalone reader played C1–C5 in order, paused at the final frame, and
showed `林遥要如何回应这条消息？`, with `去咖啡馆赴约` / `今晚先回家`.
The café choice advanced automatically through A1–A3 and held its ending at
3/3; the home choice advanced through B1–B4 and held at 4/4. Each final player
reported `ended=true`, `paused=true`, `time=duration=2.5`, `readyState=4`,
`error=null`. Restart reset the opening to frame0, paused, with no choice history.
Return to the creator workbench preserved media selections. Authored route
durations are **20 seconds / 22.5 seconds**, excluding the user's choice pause;
these are not a claim of 30-second production pacing or personal audio audition.

Local exact screenshots/media are under
`.local/unattended-2026-10-02/stage4-live/`. `runtime-choice-proof.jpg` is a
494×188 crop of the actual choice controls, SHA-256
`4438e27ea5c17133dff7dc114c63ba3077a3410ce8a3d9cd0dbb26dc7febab7f`.
`home-route-end-proof.jpg` preserves the first complete reader ending screenshot;
`final-home-route-proof.jpg` and `final-cafe-route-proof.jpg` preserve both
endings after the display-label repair and repeated natural route playback.
These are original CUA JPEG bytes, not reconstructed UI. New MP4 mirrors retain
their managed hashes; the original independent bubble experiment is not relabeled
as a canonical job.

## Verification, activation and preservation

- Full backend after the final shared conflict guard: **1,047 passed**;
  one existing Starlette/httpx deprecation warning.
- Full frontend: **413 passed / 54 files**; app and E2E TypeScript checks passed.
  The latest display-history slice additionally passed 29 focused regressions.
- Required API F401 and new/extracted backend/test scoped Ruff passed;
  whitespace check passed. A broad legacy persistence lint probe is not clean
  and was not silently reformatted; no repository-wide Ruff-clean claim is made.
- Deterministic static build passed, with the existing large-chunk advisory.
  Served 8851 JS matches source bytes, SHA-256
  `12db0b2ca0ef7bcd89de429392be414fb0a2fcb06160cc9fc71d2f4e219388e5`.
- Wheel build and installed-wheel smoke passed. Local terminal browser fixtures
  are not represented as executed real-media proof; manual CI status is separate.
- Independent native reviews covered presentation/reopening, immutable image
  instruction changes and the nonspoken-dialogue guard. No demonstrated
  correctness blocker remained at the stable checkpoint.

The owned isolated runtime alone was refreshed at a quiet checkpoint: no active
H3 jobs, specialist `busy=false`, `activeTasks=[]`. Candidate backend PID78264
serves 8851/8852; health is OK and all12 selections remain current. The isolated
process retains its explicit catalogv7 override. Normal 8841/8842, global
settings, credentials, original project and historical receipts were untouched.
The rebuilt static bytes are also visible on normal8841 through its pre-existing
read-only checkout mount. Its cached Python process was not refreshed: a
read-only probe of the new presentation endpoint returns404 there. This is a
known normal-installation activation mismatch, not hidden backward compatibility
or a verified normal deployment. The usable walkthrough target is8851. Original
activation needs a deliberate additive schema upgrade (73→74 tables), outside
the unchanged-original boundary; the owner has been asked separately whether
to authorize it. No such upgrade/restart is inferred from provisional-copy
selection permission.

Original preflight and final captures compare byte-identically: **73 table
facts, 67 file hashes and seven API projections**. Evidence:
`evidence/manager-e2e-first-preflight-original.json` and
`evidence/manager-e2e-first-final-original.json` under the same local run root.
The copy alone admitted the additive presentation table (74 tables). No unknown
dispatch was re-sent, no protected original/segment was deleted, and no blanket
currentness/hash update or lease-release shortcut was used.

Release revision, final UI recheck, remote CI result and heartbeat closure are
recorded below when complete. New sound/final-film acceptance remains pending
the owner even when this E2E implementation is complete.
