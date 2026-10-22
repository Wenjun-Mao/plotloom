# Creator completion loop: implementation and acceptance evidence

Status: generic implementation checkpoint; live acceptance and final local
qualification remain manager-owned and are not complete in this record.
Baseline: retained checkout `1edae591`; approved scope is the
[creator completion plan](../roadmap/2026-10-22-creator-completion-loop.md).

## Implemented contract

- Distinct exact native-material QA grant freezes run, bundle/closure, complete
  reference decision/original identities and shot/frame originals. Atomic bulk
  handoff v4 carries typed actor through approval, intent, bindings, identity
  observations and portable receipt validation. Existing grants stay intact.
- Read-only project QA context distinguishes ordinary creators, verified eligible
  QA and known QA whose grant/current material is unavailable. Browser opt-in is
  explicit, project-local and resets on navigation; unavailable QA blocks writes.
  Every native write independently verifies its actual actor and original runtime.
- Gallery rejection records a reason without dispatch; exact predecessor cancel
  and successor preparation remain separate native operations. Recovery reads
  persisted state and recognizes explicit successor lineage. Good siblings and
  rejection history remain intact; new directions and Start stay explicit.
  Rejection reasons remain visible when preparing the successor.
- Timing is response-only, uses explicit UTC creation/observation and immutable
  adoption/handoff/AV-receipt facts, and shares the effective run state with the
  status response. Image preparation authorization is not adoption. Browser ticks
  use a monotonic clock; failed reads and terminal dates remain labelled honestly.

## Focused software evidence

Commands use the repository's locked environment, not hosted CI or live providers.

| Check | Outcome |
| --- | --- |
| `verify.py focused --pytest tests/test_bulk_material_handoff.py --pytest tests/test_delegated_qa.py` | 64 passed; existing human/manual-QA safety |
| Native-material QA, replacement and timing focused union | 32 passed before final review deltas; existing replacement 23 cases unchanged by later timing/context fixes |
| `tests/test_native_material_qa.py` after QA-context fixes | 9 passed; exact bundle, explicit actor, portable copy, changed pre/post-handoff closure |
| `tests/test_workflow_timing.py` after review fixes | 4 passed; immutable creation/GETs, explicit UTC, image authorization excluded, effective stale terminal |
| Focused material/autopilot/timing frontend checks | Pass; full quick below includes final versions |
| `verify.py quick` | Pass: 167 frontend files / 1,473 tests, API unused imports, dependency lock, frontend and browser-fixture type checks |
| Affected `frontend/e2e/video-batch.spec.ts` | Final 8 cases passed in 144.56 seconds, including cancel failure, cancel lost response, successor lost response and unavailable-QA refusal |
| Known-QA-unavailable browser case | Passed separately; no Start or job creation |
| `npm --prefix frontend run build:deterministic` twice | Identical seven-file SHA-256 trees; current `workbench.js` SHA-256 `4e509e09dd8c93c178c3070a2b26546af5364e9a7fba974d1c894b4d887d7fa8` |

The browser fixtures use synthetic provider media. They establish native UI,
persistence and failure-boundary behavior, not the live ImageGen/H3 journey.
Desktop 1280×768 pixel inspection confirmed readable successor rejection reasons,
truthful batch timing and the final saved confirmation controls without clipping.
Retained ignored screenshots are under `frontend/test-results/`:
`video-batch-selective-repl-54920-or-cancelling-its-successor/selective-cancel-response-lost-1280.png`,
`video-batch-selective-repl-fee50-or-cancelling-its-successor/selective-successor-response-lost-1280.png`,
and `video-batch-native-batch-s-d03d3-atomic-audiovisual-decision/batch-saved-1280x768.png`.

## Retained failures and diagnosed corrections

- The first new attributed native handoff failed at same-person review because
  its existing human reviewer encoder called `.strip()` on a typed QA actor.
  The identity write owner now admits typed QA only inside exact atomic bulk
  handoff and preserves its actor in readback. Native handoff/portable tests pass.
- Independent review found that unavailable QA was displayed as ordinary creator
  context, and that discovery omitted exact native material currentness. The
  context now distinguishes required-but-unavailable QA and uses existing native
  bundle/handoff readers; server refusal and browser blocking both have guards.
- Review found IMAGE authorization could be labelled as adoption and stale-view
  timing could keep ticking from persisted running state. Projection now selects
  only genuine adoption and shares one effective state; focused regressions pass.
- The first effective-stale regression used `manual_command`, which correctly
  changed the persisted run to `taken_over`. Its fixture now deliberately creates
  an external closure mismatch through the low-level test transaction, preserving
  the intended running-versus-effective-stale condition. No product workaround.
- Two frontend assertions retained old wording after truthful QA/status and batch
  handoff copy changes. Ordinary human uncertainty wording remains unchanged;
  the expected navigation copy now says video production, covering the batch path.
- Two focused selector invocations were refused before tests because Playwright
  selectors lacked the existing `e2e/` file path or used unsupported line suffixes.
  Correct whole-file selectors and one direct native `--grep` run were used.

Known tooling messages: jsdom reports its existing unimplemented `scrollBy` in
passing unit checks; Vite reports its existing large-chunk advisory. Neither is a
new product failure. An extra non-gate targeted Ruff check also found the existing
unused `ImageJobCandidateRow` import in the touched identity module; the native
API-import gate passes. No lint rule or assertion was suppressed.

## Boundaries and remaining evidence

No provider submissions, original-runtime grant binding, installation, activation,
owner-story edits, GitHub Actions or push were performed by this source worker.
No new full gate has run. Exact live native scope fields arrive only after the
manager's original native bundle exists; there is no placeholder/wildcard grant.
The manager reports that both configured native image slots are held by historic
UNKNOWN attempts, so new native images remain queued. This source work changes
neither capacity nor UNKNOWN/dispatch accounting. The live prerequisite remains
unresolved pending the manager's supported capacity/authority decision.
The exact read-only observation is retained in the
[native image capacity note](../../.local/creator-completion-20261022/native-image-capacity-observation.md).
The user subsequently authorized designing an explicit safe capacity-recovery
path; that follow-on is separate from this generic tested checkpoint and has not
changed UNKNOWN outcomes, reservations or runtime capacity.
The manager owns actual material inspection, the two-take/one-replacement UI loop,
native-audio limitations, ending playback/reopen, preservation checks, final full
local qualification and exact tested-package activation. Synthetic checks and
independent code review do not establish those outcomes or creative acceptance.
