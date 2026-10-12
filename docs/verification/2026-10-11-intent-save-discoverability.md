# Intent package save discoverability

Status: implemented, independently reviewed and risk-scoped locally qualified.
Owner acceptance and hosted qualification remain separate; no CI dispatched.
Trusted clean starting revision: `9034a58d`.

## Cause and bounded decision

In the owner's 29-entry walkthrough the only ordinary「保存戏剧意图整包」button
was after the entire list, making the workflow guide's named next action hard
to find. This is a presentation/discoverability issue in ProductionBridgePanel,
not a missing intent, generator, API or save operation. See the
[approved scope](../roadmap/2026-10-11-intent-save-discoverability.md) and
[ADR 0140](../adr/0140-native-bridge-intent-candidates.md).

Replace that button with one highlighted sticky-bottom bar inside the open
intent review section. Keep its logical keyboard order after the fields and
keep it visually reachable while reviewing the beginning/middle/end. The bar
names the whole package, shows its item count and intent-only state, and says
that saving neither confirms production nor generates media. It does not
count reading as review progress or use presentationDirty as intent status.

The existing disabled expression, accepted-state hiding, admitted run handler,
proposal revision/content hash and complete `{id,text}` payload remain intact.
No backend/API schema or request-payload, persistence, admission/auth,
provider/prompt, dependency, build-tool or package-contract changes exist in
the reviewed diff. This is bounded frontend qualification, not the full local
Python/release gate. No valued content was edited or saved, no provider/native
job was dispatched, and no service was restarted.

## Executed verification

- Focused Vitest: native-bridge-intent, production-bridge-panel and
  production-bridge-basis: 69 tests passed in 1.094 seconds runner time.
- Final `verify.py quick`: 150 frontend files / 1,275 tests, lock check,
  API unused imports and both TypeScript checks passed in 12.983 seconds.
- Focused browser presentation/rebuild specs: 3 cases passed in 17.8 seconds
  (runner 19.921). After tightening field-clearance assertions and the reviewed
  status-copy edge cases, presentation was repeated: 2/2 passed in 15.9 seconds
  (runner 21.322). Unchanged rebuild evidence is retained, not relabelled as a
  second run. No full suite or hosted workflow was run.
- The actual contract-valid disposable bridge has 33 intent entries. Browser
  assertions verify a single save button visible at the first, middle and last
  entry at 1280×460, 1280×768 and 1700×900, without horizontal overflow. The
  selected field fits below the sticky guide and above the bar. The complete
  ordered save payload, post-save status/disabled state and separate production
  acceptance path pass; stale rebuild/completeness/currentness guards remain.
- Root inspected all nine start/middle/end desktop captures. The bar is compact,
  readable and confined to intent review; existing report/presentation controls
  are not duplicated into a global toolbar.
- Two final serialized deterministic builds matched all seven static-file
  SHA-256 manifests. Generated assets are included. The existing non-blocking
  Vite large-chunk warning remains.
- Attended GPT-6 Luna / Max independent review found no blocking defect. Its two
  copy nits were resolved: clearing a saved entry now reports both unsaved
  edits and missing items; restricted saving names permissions and proposal
  state. The reviewer read the changes back and found no remaining issue.
- `git diff --check` passed. Existing owned tests/specs were extended; test
  ownership and browser shard assignments are unchanged.

## Live check and handoff

Root opened a separate read-only browser tab for「给今天的自己」project
`160554c7-f021-40b0-b218-b9d53412b75c`, focused the first existing textarea
without typing, and inspected the 29-entry save bar with
「建议待审阅并保存」and its whole-package boundary. No save or confirmation was
clicked. The ignored capture is
`output/playwright/intent-package-save-bar-20261011.jpg`; fixture captures live
under the existing ignored `frontend/test-results` directory.

The final HTTPS-served `workbench.js` matched local assets at SHA-256
`2f101597ec942a458722bcd3987aa9aea00d6e057a74252f99bcd6ad2ec12e53`.
Existing browser tabs need a reload for the new UI; the owner must preserve
any unsaved edits before reloading. This is software/presentation evidence,
not creative review, production confirmation or media acceptance.
