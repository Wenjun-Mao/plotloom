# Codex Exec serial proof and F5 timing boundary

Date: 2026-10-14. Scope: local functional execution and the existing canonical
receiving requirement. Parallel performance, full local release qualification,
creative acceptance and publication remain outstanding.

## Retained serial functional proof

The production-supervisor run at `596c221313a87b3afb171e8e4d4813fdb2d26602`
used actual Codex CLI `0.162.0-alpha.17.2`, Sol / Medium, profile
`573fdfe26832fdbca701900931d127e4f63ca74b2a2f075ef92c1d0ea7919397`.
It froze a maximum of eight text attempts and two normal-order image attempts,
with complete inventory required before images. Product ceilings were frozen
at 32 images / 40 jobs; no ceiling changed during execution.

Project `46ccc914-be76-4538-a731-552051c1dcd3`, run
`a748cfdb-f863-4c04-8369-426665b002dd`, completed and adopted all eight text
deliveries: Outline, Branches, Cast, Art, Script, Storyboard, Bridge Intent and
Bridge Presentation. Each has a successful typed receipt and derived report.
The original Outline attempt reconciled after same-owner reopen without resend.
Bridge installation then stopped with `contract_blocked`; no image dispatched.
This does **not** satisfy the complete functional criterion or prove speed.

Evidence remains under
`.local/native-proof/coordinator-serial-596c2213-20261014/`. Its
`halt_record.json` verifies 16 delivery files and all eight absent process
groups. All three pre-existing evidence roots match their frozen preservation
inventories; credential/token/session files are excluded from those inventories.
Halt receipt SHA-256:
`73ab8b31e4de17f97415fab749c1c4fc60e5bca5974a783891a6502da8f6390a`.

## Diagnosis and bounded correction

The accepted Script's exact reserved `VO` speaker was incorrectly required to
map to a Cast character. Reviewed source `659b0521` corrects that projection
without changing unknown-speaker behavior, text, notes or timing. ADR 0172 owns
this decision; its initial number was corrected to preserve Python ADR 0171.
The affected VO/Bridge/Presentation focused union passed 25 cases.

A read-only projection with the correction removed that speaker conflict and
exposed a separate timing failure: the retained line needs 7,920 canonical
milliseconds but its retained shot allows 6,500. The original project tree,
proposal revision 4/hash and accepted candidates remained unchanged. Diagnostic:
`post-vo-readonly-diagnostic.json` beside the halt receipt.

[ADR 0173](../adr/0173-f5-canonical-dialogue-timing-admission.md) records the
source evidence, rejected alternatives and ownership alignment. The shared
trusted estimator now supplies Bridge and a fresh F5 timing contract. Both
fresh validator routes retain all upstream gates and enforce exact canonical
minima, source ownership, cut/segment limits and complete-route ceilings.
Report language remains distinct from saved spoken language. F4 source JSON,
its independent estimator, canonical rates and retained timings are unchanged.

## Executed development checks

- Focused affected F5/VO/Brief/timing union: **64 passed**.
- Expanded frozen-plan/profile/resources/operation-diagnostic union: **83 passed,
  3 failed**. Failures were two old unit fixtures lacking the now-required saved
  language/source context and one exact allowlist expectation missing the new
  dependency. The corrected failed-consumer union passed **20 cases**; production
  grants remain specific to the chosen adapter. Unchanged passing evidence is
  reused, not presented as a fresh all-86 rerun.
- New timing regressions exercise both routes, real render/admission/F5
  acceptance/Bridge installation/reopen, exact 7,920 ms VO, two cues in one cut,
  7,919 ms refusal, missing/duplicate ownership and missing/drifted timing inputs.
  Impossible-line preparation leaves no new candidate or execution-pin row.
- Module ownership discovery passed **2,151 pytest cases / 204 files** without
  executing test bodies. Both new tests have the creative-production owner; 15
  previously unregistered CLI files now have the existing shared-provider-dispatch
  owner. Their exact native case coverage remains in the full release gate.
- Quick frontend unit step: **1,377 passed**. Its type step exposed a missing
  exhaustive diagnostic label; corrected focused UI checks passed **18 cases**,
  both type checks passed, and deterministic frontend assets were rebuilt.
- Scoped Ruff imports/undefined-name checks and diff consistency passed.
- Independent stable source review and the narrow ownership/UI addendum found
  **no blockers**. Requested reviewer settings: GPT-6.1 Sol / High; effective
  settings unverified. Reviews were read-only and did not execute checks.

Logs are retained under `.local/coordinator-resume-20261014/` with `timing-*`
names. Earlier failed checks are retained alongside successful follow-ups.

## Changed F5 native qualification

Source `e71e537f89130eb6fd8f4b7f60019ba89710fa47` passed the actual
provider-free sandbox qualification for both preset/manual and saved-Brief
F5 routes. Each successful production plan validated and rendered its exact
candidate. Both routes rejected the 6,500 ms cut against the unchanged 7,920 ms
minimum. Missing and drifted metadata caused four production preflight refusals
with zero dispatches. Separate frozen adversarial diagnostic copies also failed
the exact validator entrypoints for those faults; these controls bypassed no
production admission and claim no receipt or adoption.

All **ten sandbox commands** returned their expected results. Candidate/package
hashes remained unchanged and all recorded process groups were absent. There
were zero model/provider dispatches and zero ImageGen calls. Evidence:
`.local/native-proof/f5-canonical-timing-e71e537f-20261014-02/`, including
`plan.json`, immutable script snapshots, per-command stdout/stderr and
`result.json`. The actual CLI remained `0.162.0-alpha.17.2`.

Independent prelaunch review found a diagnostic cleanup flaw in the initial
prepared plan: waiting only for an exited leader could leave descendants.
That plan never launched and is retained with its rejection record. The
corrected harness keeps an identity-checked group owner alive through cleanup,
uses production ownership checks before signaling, and requires group absence.
A bounded local control proved cleanup of an orphan that ignored SIGTERM.
Its first preparation failed before any child because the temporary output
directory was missing; the failure root is retained separately. The corrected
control and fresh plan passed independent delta review with no blockers.
These changes concern the ignored qualification harness, not production
sandbox argv, permissions, model settings or supervisor semantics.

## Fresh bounded serial proof

Source `8ee80e9b148ffdb6a19ee698ce0a4387b01ba9d4` completed the fresh
production-supervisor criterion at `2026-10-14T21:55:24Z`: eight actual text
deliveries were adopted, Bridge installation became current, and two
normal-order character-reference images were adopted. The run then paused
before any third image. Model/effort remained Sol / Medium; product ceilings
remained 32 images / 40 jobs and the functional envelope remained eight text /
two images. The frozen complete inventory has 17 unique subjects across two
routes; the remaining 15 images were not dispatched by this experiment.

Project `15652b79-0c76-4626-a4a5-6ae2808355a0`, run
`60b52c00-0847-459b-bbc3-c0553f2aab52`, uses profile
`7a4fccea8fea939dde64083bcd38bf647d179da5561ad29b2b178d5f400dae17`.
Evidence is under `.local/native-proof/coordinator-serial-8ee80e9b-20261014/`.
The result-bound `latest_snapshot.json` is the final pre-pause observation and
still says `running`; its bytes are retained. The additive
`post_pause_receipt.json` verifies actual paused revision 68 from an exact
disposable project snapshot. It verifies ten successful adopted typed receipts,
18 output files, unchanged packages, two current Story-Bible reference decisions
bound to exact native ImageGen original bytes, and ten absent owned groups.
All 2,580 filtered files and exact path inventories across five older evidence
roots remain unchanged. Same-attempt reopen occurred without a replacement.
Post-pause receipt SHA-256:
`7ad63e42949aff9abfd200a81e79e160fde3ed2c2f5153be682c51f1ac03fadf`.

The fresh Script contains actions only: its frozen F5 timing contract has zero
spoken lines. This run establishes functional adoption/installation and image
delivery; nonzero dialogue/VO timing remains supported by the accepted sandbox
controls and regressions above. There is no complete-pack, speed or human
acceptance claim. Independent manager audit verified all 16 trusted text
validate/render exits, both actual native image calls/events and transcript
evidence hashes, original/display asset bytes, budgets and absence of human or
video facts.

The first post-pause inspection **failed** its strict before/after file check and
wrote no receipt. Its in-memory baseline was not saved, so the exact original
delta cannot be reconstructed. The failed helper/log are preserved. A bounded
diagnostic on an exact disposable copy observed transient SQLite WAL/SHM
creation/removal and zero net delta; the original stayed unchanged during that
diagnostic. This does not establish the cause of the first failure and does not
justify a production storage repair. The corrected receipt method captures
source inventories and an exact delta even on failure, inspects a byte-equal
copy, and claims original-tree equality only over that new observed interval.
Its delta is empty. Manager review and the reopened independent failure-path
review found no remaining blockers. No assertion was weakened or file excluded;
no original run, snapshot or native job was rewritten or replayed.

## Remaining qualification

The stopped `596c2213` run remains inspection-only. The fair pool, early references,
truthful concurrent progress, paired all-route performance proof and one combined
full gate remain open. Resource-heavy measurement/full qualification requires the
manager's explicit quiet-window allocation. No hosted CI or live activation is
authorized; manager owns final integration/publication.
