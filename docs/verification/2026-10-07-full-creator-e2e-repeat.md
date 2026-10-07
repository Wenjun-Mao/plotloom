# Fresh full creator E2E run ledger

Scope: [approved repeat](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
The permanent C01–C55/P01–P06/E01–E22 checklist owns acceptance. Current status
is PARTIAL, not full E2E acceptance. Dated failures, interrupted gates, native
receipts and prior checkpoints are preserved verbatim in the linked
[historical receipt](2026-10-07-full-creator-e2e-repeat-history.md).
Historical present-tense statements there do not describe current deployment.

## Current status — final gate checkpoint, 2026-10-07

Local checkpoint `406c942` is local-only: no push or normal activation.
Normal8841 was stopped only after an immediate idle check at17:03 with the
established manage.py stop; it remains in maintenance awaiting
explicit restart approval. Deployment/token/specialist settings are unchanged.
Old checked static is recoverably retained in
`output/playwright/full-creator-2026-10-07/pre-capability-checked-static/`.

Retained8851/8852 Python (PID2191/session91780) started before the final shot-policy
cleanup. Its explicit-advisory QA is semantically comparable, not identical to the
final loaded Python. Its isolated static matches the checked candidate. SHA256 is
`c8fe9734faaed15142987c80fd318561260269d4e8c8415d853845dbcd6346ab`.
Fresh8861/8862 was NOT restarted: its exact image reservation remains busy.
Existing live QA tabs on8861 retain pre-capability loaded UI; its served checked
static bytes are newer, so those tabs must not reload against the old Python.
No absent-field compatibility fallback or concurrent API writer was introduced.

Final independent gates are PASS: V8 full Python 1,227 tests; frontend 582 tests;
V7 unfiltered full browser 204 tests; frontend and E2E typechecks, lock check,
API F401 lint, diff check, wheel build and wheel-installed smoke. Independent
source review has no blocker. Full 847-file final fingerprint:
`761a22ec55021b22a218d82569d2f0767600a8bf818f3f220ce5155adc2730c7`.
During the browser run only the authorized Python unit-test module changed;
the other 846 product/E2E/harness/static inputs remained identical. This is not
a claim that every input stayed unchanged. Prior interrupted/checkpoint gates
remain historical, not replacements for these final gates.

V7 Python had two failures: its dependency-invalidation fixture now began with
advisory policy, so advisory→advisory correctly remained ready rather than stale.
The single-file test correction explicitly tests advisory→strict invalidation and
advisory→advisory no-op for direct/draft saves, with unchanged no-op revision and
exact draft consumption. Focused module: 11 PASS/2.85s. Production behavior and
bounds were not weakened; V8 full Python includes this correction.

Durable gate artifacts live in `.local/full-creator-e2e-repeat-2026-10-07/gates/`:
`independent-final-v8-python.log`, `independent-final-v8-before.json`,
`independent-final-v8-python-after.json`; `independent-final-v7-browser.log`,
`independent-final-v7-before.json`, `independent-final-v7-browser-after.json`;
and `independent-final-v7-{frontend,typecheck,lock,lint,diff,wheel,smoke}.log`.
`independent-final-v7-python.log` retains the failed attempt, not a passing gate.
Wheel SHA256: `82bee9d078bcd01c4001183adf25d2661ea778dc0d546aa2c20b20d8544bdcde`.

Qualified software release still awaits root's exact scoped local commit, paired
normal restart and publication authorization. No final activation or push occurred.
The real E2E remains PARTIAL: native image continuation requires separate human
authority; remaining media routes and controls are not qualified by fixture gates.

Parent protection recaptures match the baseline aggregate exactly:
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
Scope is two owner DB schemas/rows, Wind17+Rain67 managed files and three protected
configuration hashes/modes/UIDs, not the global QA registry/application DB.
Root's final read-only recapture at18:24:32 matched this exact baseline and final
847-file source fingerprint; post-activation comparison remains due.

## Current coverage and explicit gaps

| Contract | Current qualification | Remaining scope |
|---|---|---|
| E01–E04/P01–P05 | Fresh UI Brief/source/Outline r1, native branch review/Confirm/Apply; actual Outline timeline/table PASS, export BLOCKED_BY_DESIGN | Richer native structure not generated merely for counts |
| E05–E06/C01–C55 | Separate real structural QA123→222→333 sequence; bypass/unconnected deletion/Undo; Save-close-reopen; partial-key C49; real stale-CAS refusal and matched live selection refresh; C48 legal/refused type/start guards; C50 endpoint/edge-only deletion/Undo; C51 retain/discard; C55 normal-flow help retests | Remaining type/kind/ownership permutations; OS blur NOT EXERCISED |
| E07–E09/P04/P06 | Fresh native Cast/Art confirmed r1 with offscreen style boundary; original gallery provenance, current static readers and original gallery zoom PASS | Native Character/Scene/Prop images and same-subject pair pending |
| E10–E13 | Fresh Script/Storyboard r1 confirmed; proposal r3 presentation reviewed/installed; ordinary first-shot handoff PASS | Model inference E12 NOT EXERCISED (runtime unavailable); physical direction realization remains unspecified |
| E14–E18 | No fresh native media-route qualification | Keyframes, managed endframe/dirty guards, multishot preview, H3/all routes/staleness NOT EXERCISED |
| E19–E21 | Task/reopen/owned idle restart; exact QA snapshot/operator restore/archive/unarchive/typed disposable-copy delete PASS | Media-bearing deletion and remaining lifecycle recovery NOT EXERCISED |
| E22/C37–C39 |18 actual graph pixels across three sizes/two preferences reviewed independently; three siblings readable;34s exploratory navigation and final clean nine-seed reset; final software gates PASS | Six-sibling state/OS blur not qualified; native journey remains partial |

### Fresh native identities and review boundaries

Project `b3a933f7-b6fc-40e3-826f-5162f95a119a` is the new minimal two-route film.
Brief/Outline/branch/Cast/Art/Script/Storyboard used supported first dispatches.
Cast's capacity failure was recovered once on the SAME job with explicit human
continuation authority; no blind resend. Cast is one offscreen Lin, half-painted
F2 style, not same-appearance or live-action creative approval. Frozen F3 Art,
Script and Storyboard follow author-selected live-action and no visible people.

Art r1 hash `640131312426c031d557214faf59696a9ff125880f32a5d3e9b86dda48e166df`;
Script r1 hash `e861b07e03c5ab51f01dbbb5257f47d91a86501b3002e6900267c693bd325be7`;
Storyboard r1 hash `375f1afd164e2f8a6cadf2f4076d0778e3ae4f0b0bf4a046617c3b7361031d06`.
Storyboard's one turn completed normally after1,440,093ms; report17/17 includes
recipe-library skip, placeholder Picture1 and unspecified physical east/west
realization. Pixels28–31 qualify visible report reading;27 does not.

Authored-intent checkpoint r2 hash `dec232ca6958789678713689bb68f53e5f2a21df77ec0a24a130b14225fc72d6`
has nine source-bound author intents (`suggestionOrigin=none`,
`reviewState=author_saved`, absent model provenance). Only presentation_required
remained then; later functional presentation classification/install is below.
No inference retry or invented physical direction.

Image `ij_5be49304cccb4b1bbbc215f08b2f75cd` stopped at committed-source preflight.
Frozen request hash `9bf2758335113c686f921d6f6f283e867911552c6762f8e39669389a483ce3ba`.
No image/completion exists. Preserve request/reservation; SAME-task continuation
still awaits separate human authority. Queue/package state is not native
execution status. Native Scene/Prop/pair/keyframes/H3 have not been exercised.

### Demonstrated repairs and separate evidence

Persisted-provenance omission is repaired in the shared public projection
(ADR0125), including earliest declaration ordering/null-vs-unknown semantics.
Character/shot disclosure-owner omissions are also repaired without inference.
Long-note layout initially stretched sibling actions; intrinsic card alignment
and all-sibling guards now pass. Four retained corrected1280/1700 pixels were
directly read by writer and parent; FAIL pixels remain separately retained.
These long-note fixtures do not qualify native image delivery or legal rights.

ADR0126 static Script/Art/Storyboard/Cast readers preserve archived bytes/hash,
CSP/empty sandbox, actual images, native disclosures and anchors. Pinned scripts
remain forbidden. Original live readers and final Script owned-note suppression
passed; duration/scene-table notes remain visible. Parent inspected38.
Retained8851 QA project `4ede8a69-bd36-4e3e-9e6f-5678181a29fa`, separate from
the fresh8861 native project, showed raw English as primary guidance in pixel40;
typed stale status now owns Chinese guidance, unchanged raw diagnostics remain
inspectable under technical details. Live42/43 preserve that retained project's
installed proposal r3 hash
`0dbdbfd4f3a89bf2bc7af418556cbaaaec74f785d3bd92cbcc37f3bf9992d653`.
No unsupported post-install reprepare or automatic regeneration is promised.
This is not the fresh native installation, whose current r3 hash is `ef1d922c5cb266cb5192d9a1f49846f46d19a77bb151c0b4d7f5d9019b8da6bd`.

Runtime-only intentGeneration capability (ADR0079) is available iff both service
owners are wired, never persisted into proposal/hash; typed503 refuses before
jobs/writes. Unconfigured UI disables service operations but retains authored
intent saving. Strict declared preset validation now precedes installation/key
bootstrap (ADR0011); explicit CUSTOM remains valid, no migration/relabel fallback.

### Structural and recovery readback

Structural project `0eabd058-b8a6-4ad1-8764-d2bbf11155be` retained exact unfinished
edge JSON and two-line prose through Save-close-reopen without Confirm/Apply.
C49 join `join-a5801402-05aa-52b8-a238-6e90dd2e660f` retained nonblank partial keys
`lamp.partial_QA_`/`lamp.unfinished_QA_` through blur/mode/select/save/close/reopen,
server draft53/baseCanon0. Blank separators/trailing list newline normalize by
the typed list codec; that is not nonblank content loss.

Matched8851 UI-origin QA `274ea714-6506-4396-9520-f1b818d79919` independently
proved stale draft3→4 refusal, no repeated stale POST, explicit reread preserving
this tab's surviving join despite another tab's stored start preference, newer
prose readback and new preview Cancel. Pixel39 qualifies the corrected selection.

Snapshot `20261007T171218926407Z__540792a9-a7e1-4436-b207-4ecbcde33ec5` was created
by UI. Operator restore into separate `.local/full-creator-2026-10-07/e21-restored-outputs`
has byte-equal project.sqlite3; no second API/writer or configuration restore.
Actual archive/unarchive and wrong-name/cancel/exact-name typed delete passed for
disposable brief-only copy `1154579c-dc16-4915-ba9d-e32778bea500` only (API404).
Source QA274 and snapshot retained; this does not prove media-bearing deletion.

C51 on QA274: unsent two-line prose retained by 保留草稿, then separately explicit
放弃图草稿 cleared draft/Undo. Server draft:null/baseCanon0 and original nine node IDs;
empty start title/prose, Undo disabled. Pixel45 directly read by writer/parent.
No accepted content existed, so accepted-media preservation is not claimed.

Graph18 pixels qualify readable/clamped graph-area editor, three horizontal
siblings, curved joins, footer, fixed dark composition under both color preferences.
Top graph-area clamp intentionally prevents literal viewport-only centering.
Pixel26's document selection is a prior nonqualifying attempt; clean pointer34
has empty selection before/after. No OS blur or six-sibling extrapolation.

### C55 current root cause, repair and retest

Pixel44 demonstrated focused help intercepting the required input. The owning
ContextHelp CSS absolutely positioned the explanation below the trigger, contrary
to its shared dock contract. Group-owned normal-flow dock now follows the five-field
grid; one active label/content, exact active-only aria-describedby, focused/pinned
priority and trigger-scoped Escape remain. No pass-through, clipping or focus weakening.
Two unit tests and both focused browser tests PASS12.5s; both typechecks/build PASS.
Changed legal input values plus exact restoration are tested, not only same-value fill.

Actual QA274 all five hover/focus/pin/Escape controls at1700×900,1280×768,1280×460
have own help text, no field/dock overlap and unforced associated/next input clicks.
Durable46 top views qualify unobscured fields;47 at1280×768 shows readable dock.
47 short view alone did not expose the dock and is not readability proof; ordinary
wheel scrolling reaches full dock/next settings in48 at1280×460, directly viewed.
Save scroll visibility is not save-action acceptance; existing Brief save checks
remain separate. Parent directly reviewed46-1700/47-768/48-460 and independently
ran both unit tests PASS305ms; source review closed without blocker. First live
alternate-value loop transiently made nodeBudget1/endingCount3 invalid and was
refused by background Brief validation. Exact values restored and error ordinarily
dismissed; no accepted write. Fixture alternatives now increment within valid
ranges instead of reducing node budget below ending count. Existing pinned help
closed on the first repeat-click observation; explicit Escape reset plus changed
values1/2 retest preserved pinned help. All15 pairs changed/restored; no blanket
claim that every transient combination was collectively valid.

## Final finite structural checks — 17:41 UTC

On QA274, edge `edge-11dfd08f-d8ab-5f56-bf5a-9e65035a0bdb` terminal cleared via
preview/Confirm and restored to `node-6dfd1b52-dfa7-591f-8c34-aa078cc9a97f`;
nine nodes retained. Delete EDGE removed only that connection, not either node;
Undo restored the same identity/target. C48 current-start type select is disabled,
and nonstart start option disabled. Connected scene `node-f0aa134f-bed2-5703-b302-64b585a7d1c4`
to ending correctly refused out_degree; scene to decision refused edge_kind.
After two failures, reassessed the edge/type contract rather than bypassing it.
Cancelled add-node dialog without preparing/adding a tenth node; deleted outgoing
`edge-0f415931-b5c7-582a-bb3f-31b673b223aa`, then legal scene→ending preview/Confirm
succeeded. Undo restored scene type; second Undo restored exact outgoing edge.
No complete type/kind permutation claim.

34s free-form exploration17:40:26→17:41:00 inspected ending Story/Production,
Professional layout/scroll and Creator join without a predetermined expected
sequence. No new defect. Final explicit discard restored exact original nine IDs,
draft:null/baseCanonical0/Undo disabled. No Confirm/Apply or accepted-media claim.
Presentation classification was authorized as functional QA, not creative/media
approval. Initial keyboard/pointer selection attempts were no-ops, not product
qualification. Plain readonly textarea reproduces the same behavior; editable
counterfactual arrows work. Ordinary native Shift-click works on both plain and
current readonly fields. Exact current source0:15 selected the lamp-stays prefix,
active:true/disabled:false, then Split produced two exact fragments with original
source unchanged. Native selection and existing full presentation fixture2 PASS22.1s,
no setSelectionRange or DOM mutation. Nine-source classification is paused to
prioritize source/gates at that checkpoint; later normal classification is below.
No image/H3 send, lease clearing or image continuation occurred.

## Uniform shot-policy cleanup — 17:54 UTC

Root/independent audit confirmed a compatibility split: absent stored policy was
strict while absent new-project input became advisory through helper stamping;
gate hashes excluded implicit policy. Owner's cleanup instruction supersedes this
dated ADR0080 clause. One current ProjectBrief default is now advisory; explicit
strict remains strict, helper/export/import/calls removed. Effective policy is
always hashed: implicit advisory equals explicit advisory, differs from strict.
Missing-field read preserves exact stored Brief/revision; no migration/read-time
write. Protected owners have explicit advisory, unchanged semantics. Strict
regressions now explicitly declare strict rather than weakening bounds.
Shot-policy/domain/source-outline34 PASS2.15s; bridge/generation63 PASS25.20s;
Idempotent missing-vs-explicit advisory creation included in final34 PASS3.53s;
API F401 lint and diff check PASS.
ADR0080 retains dated historical clauses with precise superseding current decision.

## Fresh presentation/install/handoff — 17:58 UTC

After source readiness, ordinary Shift-click source selection/splitting and role
controls classified all nine sources. Every fragment concatenates exactly to its
original source; source coordinates/hash/frozen evidence unchanged. Physical
renderings copy source verbatim; player opening→choice is runtime_choice; abstract
east/west state/termination and explicitly unspecified realization are review_only
with honest reasons excluding invented mechanisms/colors/signals/people/rescue
events and creative/media quality acceptance. Physical restrictions remain physical.
Pixel51 directly inspected the unspecified west-state reason and full restrictions
before Save/install; it does not independently prove installation.

Functional-QA completeness checkbox and Save produced proposal r3 hash
`ef1d922c5cb266cb5192d9a1f49846f46d19a77bb151c0b4d7f5d9019b8da6bd`,
reviewed:true/installable:true. Explicit Confirm installed normally: status accepted,
hasInstallation:true/installedStoryboardCurrent:true; three scenes/three exact5s
cuts, same east/west outcome IDs/coordinates and original two10s routes. No image
or video generated, no implicit media selection. Ordinary Continue opened
`shot:node-b64d6809-7161-5042-a7f8-a3c5c854e733-s1-c1` in the canonical workbench.
Pixel52 directly inspected5s/current shot/no-original candidate boundary; readback
has both route filters, exact physical opening actions, Lin unchecked/S01 selected/
P01 checked. No shot approval or further native task sent at this checkpoint.
Parent's read-only GET at18:02 independently corroborated r3/hash, accepted status,
reviewed/installable, three scenes/cuts and current installation. Pixel52 plus that
GET qualify post-install handoff; pixel51 remains pre-install classification evidence.
