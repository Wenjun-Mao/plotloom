# Project availability and retained media — repair qualification

Status at 20:36 UTC: candidate203 qualified locally and in isolated native replay,
published as executable `628411858734a8496314cb9644d2384b61b82453` and activated
healthy on normal8841. Full Create → Revise → Recover remains PARTIAL.
This closes the two demonstrated read/presentation defects in the
[native recovery receipt](2026-10-08-native-media-lifecycle-recovery.md), not the
outstanding installed-story rebuild or same-node multishot journey.

## Root causes and durable repairs

1. A route's failed initial project load lost structured availability and rendered
   a fabricated empty project. The aggregate loader now owns typed availability;
   an unavailable destination gets truthful recovery guidance. A failed matching
   refresh retains accepted content and local drafts but withdraws write admission.
   Retry is an exact-route read, not job continuation or an implicit reset.
   [ADR0136](../adr/0136-project-load-availability.md) owns this contract.
2. Lifecycle/currentness was incorrectly used as immutable media integrity.
   Archive therefore made valid retained clips look stale or too short, and
   unnecessarily denied verified preview. Frozen snapshot ownership, request and
   window hashes, derivative identity and bytes now independently govern evidence
   reads; lifecycle/input reasons separately govern production. Archive still
   refuses preparation, review, selection and story playback. Malformed evidence
   fails closed; historical requests are not replayed or adapted.
   [ADR0137](../adr/0137-retained-video-evidence-admission.md) owns this separation.
3. A ready archived media read could reactivate durable draft autosave. RED tests
   reproduced visual-intent/image-direction writes and retained offscreen writers
   resuming after failed deletion. Project-owned lifecycle write admission now
   guards autosave, flush/discard, retained review/media writers and drain results.
   Archive/restore ACKs publish admission before session guards; local buffers
   remain intact and only admitted current reads resume writing.
4. Actual archive pixels exposed a misleading “用于故事 · 待审核” navigation label
   despite disabled review. Candidate203 now says “用于故事 · 已停用”, with a RED
   regression followed by the full green frontend/browser gates.

The retired frontend media barrel and obsolete incomplete historic H3 execution
test were removed, rather than adding compatibility behavior.

## Stable candidate qualification

- Full Python: **1,309 PASS**, one existing warning,430.66s on candidate201.
  Backend and Python tests did not change in202/203; this is reused qualification,
  not a claimed203 Python rerun.
- Final203 frontend: **806 PASS** across102 files,3.90s. Application/E2E types,
  lock, API F401, compile and diff checks passed.
- Final unfiltered203 browser gate: **239 PASS**,7.0m, four workers, zero local
  retries. Artifacts: `output/playwright/full-lifecycle-2026-10-07/203-retained-full-gate/`.
-847 executable/test/config inputs stayed unchanged through the final gate and
  deterministic paired default build:
  `8f6aa2ce121b5a596e13e957b8cf610fce486143d4dba5db9873660dbf111a39`.
- Seven static members have identical isolated/default-build inventory hash
  `4a028629a93716e9cc29989a6cfdaa3652bae8a3c35f54ac6f33fb88b96302cc`.
  JS `3a8843193da3df6852f8b12731e33c90961dbe1339a9882b30fb2e03290555d5`;
  workbench2 CSS `a9d4952ea7d019fc6585de093c0f1278034e52328a3a4a7bd7d8b7c1f499dc59`.
- Final paired wheel was rebuilt after the checked default frontend build:
  `/private/tmp/plotloom-retained-wheel-203.Qxeql7/plotloom-0.1.0-py3-none-any.whl`,
  SHA256 `b5bb20ade39c923e038b46262c826d0e2484318864a8ba704742d7919a3edbed`.
  Fresh installed-wheel smoke passed outside the checkout (`203-paired-wheel-smoke.txt`);
  the earlier pre-default wheel is not used as paired static-packaging proof.
- Independent read-only source/lifecycle ownership review closed with no concrete
  blocker. Final203 archive/held-refresh pixels independently reviewed and closed;
  pixel review does not establish interaction, playback or artistic/audio quality.

## Native acceptance on the disposable media-bearing project

Exact target: `b3a933f7-b6fc-40e3-826f-5162f95a119a`, isolated8861/8862.
Evidence names below are in `output/playwright/full-lifecycle-2026-10-07/`.
No generation, canonical edits or media selection changes occurred.

| Check | Current observed evidence |
|---|---|
| Closed destination / failed matching refresh | Native198/199 closed-link and injected503 checks at all three desktop sizes; truthful unavailable state and preserved matching drafts with writes withdrawn. These executable paths are unchanged in203 |
| Archive with delayed reads, no reload | `203c-native-archive-held-no-reload.txt`: one exact archive POST,200 ACK/r10; held video-jobs and visual-workbench reads withdraw old playback/selection authority; no navigation and no false missing-footage message; after release retained read guidance and all production actions disabled |
| Archived preview | `203-archived-retained-playback.txt`: trusted native Space/playing/ended on the exact West derivative,5s/120 additional frames,0 drops/no error; local preview selection enabled, preparation/confirm/reject disabled; zero writes and jobs unchanged |
| Desktop pixels and short-height scroll | `203-archived-guidance-top-{1280x768,1280x460,1700x900}.png`, `203-archived-short-bottom-actions.png`, `203c-native-archive-held.png`; guidance below toolbar, no horizontal overflow, truthful disabled navigation and reachable bottom controls. Root and independent reviewer inspected these exact final pixels |
| Restore, no reload | `203d-native-restore-no-reload.txt`: one exact restore POST,200 ACK/r11, both current reads fetched, no navigation; current explicit selection and production controls return only after qualification |
| Byte/content preservation | `203-active-final-readback.json` vs `203-active-start-readback.json`: six API views unchanged excluding only named project lifecycle/update fields; all15 asset paths/sizes/hashes identical. Final QA state is active/r11 |
| Both current story routes after restore | `203-current-native-routes.txt`: opening→route-only choice→East and opening→choice→West; trusted events, each terminal5s/120 frames,0 drops/no error; zero writes and jobs unchanged. Choice pixels at1280×768,1280×460,1700×900 have no horizontal overflow |

Owner/protected-file checks before and after the owned idle stop still match
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
17/67 managed files and three protected files unchanged. Normal8841 prebuild
reported `busy:false`,zero active tasks before the graceful stop. No busy shutdown,
lease clearing, duplicate dispatch or unknown-job retry occurred.

## Publication and activation readback

Main was clean and exactly synchronized with origin at executable6284118.
The owned composition was rebuilt/recreated after the idle preflight; Docker
reported Healthy and native Codex bridge available. `/healthz` returns200/ok;
the actual served `/v2/workbench.js` SHA256 is the checked `3a8843…555d5` above.
Post-activation owner/protected-file aggregate remains exact in
`203-owner-protection-after-activation.json`. Activation log:
`203-normal-activation.txt`. No owner migration, reset, credential change or
generation occurred.

Fresh unfiltered [CI37840593084](https://github.com/Wenjun-Mao/plotloom/actions/runs/37840593084)
binds executable6284118 and is **in progress**, not yet a passed remote gate.
The final publication note is a documentation-only commit, not a different runtime
qualification. This finite repair checkpoint does not complete the active full run.

## Method failures, reassessment and deployment isolation incident

- Candidate200 retained an obsolete incomplete H3 request assertion and old raw
  alert assertions:1 Python/2 browser failures were diagnosed and preserved,
  then corrected with current-contract tests, not relabeled PASS.
- The first202 native hold helper unregistered a route before its blocked handler
  completed (`Route already handled`). The helper now releases, awaits each held
  handler, then unregisters. Cleanup was observational; the successful archive
  ACK was not repeated blindly.
- The first203 archive helper timed out after its successful r8 ACK because a
  fresh-page directory hid archived rows. Readback established archive; an exact
  restore r9 and explicit “显示归档项目” precondition preceded clean203c archive r10.
  Failed evidence remains; this was a harness precondition, not a product defect.
- A read-only result parser initially included the CLI's trailing code block;
  it was corrected to parse only the result section. No product action was repeated.
- At19:46–19:48 a201 build used `PLOTLOOM_STATIC_DIR` expecting Vite isolation.
  That variable configures the backend, not Vite output, so normal8841 briefly
  served the unqualified frontend. Exact published HEAD static files were restored
  immediately; empty diff, published JS hash and protection checks proved restoration.
  This exposure is not erased by the later restore. The reusable playbook now
  requires explicit `npm run build -- --outDir <isolated-directory>` for isolation.
  Normal was gracefully stopped before the qualified203 default build to avoid
  mixing newer frontend fields with cached older Python.

## Remaining full-run scope

[ADR0138](../adr/0138-one-current-story-explicit-rebuild.md) records the owner's
choice of one current story with explicit rebuild. It is not yet implemented or
native-qualified. Same-project installed production revision, new review/current
media through every revised route, within-node native multishot, remaining source
reference-consumption and unobserved visual/text state permutations remain open.
Decoder functional success is not a diagnosis of the earlier system crash;
image/video creative quality and audio judgment remain separate owner/H3 review.
