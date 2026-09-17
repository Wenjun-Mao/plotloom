# F0 Shuohao foundation and handoff receipt

Date: 2026-09-17. Scope: F0 only. This records implementation and technical
evidence; it is not creative approval, canonical installation, or M2 product
acceptance.

## Delivered

- `third_party/shuohao-skills` is a project-local Git submodule pinned to
  `4322897e6d2bdaf66365534fd40194360c75a85f`, with the upstream Apache-2.0
  `LICENSE` and `NOTICE`; root `NOTICE` records the redistribution attribution.
- `plotloom-shuohao-specialist` routes one exact package through the five
  upstream stages. It has no backend, queue, selection, or canonical authority.
- `CreativeHandoffExchange` and its CLI prepare an immutable self-contained
  stage request and read a traceable candidate plus derived HTML report. It
  binds delivery to job/request/stage, exact upstream revision and skill hash,
  local specialist skill hash, output hashes, and stale-stage rejection. It is
  transport validation; upstream semantic validation and future review/install
  ownership remain separate.
- The five-stage field/gap/retirement map is in
  [F0 handoff contract](../creative-workflow/f0-shuohao-handoff.md). F0 has no
  browser entrypoint, so manual package operation remains an explicit F1/F10
  usability gap rather than hidden developer intervention.

## Disposable attended specialist evidence

Fresh `gpt-5.6-terra`, high-reasoning specialist task completed job
`ch_f0disposableterra003` from a self-contained two-episode synopsis package.
It wrote only ignored project output, never a canonical project record:

- candidate: `outputs/f0-disposable/jobs/ch_f0disposableterra003/delivery/outline.json`
- report: `outputs/f0-disposable/jobs/ch_f0disposableterra003/delivery/report.html`
- receipt manifest hash: `bdce28ae2cc9d4bdf48e0dd62d63a47d9c982d3d47ee68a343f846235fd72d2c`

The upstream `novel-outline validate --stage full` passed. Receiving-side
`creative_handoff.py inspect --current-stage-revision 0` accepted the candidate
transport and provenance. Its receipt binds revision
`93bf726cd09a16f575458d56f2f5f4ad26144732`, specialist hash
`5c18144f50ef790daee8a98748a628d282f562e37918df4fee9554ec73049315`, and
upstream revision/hash `4322897e6d2bdaf66365534fd40194360c75a85f` /
`e611c46f54513ae200eff525fc83ef16e7b0531a84ab6a456923d7c534988dde`.

Two earlier disposable jobs remain ignored, preserved evidence rather than
rewritten history: `001` exposed an ambiguous relative delivery path and an
impossible one-episode major-beat gate; `002` passed the upstream validator but
truthfully omitted known model/reasoning fields. The contract now names the
sibling delivery directory and requires coordinator-known provenance. The final
fresh run above was the adjusted method after those two failures.

## Verification

- Project-local specialist `quick_validate.py`: passed.
- Pinned upstream `novel-outline` deterministic self-test: 249 assertions
  passed.
- Fresh `git clone --recurse-submodules` fetched and checked out exactly
  `4322897e6d2bdaf66365534fd40194360c75a85f`.
- Focused exchange plus extraction-boundary tests: 18 passed after adding the
  explicit `.gitmodules` and `third_party` roots.
- Full Python suite at the executable F0 candidate: 570 passed, one existing
  Starlette deprecation warning. Log:
  `.local/relay/4175406c-e454-4960-bfc7-0f713865cb9d/f0-full-pytest-rerun.log`.

An independent attended Terra read-only review found missing execution-pin
binding, overly broad transport-admission wording, and a stale ADR status. The
execution binding and receipt test were added, the boundary is now called
transport validation, and ADR 0057’s status was corrected. No remaining review
findings were reopened.

## Acceptance boundary

Implemented: reproducible pin, candidate-only manual exchange, malformed/stale
delivery protection, specialist operation, and one traceable source-faithful
candidate. Not accepted or implemented: creative quality, source-rights
clearance, UI integration, canonical schema/install, review UI, media
generation, or retirement of old authoring paths.

## F0 recovery correction — 2026-09-17

The preserved evidence above describes the candidate at `c2921ce`; it does not
prove full F0 acceptance. Recovery found two foundation gaps: CI did not
initialize the project-local submodule, and candidate reading rechecked only
`request.json` even though the specialist consumes instructions and `inputs`.
The current candidate requires recursive CI checkout, validates the full frozen
package before readiness, and rejects an initialized submodule whose `HEAD`
does not equal Plotloom's recorded Git gitlink. These are transport and
reproducibility corrections, not a new canonical system.

F0 remains a checkout-operated candidate transport. It does not support the
specialist from an installed wheel and it has no chosen, implemented, or proven
review/canonical-install owner. The F1 UI/install decision and its owner proof
remain open; creative/product acceptance is still unclaimed.

Recovery verification at `447f8ff`: a new `git clone --recurse-submodules`
checked out the recorded `4322897e6d2bdaf66365534fd40194360c75a85f` gitlink
and passed the focused exchange suite (9 passed). The full Python suite passed
(574 passed; one existing Starlette deprecation warning), and the built wheel
passed `scripts/smoke_installed_wheel.py`. No frontend or browser suite was
rerun because this recovery changes only the backend handoff seam, CI checkout,
and documentation.
