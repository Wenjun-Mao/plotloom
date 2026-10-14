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

## Remaining qualification

Pin and qualify the changed F5 validator plans through the actual provider-free
sandbox: both routes' successful validate/render pairs and exact known refusals
for too-short, missing and drifted timing inputs. Record production preflight
refusals separately from adversarial validator-entrypoint controls; neither
creates a successful receipt or adoption. Reuse unchanged runtime evidence only
for unchanged inputs/behavior.

Then run a new bounded disposable production-supervisor proof under fresh pins.
The stopped `596c2213` run remains inspection-only. The fair pool, early references,
truthful concurrent progress, paired all-route performance proof and one combined
full gate remain open. Resource-heavy measurement/full qualification requires the
manager's explicit quiet-window allocation. No hosted CI or live activation is
authorized; manager owns final integration/publication.
