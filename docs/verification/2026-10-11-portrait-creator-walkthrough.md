# Portrait creator walkthrough ledger

Authority and boundaries: [run profile](../roadmap/2026-10-11-portrait-creator-walkthrough.md).
Status: COMPLETE for the bounded product walkthrough. Nine portrait keyframes
and nine 2.5-second cuts are explicitly selected; both interactive endings,
restart and retained playback after page reload were exercised. This is not
final-film acceptance: the leave-ending turn remains a recorded creative defect,
and human listening/mixing and full visual continuity QA are not claimed.

## Starting evidence

- Clean main `0c5a5bd5d219f0c5d0ff6f49b6db807f2371d991`.
- Normal 8841 completed landscape project remains
  `a46790f2-981d-4454-a9f4-8679d70e65e5`. No settings/media were changed.
- Existing browser opened at a narrow 628px viewport. Two semantic Home clicks
  failed; switching to the documented desktop editing viewport 1440×900 made
  the same control work. This is not evidence of a supported desktop defect;
  mobile/narrow editor support is excluded by the current contract.
- Used visible Home → Create blank project. Entered comparable lamp synopsis,
  zh-CN, urban drama, live-action warm/low-saturation style, 9:16, 30-second
  complete-route ceiling, one choice/two endings, six-node budget/two options,
  no joins and advisory 1–4 cuts per scene. Save acknowledged project
  `63e4851b-3af2-40cd-839c-501470c691de`, root
  `.local/creator-walkthrough/outputs/20261011T200746992619Z__63e4851b-3af2-40cd-839c-501470c691de`.
- Landscape preservation baseline: project.json SHA-256
  `a676fc1b3128d8776a5268f2a961bcd6d21a00958ab10fa9b7598c80dc141c25`;
  SQLite file `d94f8e331ad8550f5d8ff658b2b2d7706d878155edc75bcc195f41e47eedd9b4`.
  Read-only immutable logical dump hash
  `917ac0608ef37c6389b71dd70549411d147e26c5aaf3f3611efd3b206ff65411`
  is supplementary evidence and does not include an uncheckpointed WAL.

## Source and recovery

- Source r1 confirmed through the visible UI. Unsent outline `ch_c26cdbb3…`
  cancelled before dispatch; source remained r1 and preparation became available.
- Outline `ch_0ffc7e2762ff4e5e9529c9cfc4bb0a02` dispatched once at clean
  source `58cf351e5ef2eaf7085ad2ecfd7922ffc838ede4`. Frozen request carries
  9:16 and topology hash
  `70c8b1c62ecd71542fe43d01d118c32bd44800885ee899caa57650e0cf81fe09`:
  four nodes, one route-only decision, two endings, no joins.
- Navigated away and returned during execution; the same task remained visible
  without resend. Native specialist completed in 130.478 seconds. Automatic
  check admitted the candidate; an attempted manual check raced with removal
  of that control and made no second dispatch.
- Read the complete candidate in the native isolated reader, then confirmed
  outline r1. Proposed durations 10/7.5/5 seconds remain creative suggestions,
  not exact generated/cut timing. No portrait media has been created yet.

## E22 finding: premature empty production hints

Opening Role during outline execution invited style selection and task
preparation. After one preparation click, the unchanged server safely rejected
missing source/outline/branches/applied-route prerequisites; no Cast candidate
was created. Script and Art also offered preparation before those prerequisites.
Evidence: `output/playwright/portrait-walkthrough/role-before-outline-rejection.png`
and `script-before-outline-hint.png` (local ignored captures).

Root cause: the shared recommendation model already receives the active source
snapshot and stage heads, but production guidance delegated immediately to an
empty local stage. Those observations describe candidate state, not upstream
admission. Fix only the empty-stage preparation invitation using existing
source/outline/map/applied-head identity checks. Busy/error/dirty/retained and
delivered work retain their owner's guidance. This is advisory presentation,
not a new preparation gate or duplicate read owner.

Scope against `58cf351e`: no backend/API schema, request payload, persistence,
admission, authentication, provider/prompt, dependency, build-tool or package
change. Risk-scoped local frontend qualification applies. First focused run:
79 unit cases passed; browser regression exposed a test mutation/acknowledgment
race (navigation immediately after source save). The test now waits for visible
source-r1 acknowledgment before navigation. Typecheck also caught a readonly
test-fixture array, repaired without weakening the production contract.

Qualification: quick passed (149 files / 1,254 Vitest cases, lock/lint and both
TypeScript checks). Five explicit guide specs passed 13 browser cases. The
final guide-spec rerun includes causal source-read failure recovery: 503 remains
active through Source activation, then page-level Refresh alone recovers it.
Independent GPT-6 Luna / Max review found the top-bar recovery seam and a test
causality gap; both were corrected and rechecked, with no remaining finding.
Two serialized deterministic static builds produced identical seven-file
SHA-256 manifests; workbench.js is
`473fd1aa376176df9c8e7111da129a7591bba81c800edbfb2bb43c89f435a83f`.
Supported-desktop guide captures inspected at 1280×768, 1280×460 and 1700×900;
no layout rules changed. Normal 8841 readback after reload correctly identified
the portrait project's missing branches, without a rejected preparation click.
Published main `9455e71c7dec04e0349088e14c349b8d4ea7d929` includes the advisory fix.
Hosted qualification of this advisory change is separate and pending.
The main task-card controls remain server-gated; this change improves the shared
guide, not every empty card's explanatory copy.

## Reviewed creative inputs and portrait references

All following native jobs froze clean `9455e71c`; source/package/canonical data
were not edited by specialists. Candidates were read and accepted through UI.

- Branches `ch_d2487f42a59e4d958021231de85d2a2d`: reviewed four nodes, the
  question, both option targets and constraints, imported to draft, confirmed
  r1, then separately applied. Choice remains route-only, without extra film.
- Cast `ch_8f112e9b157a42e7b515437e96078925`, Art
  `ch_665c8821d74c44dcb7db6caa35c419db`: complete JSON/report reviewed and
  confirmed r1. Inferred appearance and lamp geometry are identified as design
  proposals, not source facts. Art negative wording was made specific to
  displayed wall pictures before validation, not a relaxation of realism.
- Script `ch_ce3e268b1ff24650952e4554d2aa1445`: confirmed r1 after full
  candidate review. Three footage episodes, five scenes, nine actions; no dummy
  choice episode. Planned shared/take/leave durations 10/7.5/5 seconds produce
  17.5/15-second routes, under the 30-second ceiling. Technical `lang=en` is the
  explicit frozen renderer contract, not a change to Chinese story content.
- Storyboard `ch_c5f8bf4d2d7f483ca308e8205cfac317`: reviewed UI's readable
  cut list and full JSON, then confirmed r1. Nine 2.5-second static shots,
  native portrait staging; the intentional face close-up is not widened into a
  full-body image. Production proposal/mapping still pending. Its preparation
  was blocked while the lamp image publication was unresolved. After that
  publication completed, the mounted preparation observation remained stale;
  see the re-entry finding below. The server gate was not bypassed.

Actual ImageGen receipts and explicit UI selections:

| Subject | Native job | Delivered SHA-256 |
| --- | --- | --- |
| C01 identity | `ij_0f3546b1f31d4c58a5d8fb35c33bbd5f` | `6bcff55bc847e0420c02082091102d0d4b332f9edf51698079378cf17eb55442` |
| S01 room | `ij_e3fdd6cffa5a40abb5668bdb317b675e` | `f89985395c60308860cfef2eb140c01bd1194b4e8e940bba9d33076e79bc12ab` |
| P01 lamp | `ij_bf1421588a484d6ebbe1ea77c05d6311` | `8c4e771aa3e32e16fd59ec8c76fb3834b1fb9ebde6a9c671df670f591d6589a1` |

All three originals are 941×1672, nominal portrait but not exactly 9:16 by
integer cross-product. Viewed in full-image dialogs: character head/hands/shoes,
room action space, and complete unlit lamp fit without UI cropping. Captures:
`portrait-character-viewer.png`, `portrait-room-viewer.png`,
`portrait-lamp-viewer.png` under `output/playwright/portrait-walkthrough/`.
Character selection explicitly recorded r1. Art UI explicitly states room/prop
selection is reference-review only and is not passed to shot production; that
selection must not be reported as actual shot reference alignment.

The lamp worker corrected two conspicuous chips to one shallow base scuff before
publishing. All image receipts passed hash/provenance checks; candidates were
not automatically selected. Art delivery required explicit Check delivery;
navigation preserved the active job without duplicate dispatch.

Cleanup is NOT complete: the staging helper refused because the generated-images
directory is not private. Delivered project-local images and staging originals
remain intact. Preserved worker staging files: `exec-a8fad3bc-2350-408c-8f3f-102c5bfdd0aa.png`,
`exec-0279b002-9d6a-4ba7-9d96-7c2c02ed986e.png`,
`exec-3e405616-8052-4197-b09d-7dc5c7388569.png` (lamp initial draft), and
`exec-c2b078fe-2be8-4cd6-a1ce-786e77293fee.png` under the image specialist's
`/Users/wjmao/.codex/generated_images/01a0c506-84d5-7161-8ae0-2ae914e5d81a/`.
No permissions were weakened and no manual deletion was attempted.

Deferred observations, not completed fixes: Script candidate disclosure still
requires raw JSON reading (Storyboard has a readable cut list); Source's route
checkbox copy differs from Creator's “此节点需要拍摄”. The subsequent real-media
findings below replace the earlier shot-preview/H3 hypotheses with observations.

## E19 finding: unchanged review did not refresh external-work admission

After the accepted storyboard and lamp delivery/selection, navigating Art →
Storyboard kept “unresolved publication or execution prevents production
rebuild” and disabled Prepare. Read-only project inspection showed all three
image proposals delivered, creative candidates accepted/ready/cancelled, and
no image/video/intent job left active. Browser reload alone read the available
gate. This establishes stale presentation, not a stuck provider or server gate.

Root cause: Storyboard's activation read revalidated on entry, but the mounted
bridge read keyed only project/storyboard revision/hash/status. External-work
quiescence can change without changing that basis. The bridge now consumes the
owning acknowledged Storyboard read as a refresh token. It rechecks unchanged
bases on entry and server refresh, retaining intent text, conflict detection,
request sequencing and independent pending-operation occupancy. Token changes
during same-owner mutations are coalesced until settlement, preventing an older
pre-write read from replacing a successful save. Independent review identified
that race in the first candidate and confirmed the deferred-token repair and
regression test close it; no further actionable issue was found. No remount,
automatic write, polling workaround or admission bypass was added.

Scope against `d0c2b78`: unchanged APIs/payloads/backend schema, persistence,
server admission, auth, provider/prompts, dependencies and package/build tools.
Frontend qualification: focused 59 unit cases and eight bridge-refresh,
shot-handoff and recommended-guide browser cases passed in 28.244 seconds;
quick passed 149 files / 1,256 Vitest cases and both type checks in 12.217 seconds.
Two serialized deterministic builds matched all seven asset hashes;
workbench.js `aba440125243aeff98584169292314c545984e58f340853cfde4673f76a3b107`.
Desktop captures inspected at 1280×460, 1280×768 and 1700×900; button and guide
remain readable and actionable. Unfiltered browser shard reconciliation passed:
89 specs / 296 cases across four shards (84/70/71/71), no gaps or overlap. The
added case is in an already-owned file; no ownership or shard assignment change
was required. Independent review is complete. No new full/hosted gate is claimed.

## Coverage focus

E01–E04/E07–E17: new real creation, frozen portrait inputs and both routes.
E18–E20: targeted format/currentness, navigation/reopen and task-state checks.
E22: separate visual/copy pass, especially full portrait reference visibility,
H3 aspect consent and action-ready guidance. Other playbook combinations remain
NOT EXERCISED until separately evidenced; previous results are not new PASS.

## Portrait production installation and first media boundary

At clean `7141a1ce`, native intent task `ch_29f004e6ff2c4626b9a3d2e17550176e`
returned 14 suggestions. Reviewed the complete report and 18 action/composition
strings, saved the whole production proposal, confirmed r4 and separately
installed its five scenes/nine shots. Storyboard v1 (`817fd4d3…`) was approved
through UI. C01's production identity decision is r2
`47ad6343-8172-43a4-a050-b7e7dee84d4e`; this is distinct from image selection r1.

All four opening ImageGen jobs froze `7141a1ce`. Their 941×1672 originals were
inspected at full size, then visual intent/provenance saved and explicit
keyframe selection plus same-person review acknowledged. These are bounded
fictional-character visual judgments, not biometric identity verification.

| Shot | Job | Delivered SHA-256 |
| --- | --- | --- |
| Opening approach | `ij_8bef23577a8546ecac349adfb246d1e7` | `084589c40aaac71df4e3be4c62fe7ac7ad9f9726c7c7e1c550f041e97e4fd7bf` |
| Hand before switching on | `ij_a6a66e2acc874b6d8c5ff5822f2aa73c` | `e8e1bdb49652c50b1f7c5e0ad3d109f562f070b17692077c0181c264f777841a` |
| Intentional face close-up | `ij_41593969985d42829160b72359f6e88f` | `40d4b9a49f79223279344decce6b0c532e34c91400f363cfb2cd00906ea4b0f0` |
| Pause beside lit lamp | `ij_ce0b6439b8344346b7be32e4bc195068` | `f7de2ca1cdd1699198339b51927709557f2a036aff430c747701b215e0c246b2` |

Identity reviews: `89a47e41…`, `ab800dac…`, `4f7a92ac…`, `513364f8…`.
Complete head/hands/lamp were inspected where composition requires them; the
face close-up intentionally excludes the hands and most of the lamp. Known
visual limitations: window panes/frame color vary across opening shots and
some lamp highlights remain glossier than the matte design. Art selections are
not actual shot reference inputs; these are not claims of final continuity QA.
Specialists retained first drafts and delivered originals after safe staging
cleanup refused; no permissions or evidence were removed.

H3 profile: explicit quality8 576×1024 portrait v2, full-image contain/pad consent,
5-second request yielding 124 frames at 24fps (5.167s), no end frame. The authored
cut remains 60 frames/2.5s, not the original's duration.

First original `vj_08430e4378f24cc1a0601fca94d55b86` decoded in the real browser
and was inspected at 0/2.5/5.167s. It reached toward and then lifted the lamp,
violating the opening's action boundary; trimming did not repair its first cut.
Rejected through the explicit UI confirmation; original and cut evidence remain.
Local ffprobe independently read 576×1024 H.264 High/yuv420p, AAC-LC 32kHz stereo,
124 frames and 5.167s. Capture: `portrait-first-original-boundary-rejected.png`.

One tighter retry `vj_07b35d30e1d4451c9ce7c5b75aa98002` used seed
`4821541421190110`, prompt hash
`b65f26298a9a1d1ba35ee48729185ccc6297ec193f40f49274ba0d0e2b299e63`.
Its later footage still reaches, so the whole original is not creatively passed.
The first 0–60 frame cut approaches the unlit stationary lamp without touching
or lifting, preserves head/shoes and actually plays through `ended=2.5` without
decode error. Explicitly selected that cut. Audio stream/native unmuted state
is observed; no human listening or final-mix acceptance is claimed.

## E22 finding: shot media lacked full-image review

Actual portrait candidate geometry was only 260.5×96 with `contain`; identity
comparison images were similarly constrained, with no full-image dialog.
Character/Art already support complete-image review. Downloading originals
proved full framing, but is a poor product path for assessing hands, margins,
and same-person reference details. Capture: `shot-candidates-small-review.png`.

Root cause is missing use of the shared presentation primitive in the shot
candidate and frozen-reference panels, not asset cropping or generation geometry.
The bounded fix reuses `ManagedAssetImage` and `AssetZoomDialog`, exposes a
separate “查看完整图片” button beside candidate selection, and image-triggered
viewing for candidate/frozen-reference comparisons. Native Esc/close/backdrop,
focus return, body scroll locking and HTTP/decode fallbacks remain shared.
Modal ownership resets on project, shot/binding, asset and byte-identity changes,
so stale evidence cannot reopen when returning to an old selection.

Scope against `7141a1ce`: local read-only presentation only. No selection,
approval, backend/API schemas or payloads, persistence, admission, authentication,
provider/prompts, dependencies, build tooling or package contracts changed.
No job was active during edits/builds. Opening the viewer neither selects nor
approves; tests also observe no non-GET API calls. This routine reuse does not
introduce a new workflow or generation contract.

The first real 1440×900 screenshot caught an additional shared-dialog sizing
defect: fixed image maximum height did not reserve the new title/footer. Image
bottom was 907.7px and explanation bottom 937.8px, beyond the viewport. The
shared shell now reserves its close control and lets the content allocate the
remaining height, shrinking the contained image rather than clipping it.
Regression checks assert all image/title/footer/control bounds at three desktop
sizes. The existing Character/Art image-only consumers use the same contract.

Final focused check passed 26 unit cases and four image-job/reference-layout
browser cases (28.374s). Quick passed 149 files/1,263 cases and both TypeScript
checks (10.960s). Seven missing-media/reference-layout regressions had also
passed (16.249s); the final reference-layout rerun follows the sizing repair.
Two serialized deterministic builds matched all seven asset hashes;
workbench.js `6177684df6b04a824fc26ec905f3b98479d54fd66d40844c18ba2625b53a3d49`,
workbench2.css `ac0655604c3f12116fec6cd7008680def5166c41ea15ea3c3d589f679e18e64a`.
Actual portrait image, title, explanation and close control fit at 1280×460,
1280×768 and 1700×900. Esc restored the exact candidate-view trigger and released
scroll locking; frozen C01 reference also displayed complete head/hands/shoes.
Local captures: `full-shot-image-{size}.png` and `full-frozen-reference.png`.
Seventeen existing Art/Cast browser regressions passed (51.496s), including
their shared full-image dialogs. Independent GPT-6 Luna / Max review found no
remaining issue after inspecting the sizing repair. A proposed dismissal issue
was resolved by distinguishing the black contained-image canvas from the true
backdrop outside the centered content area; clicking the image canvas is not a
dismiss action. The browser regression explicitly checks the true backdrop,
Esc, close, focus return and non-mutation.
The final backdrop/focus/non-mutation image-job journey passed (25.866s).
No new full or hosted release gate is claimed.

## Remaining portrait media and actual endings

The five ending keyframes froze clean `6c8f44a9`; all nine shot image jobs reached
delivered. Inspected complete images, saved visual intent r1, then explicitly
selected and reviewed each candidate. The first four receipts are above.

| Shot | Native image job | Delivered SHA-256 | Identity review |
| --- | --- | --- | --- |
| 5 switch off | `ij_607c360731e24b359c8cef2998d08492` | `bd356a08b129ce5dc5665f61769a7317badcfd374583e55e5a29b91eff632a11` | `fd9ac458…` |
| 6 lift unlit lamp | `ij_e08f02611a5943a28a9d8204d72ef1ba` | `09403634386acb42ab4a8e90fc33edcbe16fcb9da2a7e7214da36f0074087e51` | `0a7c832c…` |
| 7 hold and turn | `ij_ce535401b8ef4a8db9809b266c7bacbf` | `9b3a167286875adba2039f4cf956a3877cc6476a3ae28f25ab40565172b8d2ad` | `87607589…` |
| 8 withdraw hand | `ij_b91e1110eb3843ddb05d33f812865a1c` | `915d85b0a36001ff08d9dedceb106a70f8c30be01c8bd1243aba54376bc7de82` | `7e464c88…` |
| 9 leave empty-handed | `ij_f8bf1ec8b53441c5a7feec509af84dcb` | `ad12d71c0d05fb8ebf893d74d561ec473596c0997bdcbaff1f6bbc5cefa9e796` | `a9985f5d…` |

All nine are 941×1672 nominal-portrait inputs. The explicit H3 quality8 v2
576×1024 treatment uses contain/pad consent, not stretch or silent cropping.
The real originals decode as 124 frames at 24fps / 5.167 seconds; accepted cuts
are independently authored 0–60 frames, revision 1 / 2.5 seconds.

| Shot | Selected original job | Selected cut | Cut SHA-256 |
| --- | --- | --- | --- |
| 1 | `vj_07b35d30e1d4451c9ce7c5b75aa98002` | `112a555a-b0c8-4e84-abf6-bf8621075372` | `2627a849f5c83f7b8643515d9d83a0e777c7570a5fe691e1a75e33a4165e5bba` |
| 2 | `vj_ea1e2dc1e494444dbffc8ab078c1dc59` | `66707cbc-d458-4b18-8b8f-f24287f0083f` | `10fe6d01b56b0bc6466dad535706c57a5b4b3503378d02fa5f6413ee3a4ad0dd` |
| 3 | `vj_5a68e9e5087d455b9f4b5215a7ae95c3` | `e42dd69b-8dfa-4e9b-a0eb-0ad467a4fab0` | `7184e134f96c929b122a5f637eda3ed2dd7694ed3bda64c7d7487f3d5df1072b` |
| 4 | `vj_b7df01ff51a545c787ba368ac235085f` | `b38b4261-78a3-47fb-8cd9-8a4aac61a578` | `2f0211f13f77c397cb7edb022f05dd325db944230a5e1ed0e48d4541f78f797b` |
| 5 | `vj_4d60c592e41a4fc69bc40d7587afc691` | `e17f7ded-3ec8-402c-ba57-a53ae3973b16` | `1cb0737dff1f36421fa0fbd4e652960751fc23a80dc017b0cc2eab2093be7d0c` |
| 6 | `vj_4f45ab7fe8864a5ba52e7ebc9f095093` | `4d40df64-b1bb-424b-8d47-7e535c39a47f` | `566a844e844dec40c8041e821ceed863637ca090b8eaeb324165740e92c71e48` |
| 7 | `vj_07bf34dc80d9473b83269cd5e93164f9` | `61312571-29cd-4d22-9fbd-d8079d8eac02` | `16a9b93646fe543abadd30eaca73e6071dd23a8affbcebcdbcff0cc48cb48a77` |
| 8 | `vj_47962e7490884f09ba8d15445970c675` | `70b974a9-cbf4-4995-b350-abeaf9627762` | `a26480775afe7e6a054c562a623d6ee2aeb3fc2d22a3c63b82c4abb27dd8f2a8` |
| 9 | `vj_a4ee858333e24342bf05790b05786927` | `cf221834-9ea0-499e-994c-ee6f7627a73d` | `1650b79f7f36213132396ab850d609f5820b6c80c7af0c0f86cfa467fe7651fd` |

Twelve originals reached ingested; three were rejected and remain preserved.
In addition to shot 1's original above, shot 4's first
`vj_6b7b7ec487b24dcf8bde9c4aefe16c8b` lifted the lamp before the choice, and
retry `vj_cf442d8c9240445a976b16358ce3c329` switched it off within the cut.
Two equivalent failures triggered reassessment, not another blind retry. Using
the same approved shot image as both start and end frame through native controls
produced a lit, stationary pause in `vj_b7df01ff…`. The changed endpoint input
correctly leaves older frozen jobs mismatched and unselectable; no gate bypass.
One successful endpoint attempt is not a general model reliability guarantee.

Shots 2/5 complete on/off separately; shot 6 lifts the unlit lamp just above the
desk within its selected cut; shot 7 holds and turns; shot 8 withdraws the hand
without moving or extinguishing the lamp. Shot 9 keeps full framing, empty
hands and a lit stationary lamp, but its weak turn is toward the window rather
than convincingly away. Its explicit `Codex walkthrough only` review records
that defect and requires replacement/revision for a final film. Pose-height,
window and lamp-finish continuity limitations are not concealed by execution
success. AAC stereo and native unmuted decode are observed, not listening approval.

Actual player journey at 1440×900: four shared cuts played automatically into
the route-only choice, with both exact options and no dummy choice film. Take
played its three cuts and stopped at the take ending; Restart cleared history
and returned to opening 1/4. Leave played its two cuts and stopped at the leave
ending without continuing into Take. Each final native video reached
`ended`, duration 2.5, 576×1024, without decode error. Route footage totals are
**17.5 seconds Take / 15 seconds Leave**, excluding the viewer's answer time.
They satisfy the 30-second ceiling, not a claim of exactly 30 seconds.
Page reload retained the nine selected cuts and reopened playable opening 1/4.
This is reload evidence, not a new process-restart or format-revision exercise.

At exploratory 390×844 playback, page width remained 390 with no horizontal
overflow; video measured 320×568.883 against native 576×1024. Both choices fit,
vertical scrolling remained available, and Restart → choice → Leave completed.
This is not a mobile editor support claim. Local surrounding-context captures:
`portrait-take-route-ended.png`, `portrait-leave-route-ended.png`,
`portrait-player-390x844.png`, `pause-endpoint-cut-reviewed.png` under
`output/playwright/portrait-walkthrough/`. The existing missing-clip guide first
identified the one remaining shot precisely; after selection it offered the
concrete interactive-play check rather than asking for a nonexistent stage button.

## Finding: compatibility review draft crossed shot boundaries

Actual unsaved `审核兼容性说明` for shot 9's leave action remained visible after
switching to shot 6's unlit-lamp lift. Capture `review-note-wrong-shot.png`.
Durable approvals were not corrupted: each actual selection received a fresh
manually replaced note. Root cause was panel-owned unscoped `useState("")`,
not a server approval or provenance failure.

The extracted keyframe draft owner scopes observations to project, shot/scene,
candidate, approval/storyboard revision and ready intent/asset byte identity.
A changed target renders blank immediately, before effects or a new media read
settle. Unchanged refresh/failure/retry preserves observations while existing
owner gates disable actions. Stored approval notes are never copied into a new
draft. No whole-workbench remount, new mutation or downstream tolerance.
This ownership decision extends [ADR 0103](../adr/0103-retained-candidate-read-reconciliation.md).

Scope against `6c8f44a9`: unchanged API/payload/schema, persistence, admission,
auth, providers/prompts, dependencies, build/package tools and generation.
No job was unresolved during edits. Regression first failed three new cases
(five passed) without the fix, then all 18 retained-candidate/failed-refresh
cases passed. Quick passed 149 files / 1,267 Vitest cases, both TypeScript
checks, lock/lint in 11.271 seconds. Four affected browser specs ran: imported
still, H3 pilot and image jobs passed; one interactive case initially matched
both candidate selection and the separate full-image-view button. Anchoring
that selection locator to its actual label repaired only test ambiguity. Both
interactive cases then passed in 53.023 seconds; all five affected cases passed
across the two runs. No assertion was weakened or Python full suite repeated.

Two serialized builds matched the complete seven-file manifests; final
workbench.js `6bda6c3982f6600d0fe533d0c72cd9c61ecf9cac7d5888a308f735bbeec866f7`,
CSS unchanged `ac0655604c3f12116fec6cd7008680def5166c41ea15ea3c3d589f679e18e64a`.
Independent GPT-6 Luna / Max review found no actionable issue. Normal 8841
readback after static reload at 1440×900 showed a temporary shot-1 note clear
immediately on shot-6 selection, remain blank after read settlement, and keep
approval disabled. The probe was never submitted; existing intent/video and
durable review records remained intact. Capture `compatibility-scope-fixed.png`.

## Final boundary and remaining work

Landscape project.json and SQLite hashes were rechecked and match the starting
baseline. Old landscape and rejected portrait originals remain intact. No paid
fallback, unsafe staging deletion or repeat queued worktree archive occurred.
The Source checkbox wording, Script's raw-JSON candidate reading, deliberate
format-change invalidation and remaining playbook combinations are deferred,
not new PASS results. Full artistic continuity, final leave-turn quality and
human audio review remain separate. Local bounded frontend qualification is
complete; no new full/hosted release qualification is claimed for these fixes.
