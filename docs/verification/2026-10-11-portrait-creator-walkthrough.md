# Portrait creator walkthrough ledger

Authority and boundaries: [run profile](../roadmap/2026-10-11-portrait-creator-walkthrough.md).
Status: IN PROGRESS. Portrait reference images reviewed; no shot-media or playback acceptance yet.

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
  was temporarily blocked by the unresolved lamp image publication, diagnosed
  by the visible preparation diagnostic, not bypassed.

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
checkbox copy differs from Creator's “此节点需要拍摄”. Shot preview cropping and
actual H3 geometry/timing remain hypotheses until real shot media exercises them.

## Coverage focus

E01–E04/E07–E17: new real creation, frozen portrait inputs and both routes.
E18–E20: targeted format/currentness, navigation/reopen and task-state checks.
E22: separate visual/copy pass, especially full portrait reference visibility,
H3 aspect consent and action-ready guidance. Other playbook combinations remain
NOT EXERCISED until separately evidenced; previous results are not new PASS.
