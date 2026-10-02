# Creator stages 2–3: reviewed contract checkpoint

Status: implementation independently reviewed; committed-candidate verification
pending. Creator acceptance remains partial.
Baseline `c027131ab3be6797c4e1c5a229dec51d651411a4`, retained `main`.
The manager owns review, commit/push and deployment. No new Script task has been
prepared after the skill/brief correction.

## Actual creator UI evidence

All decisions below are provisional agent choices in the isolated test copy,
never owner creative acceptance. The normal project was not changed.

- Cast r3 updates all six image-direction fields to live-action photography.
  Persona, voice, IDs and consumer mappings remain equal to Cast r2. The retained
  photographic C01 image was enlarged, reviewed and explicitly reselected for
  current Cast r3; no character generation was required.
- Art task `ch_57cfcd09ea6444c39e8ea4ba93788971` was prepared and sent once.
  The complete returned report was reviewed and Art r2 explicitly accepted.
  Source/outline/map/graph remain r1, with one choice and two endings.
- S02 image task `ij_8eae79be679841a5bc9859a44acf4d40` was prepared and sent
  once. Built-in ImageGen produced three purposeful attempts; the first showed
  unwanted furnishings, the second a harbor, and the third used enclosed street
  framing. Only the third was delivered. It was imported, enlarged, compared
  with the retained S02 image, and explicitly selected as the copy's reference.
  The visible result has warm opaque windows, wet pavement, no visible sea,
  people or furnishings, and clear stopping space.
- The S02 revised-requirements form was opened, edited and cancelled. The
  frozen request, delivered image and current choice remained intact. A second
  distinct prepared/sent/delivered S02 job and the prop loop remain pending.
- Script task `ch_53712ec5f84d4a18a6c05c78532c28ca` was prepared and sent once.
  Its real delivery passed upstream validation but UI admission rejected it:
  `script must contain Plotloom sectionBindings`. Its three episodes have no
  top-level binding array. It was explicitly cancelled through the UI; all 12
  package/delivery files remain preserved. Script acceptance, scoped editing,
  storyboard generation and stage 3 acceptance remain pending.

Image limits: S01 continuity was text-guided because no S01 image was supplied;
detail panels are not verified pixel crops. The specialist renamed the selected
returned basename to `candidate.png`, contrary to the image skill. Preserve the
published receipt/output and require the exact returned basename on the next
job. Cleanup refused the tool-owned 0755 staging directory; no permissions were
changed and no renders were deleted. Retained paths:

- `/Users/wjmao/.codex/generated_images/01a0fb4f-5f01-7e21-a8c6-ea5f662c676f/exec-5df563aa-abd5-43d0-b56c-bcaf1fbfd7cf.png`
- `/Users/wjmao/.codex/generated_images/01a0fb4f-5f01-7e21-a8c6-ea5f662c676f/exec-dc794164-f98f-48aa-a0e0-25caa69dd688.png`
- `/Users/wjmao/.codex/generated_images/01a0fb4f-5f01-7e21-a8c6-ea5f662c676f/exec-993d327d-88af-4c5e-8046-fa84b1da9d5e.png`

## Root causes and implementation

ADR 0064 and receiving code already require trusted ordered `sectionBindings`.
The frozen brief merely said to use the mapping; the shared skill documented
characters/art extensions but otherwise required raw upstream shapes. The fix
makes top-level emission and a pre-publication equality/episode check explicit
in both primary brief and specialist skill. Mapping ownership and strict
receiving remain unchanged. ADR 0064 records the clarification. New focused
regressions reject missing/permuted bindings and mismatched episode sets while
proving the delivered files stay unchanged.

Consumer E2Es were stale at multiple boundaries: Art prepare omitted its required
style; fixture directions lacked the exact preset sentence; notices/navigation,
manual disclosures and collapsed shot support changed; native result checks now
use the specialist `/check` endpoint. Only test fixtures/interactions changed,
preserving current production contracts and prior failing evidence.

The cancelled-task lifecycle repair is implemented and frozen for independent
review. Ordinary request lookup rejects cancelled rows in all five stage owners,
which made the check route's discarded-delivery branch unreachable. Outline
also leaves its cancelled row visible at the head, so job identity alone cannot
establish currentness. A separately named terminal lookup reads the exact stage
row, checks project/stage/job and the persisted execution pin, and never recovers
authority from package bytes. Only prepared current candidates enter admission.
Independent review also identified ready candidates replaced after ordinary
refresh but before specialist completion. Noncurrent retained ready rows now
use the same verified discarded-completion path. Eight real refresh/replacement
cases cover Outline/Cast/Art/Script with valid or tampered proof, preserved new
heads and repeated checks after a new lease. Storyboard still blocks ready-row
replacement; no stage preparation or admission guard changed.
The original exchange verifies the frozen package and terminal delivery before
discarded completion; no project row or newer head changes.

Registry completion now checks saved project/stage context, one native dispatch
root, exact receipt job/task identity and exact lease ownership. The low-level
dispatch release is unchanged. Completed receipt tombstones allow repeat checks
without touching a newer lease; a valid terminal proof can finish the receipt
after a crash between lease unlink and tombstone write. Missing/partial/tampered
proof, foreign identity and invalid current candidates retain reservations.
Manual current delivery still admits without a native attempt. ADR 0093 records
these boundaries. The general project handle's existing exchange/pin methods
were moved unchanged into a cohesive adapter before adding terminal access.

Both native specialists are idle. The live Script reservation remains intact;
the running process still uses pre-fix code. No clearing, replay, service restart
or new dispatch occurred. Manager review and a committed pin must precede the
owned restart and explicit Settings reconciliation check.

## Executed verification

- Final focused gate passed 88 tests across terminal reconciliation, registry,
  routes, workflow and creative exchange. All 57 real-composition terminal
  reconciliation checks passed: five-stage
  cancellation/replacement, restart/repeat/new leases, unknown outcomes, absent/
  partial/tampered proof, request/pin/context/receipt/lease identity, frozen
  package/provenance, crash-between-unlink-and-tombstone and ready-replacement
  boundaries. Full Ruff for the new lifecycle modules/settings/regressions and
  `git diff --check` passed after the review finding was repaired.
- The broader focused batch passed 111 tests, then stopped at the explicit
  Git-selected missing-pin recovery test. That test creates a package from the
  current dirty skill and recovers from committed `HEAD`; only the shared skill
  hash differs. The extracted recovery method's AST is unchanged. The remaining
  focused files passed 42 checks with that one criterion deselected (overlapping
  earlier checks; do not add these counts). No recovery bypass was added.
  `terminal-reconciliation-pin-diagnosis.json` records the evidence. Rerun this
  criterion on the reviewed committed candidate before declaring gates complete.
- 50 Python checks passed across Script linkage, project Art/Script/Storyboard,
  creative exchange and specialist routes/workflow.
- Storyboard source/restart/currentness and deferred response ownership: 18/18
  E2Es passed after current controls/endpoints were aligned.
- Manager independent verification passed all 28 relevant current consumer
  E2Es, 28 focused Python checks, both frontend typechecks and skill validation
  before the lifecycle repair. Manager's existing dispatch/exchange checks also
  passed 40 tests on the lifecycle candidate; independent implementation review
  and the final broad Python gate remain manager-owned.
- Navigation 6, reader 3, manual entry 6 and production handoff 1 passed in the
  preceding combined run; the other tests in that run were interrupted for
  diagnosis, not counted as passing. The later 18-check run covers those owners.
- E2E TypeScript checks passed before browser runs. New test Ruff and changed
  Python F401 checks passed at the brief-only checkpoint; `git diff --check`
  passed. Full Script-file Ruff has four pre-existing I001/TRY004 findings, and
  repository.py has one pre-existing F401 finding, reproduced unchanged from
  `HEAD`. New lifecycle modules, settings and regression files pass full Ruff.
- Original API states, all 73 SQLite tables and 67 managed files equal the
  launch baseline. Current evidence is
  `.local/unattended-2026-10-02/evidence/stage23-contract-checkpoint-original.json`.
  Current copy state and failed Script hashes are in
  `stage23-contract-checkpoint-state.json`. Earlier failure traces remain in
  `creator-navigation-fixed`, `creator-consumers-fixed`, `creator-current-contracts`
  and `ownership-current-actions`; passing storyboard evidence is in
  `storyboard-current-task-check`.
- Fresh original evidence `terminal-reconciliation-original.json` still equals
  the launch baseline. `terminal-reconciliation-live-preservation.json` proves
  all 12 failed Script files and the live specialist reservation remain equal
  to the preceding checkpoint.

No live H3/video work was attempted in this slice. Fixture results are synthetic
verification, not real media acceptance. No measured cost delta is available.

## Manager review checkpoint

Independent review accepted the Script emission clarification and E2E repairs.
The terminal-access reviewer reproduced one replaced-ready regression; the
source owner repaired it, and an independent rerun passed all eight new cases.
The separate receipt-ownership review found no actionable issues. Its 76-check
batch and the access reviewer's 77-check batch overlap the checks above.

The manager's broad pre-commit run passed 888 tests and failed only the diagnosed
dirty-skill versus committed-HEAD pin-recovery criterion (233.02 seconds). This
is not a waived gate: the reviewed implementation must be committed locally,
then the complete suite rerun before pushing or restarting the isolated runtime.
No frontend runtime source changed in this checkpoint; the existing built
assets remain current. The worker and both copy specialists are idle, both
normal specialists are inactive, and normal health is good. Fresh manager
capture `manager-terminal-precommit-original.json` is byte-identical to the
launch baseline (API state, 73 tables and 67 files). Origin and local `main`
were aligned at `c027131` before this scoped commit.

## Owned runtime and next action

The isolated runtime remains at
`http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84`,
with bridge 8852 and final installation rooted under
`.local/unattended-2026-10-02/final-installation`. Session `8066` / PID 41667
remains owned and running; normal 8841/8842 are untouched. The process still has
the pre-fix Python brief loaded; restart only the owned runtime at a reviewed,
safe checkpoint before preparing the fresh Script package.

Native image chat `01a0fb4f-5f01-7e21-a8c6-ea5f662c676f` used GPT-6 Luna/Max;
text chat `01a0fb4f-60d9-7062-883a-e00f1d17d493` used GPT-6.1 Sol/Medium.
Keep both available. After independent review/commit and safe reservation
reconciliation, continue the remaining scene/prop loop and fresh Script →
Storyboard UI journey. Preserve the absolute 13:04:18 UTC stop-new-work and
13:34:18 UTC hard cutoff.
