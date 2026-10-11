# Role walkthrough continuation and state-based guidance

Qualified candidate: the main commit containing this receipt, against trusted
`6371bf6291f9b708200730b7866df2c3b76fe1ac`. Contract: ADR 0155.

## Actual journey and boundary

The owner authorized continuing the `留一盏灯` walkthrough and repairing
demonstrated UX problems, pausing at creative sign-off or a new provider/cost
decision. After the Art/preparation correction, selecting the brief's
`真人写实` style and preparing Art was rejected with `accepted_cast_not_current`;
no Art job was created. The Role page similarly gave generic review advice
despite missing Role content and an unselected required style.

Selected the same brief-backed Role style, prepared one frozen Role task, and
sent it once using the existing configured assistant. The native delivery check
returned a ready proposal for 许宁. It remains **unconfirmed**. No creative
acceptance, image/video generation, service restart or new provider decision
occurred. The next author action is review, then `确认使用此角色设定` if accepted.
Art and Script remain later prerequisites; the walkthrough is not complete.
Read-only inspection of the proposal's performance notes also exposed an author
decision: the frozen choice section is marked `footage`, while its summary and
seed topology still describe `route_only`. This reflects the checked filming
setting versus retained story wording. The proposal records the discrepancy
without adding a scene or resolving it. Do not silently change the author's
graph or approve production; ask whether the choice needs its own scene.

## Cause and durable fix

Extend the existing active Art/Script advisory observation with the Role panel's
owned state, style, operation error, dirty/retained draft and design validity.
Name actual controls for preparation, delivery checking, review, reopened edits,
failed reads and current confirmed continuation. Text approval stays separate
from appearance-image generation and selection; retained evidence is not a
current approval. The guide adds no API reader or mutation authority.

Independent review identified one supported refresh gap: same-project
`刷新服务器版本` preserves the Role page, but its existing parent read only depended
on project ID. A new guide revision could therefore reuse old Role authority.
The same parent owner now revalidates on workspace refresh identity, reports
pending/failed reads before retained content, and rejects obsolete completions.
Continuation, editing and gallery actions wait for this verified read.
Same-project unsaved edits remain retained across refresh/failure/retry.

Actual diff/dependency review covers advisory projections/context, the existing
Role read owner and its controls, test registration, docs and regenerated JS.
Existing API contracts, mutation request payloads, persistence, admission, auth,
provider/prompt behavior, dependencies, build tooling and package contracts are
unchanged. This is bounded frontend read-currentness/presentation work consuming
unchanged APIs, not a backend or generation-contract change. Use the existing
risk-scoped local frontend qualification; no full Python rerun warranted.

## Executed qualification

- Initial focused Role selection: **61 unit cases in four files** and **3 native
  browser cases** (Role lifecycle/retry plus cast-render-choice), 11.142s, passed.
- After refresh correction: **23 units** in cast-workflow-observation,
  recommended-cast-workflow and character-reference-gallery, plus all **3 Role
  browser cases**, passed in 15.767s. The real CharactersPage test holds two
  refresh reads, rejects the obsolete response, checks failed-read controls and
  retry, and preserves an unsaved appearance edit. The browser regression uses
  the real workspace refresh control and failed/recovered transport.
- Final `verify.py quick`: **1,201 tests / 145 files**, both type checks, locked
  dependencies and API F401 lint passed in 17.011s. An earlier quick run caught
  an invalid diagnostic code in a test fixture; replaced it with the actual
  typed `source_context_not_ready` before successful qualification.
- Shared affected browsers: recommended-art-workflow (2),
  recommended-script-workflow (2), recommended-workflow-guide (3): **7 passed**,
  27.850s. These prove the extended observer preserves the prior consumers and
  guide/navigation protection. Fixture creative confirmation is limited to
  disposable native projects; it does not accept the real proposal.
- Inspected Role captures at 1280x460 and 1700x900 from the focused Role journey;
  required style/preparation controls and sticky advice fit. The 1280x768 capture
  was also produced. Read-ownership changes do not change this layout. Real
  Safari was reloaded onto the regenerated assets for the final handoff.
- Unfiltered manifest check: **88 specs / 292 cases**, shards 124/168,
  zero omissions/overlap; no release coverage removed or filtered.
- Two deterministic seven-file builds matched sorted path/hash tree SHA-256
  `40e380e4edbd0bdb75f679adb745ffbf893db7762b015ab9f634c4ab69eaf898`;
  JS `a40b50a369c708cf8bb931f239222e92f2aa9ee2b926bf9e12b74f572e9a9d9d`.
  Existing large-chunk warning remains. `git diff --check` passed.
- Independent GPT-6.1 Sol / Medium review found the refresh P2, then reviewed
  its concrete closure with **no actionable findings** and independently ran
  the **23 focused units**. Effective host settings were not independently
  exposed. Reviewer did not independently run browsers or broader gates.

No unfiltered Python/browser full gate launched. Hosted CI is separate and
pending for this candidate until actually observed; modular-verification branch
evidence does not qualify these later UI changes. Local software verification
is not full-release or owner creative acceptance.
