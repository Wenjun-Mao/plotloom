# Top-five historical storage review and cleanup proposal — 2026-10-25

Status: proposed for owner review. Investigation and planning only: no product
merge, historical-data deletion, media adoption, provider call or service change
is authorized by this document. The earlier cross-shot cleanup is complete and
is a separate scope.

Source reviewed: main `016552e63c0304b79a64fd76b351d1648579fc18`.

Aliases:

- `R`: `/Users/wjmao/.codex/worktrees/b30f/plotloom` (retained source).
- `P`: `/Users/wjmao/projects/HU/plotloom` (installed checkout).
- `W`: `/Users/wjmao/projects/HU/plotloom-worktrees`.

The [complete storage inventory](../../.local/cleanup-inventory-20261025.json)
remains the exact-path census. This plan resolves its first five review groups;
it does not replace the earlier approximately 4.2 GiB disposable-batch proposal.

## Findings and recommendations

| Group | Allocated KiB | Main-source conclusion | Recommended disposition |
| --- | ---: | --- | --- |
| Five parked checkouts under `W` | 3,451,240 | One useful committed reader proposal; remaining dirty product changes incorporated or superseded | Preserve its existing Git ref, the small census dependencies and one original image; remove checkouts through Git lifecycle |
| `R/.local/native-proof` | 1,945,772 | Production fixes already on main; historical source copies add no missing feature | Keep deduplicated real generated originals and provenance; decommission isolated proof envelopes |
| `R/.local/remaining-cost` | 590,932 | Three optimization families incorporated; private census unique and unaccepted | Keep about 0.6 MB of private source/decisions off main; discard copied checkouts, fixtures and profiles |
| `P/.local/relay` | 289,048 | No missing production source or skill | Keep selected original media and finite creative-source exports; discard all old fixture DB families and task/QA wrappers afterward |
| `R/.local/specialist-integration-20261022-preserved` | 213,760 | Specialist integration already merged; source archive semantically matches main | Keep six original media files; remove container images, duplicate source, browser captures and build output |

Total allocation is approximately 6.19 GiB, without double-counting the two
linked worktrees inside `remaining-cost`. After preserving source media and small
source/metadata sets, estimated reclaim is about 5.9 GiB. This is a planning
estimate; measure allocation after the approved operation rather than promising
filesystem free-space gains.

## The one recommended product merge

Keep `refs/heads/codex/python85-release` at `76d6a916` while evaluating committed
proposal `11b7ad65` and whitespace correction `4cb72753`. Do not merge the entire
old branch into current main.

Current `autopilot_materials.initial_inventory()` still calls
`production_bridge_state().installation`. That full state also assembles the
proposal, review presentation, preparation availability and job views. Main's
`d09322cb` shares context resolution within that state but does not eliminate
those unrelated projections.

Recommended change: port the narrow validated installation reader through the
existing read lease, project/head checks and `installation_in_session()`; expose
the small ProjectStore facade and change only the inventory caller. Keep current
staleness, canonical identity, missing/corrupt-evidence and exception contracts.
This separates responsibilities; no measured speed benefit is claimed.

Relevant current owners:

- `src/plotloom/persistence/project/production_bridge_installation.py`.
- `src/plotloom/project_storage/project_creative_stages.py`.
- `src/plotloom/autopilot_materials.py`.
- Existing Bridge, rebuild and inventory/readiness regression owners.

Port `tests/test_production_bridge_installation_read.py`, adapt readiness stubs
and register test ownership. Document the adopted decision and update ADR/spec
indexes; the proposal's historical ADR 0164 is provenance, not evidence of current
main adoption. Resolve numbering against the current ADR catalog at implementation.

Observable first slice: a disposable installed-story fixture returns the same
validated installation and material inventory through the narrow reader while
review projection methods are forbidden. No live user project or provider call
is needed. Cover missing/current/outdated installation, canonical and upstream
drift, corrupt proposal/hash/inputs/stage identities, missing project/head,
successive fresh reads and current read-only/authority boundaries. Then run the
affected current Bridge/rebuild/readiness owners, independent stable-diff review
and one stable final local full gate before merging product code. Historical
branch passes do not qualify the adapted change. Hosted CI and push remain off.

This useful improvement is independent of storage cleanup. Its existing Git ref
preserves the proposal; cleanup need not wait for its implementation or full gate.

## Source that must not be lost

### Parked source adjudication

| Checkout | Actual comparison with main | Disposition |
| --- | --- | --- |
| `W/autopilot-ux-release` | Dirty encoded-row/material-byte/hash/receipt mechanisms and their tests are incorporated; main has later processed-Result and snapshot-scoped reuse | Discard superseded dirty proposal after recording exact path disposition |
| `W/pre-video-autopilot` | 185 of 188 added nonblank plan lines already occur on main; remaining three claim completed work is still unapproved | Discard stale plan delta |
| `W/python85-baseline-timing` | Clean; revision reachable from main | Remove checkout |
| `W/python85-profiling` | Three commits patch-equivalent; `e4948ac3` executable changes incorporated by `da4bf5b3` and later owners | Remove checkout; no product merge |
| `W/python85-release` | Committed installation reader missing; dirty command-transaction optimization and authority tests incorporated | Keep existing proposal ref; discard superseded dirty changes |

Before any forced worktree removal, revalidate the exact dirty/untracked path
set against this reviewed disposition. An unexpected new change is preserved
and reviewed independently; it does not hold unrelated approved removals.

### Unique private optimization source

Keep these off main in a dedicated local Git preservation commit/ref, using an
isolated temporary index and leaving main's index/tree unchanged. Existing Git
history already preserves committed branch work; do not create checkout or tar
backups of it.

Under `R/.local/remaining-cost/whole-worker-stack-census-52b61d0c-prep-20261017-02/`:
`observer.py`, `native_entry.py`, `census_worker.py`, `census_bindings.py`,
`census_plugin.py`, `census_sampler.py`, `census_capture.py`, `pure_core_guards.py`,
`pure_guards.py`, `pure_protocol_guards.py`, `control_flow_guards.py`,
`expected-native-cases.txt`, `README.md`, `PAUSE-RESTART.md`, `root-cause.md`
(478,892 bytes).

Keep its two actual helper dependencies:

- `W/autopilot-ux-release/.local/remaining-cost/current_python_external_capture.py`
  (19,527 bytes).
- `R/.local/remaining-cost/canonical-row-bytes-screen-20261017/run_arm.py`
  (10,079 bytes).

Keep the small useful decision/analysis files under `R/.local/remaining-cost`:

- `autopilot-prefix-eligibility-52b61d0c-20261017/decision.md`.
- `current-python-52b61d0c-prep-20261017/{whole-analysis.json,raw-admission-restart-addendum.md}`.
- `raw-admission-region-52b61d0c-prep-20261017/method-decision.md`.
- `raw-admission-B-design-4a61133f-20261017/decision-note.md`.

The latest timer sources and guards under
`raw-admission-timers-52b61d0c-prep-20261017/` add 45,151 bytes:
`raw_timers.py`, `child.py`, `outer.py`, `support.py`, `protocol_guards_v3.py`,
`synthetic_guards_v3.py`, `thread_trace_guard.py`, `method.md`.
The complete proposed source/decision set totals 598,089 bytes.

This preserves useful authored work, not an executable old resume packet.
`Census.invalidate()` still suppresses `BaseException` from its fault sink; that
control-flow defect remains unresolved. The B note's assumption of no explicit
transaction is superseded by current `BEGIN` and `proof_scope` behavior. Record
these limitations with the source. Do not resume optimization, reuse old pins,
merge this experiment or make a speed claim as part of cleanup.

Old one-shot valued-rollout/cutback operators are pinned to obsolete deployments
and hardcoded allowlists; they are not current recovery dependencies. Do not run
them or retain gigabytes merely to keep them executable. Current functional
recovery and existing valued installations/backups remain excluded from cleanup.

## Creative source and original media preservation

Use one private content-addressed source-material collection, proposed at
`P/.local/creative-source-library/`, outside all deletion targets and current
project/application storage. Keep originals and compact ownership/source records;
do not create a new project, auto-adopt material or publish binaries into main.
Verify destination SHA-256 and byte counts before deleting the last source copy.

Recommended masters total **109 unique files / 255,089,847 bytes** (about 243 MiB),
plus small provenance/source records. These are genuine generated development/QA
originals, not human creative acceptance. This is preservation of irreproducible
source bytes, not retention of test evidence. Rights/selection declarations remain
as recorded, including uncertainty; do not promote them by relocating files.

### Native proof masters

Discover no-follow `**/delivery/outputs/exec-*.png` under `native-proof` and
deduplicate by SHA-256. Resolve each completion's
`toolEvidence.executorAttemptId` to exactly one original owning supervisor row;
require completed image state, `terminalResult=success`, a saved receipt and
matching job ID/request hash. Select that row's `job_root/delivery/outputs/` file
and `job_root/delivery/completion.json`, verifying the output hash. The 107
filesystem receipt paths include wrappers; only 89 genuine owner receipts are
needed (355,109 bytes). The canonical owners are:

| Child | Unique originals | Bytes |
| --- | ---: | ---: |
| `current-parallel-4525e3e0-20261015` | 16 | 35,729,813 |
| `paid-pair-d52a863e-20261016-01` | 7 | 15,871,031 |
| `coordinator-serial-8ee80e9b-20261014` | 2 | 4,224,305 |
| `matched-pair-observed-2a359171-20261015-02` | 3 | 7,071,816 |
| `paid-pair-4a0d3478-20261016-01` | 4 | 9,988,505 |
| `paid-pair-44c581aa-20261016-02` | 18 | 42,749,178 |
| `paid-pair-b313ac83-20261016-01` | 30 | 74,128,573 |
| `matched-pair-8ab58839-20261015` | 6 | 14,428,354 |
| `matched-pair-observed-8ab58839-20261015` | 3 | 7,076,636 |

Root independently verified 89 unique hashes / 211,268,211 bytes and no match in
the recorded eight-project media inventory or current tracked media. Keep the
matching `delivery/completion.json` ownership/actual-prompt records; original
request recipes add about 1.5 MB if needed for reference bindings. Discard display
copies, geometry derivatives, browser screenshots, synthetic references and raw
sessions after their source/recipe relationships are represented.

The two discovery aliases `postpause-storage-diagnostic-8ee80e9b-20261014` and
`paid-pair-7b1e38f5-execution-20261016-01/closed` add no separate ownership: their
two and eighteen originals respectively map to the canonical rows above.

### Other masters

- Parked `pre-video-autopilot/.local/p5-retained-native-original/original.png`:
  2,087,717 bytes, SHA-256
  `30f3a733e973371a38f3fcd4fa4f47ef9081da240b7dbfe215cc70636a339be7`;
  keep its 808-byte `proof.json`. Centered derivative is regenerable.
- Relay: six original H3 clips, two original keyframes, two distinct Lighthouse
  stills and three nonduplicate character stills: 13 files / 23,043,629 bytes.
  They are under `real-shot-trial`, `h3-adjacent-shot`, `h3-longer-shot` and
  `ef469f97-f8f0-4cf0-8d63-6b67e4c9638a/characters-walkthrough`.
- Specialist: five original H3 MP4s plus `h3-walkthrough-20261021/first-frame.png`:
  six files / 18,690,290 bytes. Source copies are under `worktree-evidence` in
  `.playwright-cli` and `.local/h3-output-actions-20261022`.

Two copies need no extra master: Relay character hash `42ec6a9e...` is already
tracked as `docs/verification/supporting/p0-generated/01-arrival.png`; specialist
clip hash `9abfeb93...` is already in current project `d7deb82f-4801-4c9f-bfa8-9195c3b36489`.
Recheck those owning copies before discarding duplicates. Other candidate hashes
had no duplicate in the checked valued-example/current-story/legacy-output roots;
this is a bounded duplicate check, not a claim of global uniqueness.

Exact non-native master selectors follow. All are relative to their named
preservation source, not proposed new runtime paths. `A` and `L` are respectively
`P/.local/relay/{h3-adjacent-shot,h3-longer-shot}/outputs/20260922T165155656597Z__fbb913c8-534b-4439-ba68-211e70ec743d/assets`.
`C` is `P/.local/relay/ef469f97-f8f0-4cf0-8d63-6b67e4c9638a/characters-walkthrough/outputs/20260920T202903050473Z__e31b1149-edb6-4611-b76c-accd4210fc22/assets`.
`S` is `R/.local/specialist-integration-20261022-preserved/worktree-evidence`.
Content-addressed asset basenames are their complete SHA-256 values.

| Master | Bytes | SHA-256 where not in basename |
| --- | ---: | --- |
| Relay `real-shot-trial/opening-s1-c1-original.mp4` | 1,452,979 | `38aa919615253555b42babb56db200a25b8de0c1c4472283d21c99cfb71c5356` |
| `A/89/890de05d3f7181bdd5bd5dab99a9d461fc354387a404295b3c80f73201fd8a76` | 1,473,577 | basename |
| `A/7f/7f1fb4000f4e51dc3d39387987fd1d90a7cc2888beee22d8081bf7668b64bdb4` | 1,665,242 | basename |
| `A/00/00f043757e7879dbb56457498e47c48217d1af665a5809756491ed5bd9a1432d` | 1,584,691 | basename |
| `A/69/69d8f07be25cddf2405588058e7d67ba76ba9558011f0358975e13a33b316e7a` | 1,110,674 | basename |
| `L/35/35f8d1b4444651055d9b2493d7654b6065e172903441aabb5bedda08eceb6a02` | 1,600,276 | basename |
| Relay `real-shot-trial/opening-s1-c1-keyframe.png` | 2,126,970 | `7c4c375db892b1b1cbc02136df59ab7fb627affbaf9437e2202b9fb939627d48` |
| Relay `h3-adjacent-shot/opening-s1-c2-first-frame.png` | 2,272,214 | `68ebf2f172d7f987d64a4780a6851f3bc89ed83d463021605c16a36519f20a5a` |
| `A/a0/a0e37cfa541b358f081312c5708d3f936db0ab382258ae44bdd175b66220fc7d` | 2,070,047 | basename |
| `A/56/56dec8379201ab4cc9e3736b642e5ec7d37bcc43afe174cd1291990f9aa34a4e` | 2,209,255 | basename |
| `C/8a/8a84b56014ccc15cab2877c68cef890bdb61448265c2506bfa85af9d88db0bf1` | 1,730,196 | basename |
| `C/99/9909481b8aa670947e078428b4837c901db66d8919a840d306b0971027bb2d96` | 1,826,407 | basename |
| `C/97/97ea52c92939f56a4b0bd8aec6c06615447c184c51bf8783b6ec63d279aa3ba1` | 1,921,101 | basename |
| `S/.playwright-cli/2026-10-21T00-00-00Z-h3-3ecd1f2f13bb4593aa1a48151d693bfe.mp4` | 4,080,043 | `e06de02f2f7a132a01b349e3ca44b9701383741f74318fd66cccf1ef68f69299` |
| `S/.playwright-cli/2026-10-21T10-47-16Z-h3-7975b0fcecc14cdf9ce9c6bcd41ebe55.mp4` | 4,930,200 | `89a64b849533d030bf73cff51c13334fb7b034b7b521045bf7996c2180b20771` |
| `S/.playwright-cli/2026-10-21T18-06-41Z-h3-cc23e43b2db24cdc8f2c0ac480b0cd79.mp4` | 456,698 | `8cb06bcfca59c1d0ea0ef1269293c38dade87dd3a511bb016671034155938841` |
| `S/.local/h3-output-actions-20261022/h3-output-actions2-https-original.mp4` | 2,822,384 | `28f9720fd4a9c2dab78bcc1337f0ea46cb7f2e8282f8194331e797817e524a91` |
| `S/.local/h3-output-actions-20261022/h3-output-actions-https-original.mp4` | 5,168,259 | `1d8a4a7055e16c34ec61f139220d4cdd942a84607b6c309d9a515a93ac7db898` |
| `S/.local/h3-walkthrough-20261021/first-frame.png` | 1,232,706 | `36d6534d670d477ea24e642a3cd12ca6c1e80e1d4c55d8cdb97917e34b9f90c1` |

The twentieth non-native master is the separately specified parked original.

### Lighthouse source: export, then discard whole DBs

Five idle historical DB families were compared using temporary copies. Original
DB/WAL/SHM bytes and directory listings were unchanged. They share original
source, canonical stages and zero author drafts; the accepted 27-cut and 26-cut
variants share all 57 saved intent entries. No whole DB needs permanent retention.

Retain `u4-lighthouse-walkthrough/logs/agent-source.txt`, its five accepted
Outline/Cast/Art/Script/Storyboard delivery JSONs and matching completion records,
plus longer-shot's 26-cut storyboard delivery and completion.

The five accepted Lighthouse jobs are `ch_5359cd306cd84354af805ec10f03c648`
(outline), `ch_c97e6e10ce0741c78b9165891ce49101` (cast),
`ch_5099cb49e6164cabbb8863caa611180a` (art),
`ch_bfbebaace45c4c9b926a859dbebf0921` (script), and
`ch_56f07c3cb22641fba27267943921c977` (storyboard). The longer storyboard is
`ch_e899f337fcfa4cd7a2061799baf96490`. Select each job's named stage JSON and
matching `delivery/completion.json`; compare stage content with the canonical
objects before retiring the source DB families.

Export these exact fields once, as sorted-key compact UTF-8 JSON without a
trailing newline; compare the canonical hashes before discarding DB families:

| Export | Source field | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `source-material.json` | source revision r1 `material` | 1,786 | `4fd3df018e95dde36573e71f317ab19bf64b3aea63a58595d15619dbe13bdab9` |
| `section-map.json` | section-map r1 `mapping` | 1,245 | `12d68596eb3c68190dc2dbceea383255b13fb3c9300c5963c0b1fd480dc6146a` |
| `author-intent-entries.json` | bridge proposal `intentPackage.entries` | 25,254 | `cb8d8e251819993c7e2995198d319184334dd9a16174abe2d7406bb225154c1d` |
| `keyframe-provenance.json` | longer-shot managed-asset `declaration` | 270 | `48b8d2270077f2980fe13afe5c93e107fedf86b66943d2a885d1f60d95223326` |

Bind agent-authored project `fbb913c8-534b-4439-ba68-211e70ec743d`, original F5 r2
→ bridge r2 / 27 cuts, and longer F5 r3 → bridge r5 / 26 cuts in one source record.
Retain media/keyframe/job relationships and the original model-origin versus
author-saved workflow statuses. `author_saved` does not mean owner-personal authorship.
Preserve the differing recorded rights declarations without inventing a grant.

## Retire historical UNKNOWN envelopes without inventing outcomes

| Private attempt | Project | Historical domain |
| --- | --- | --- |
| `95ab2970-1f85-4db7-89cb-ae4a11cb9b82` | `57ed35e8-1d12-46fa-a351-d6733e800216` | Codex text |
| `0d5b68d5-0002-43eb-ac48-726d843173da` | `2bdf857e-d9b5-4448-b3bc-e2c8ebc284d3` | Codex text |
| `7102e940-fa34-4226-ad0e-6e8ec157148d` | `a074c32e-8eee-4baf-b76a-db03e93d5cec` | Codex/ImageGen |

These are private historical supervisors, absent from installed host attempts and
revocations. Installed state was 85 attempts (82 completed / 3 settled), zero
UNKNOWN, queues, slots and validators. Do not recreate installed holds or inject
old rows into current host accounting.

The text ledgers predate current revocation/retirement tables; the image envelope
uses frozen historical pins and does not meet current no-dispatch recovery rules.
Do not initialize, migrate, replay or resume them through current bridge APIs.

At cleanup, verify exact private paths still have no processes, handles, mounts,
publication consumer or resumable owner. Retire the whole isolated execution
envelopes and external one-shot helper references together. Keep one concise
identity/disposition record: retired from use, remote outcome remains UNKNOWN,
no retry or adoption. This is a functional no-reuse boundary, not a settlement or
an audit archive. Raw ledgers, sessions, copied Codex homes and queued fixtures need
not survive merely because their historical row says UNKNOWN.

If a concrete consumer is discovered, defer only its bounded envelope and record
the exact next action; continue unrelated approved removals. The conservative
temporary review subset across all three is 24 files / 4,882,394 bytes, including
two already-deduplicated original references. There is no blanket UNKNOWN-ledger
retention requirement or prerequisite to query a provider simply to delete a
fully isolated, retired QA envelope.

## Proposed execution order and acceptance

1. After approval of this cleanup scope, freeze one source owner and take a fresh
   current-project/settings/host/runtime preservation baseline. Revalidate the
   exact target paths, Git status sets and no-follow deletion boundaries.
2. Preserve the reader's existing Git ref, the small unique census/decision set,
   original media and finite Lighthouse source exports. Verify hashes and Git
   object reachability. Do not retain whole historical directories as backups.
3. Verify an actual small preservation-and-removal slice on one completed fixture
   subtree, then continue the reviewed inventory. This is an engineering check,
   not another owner-approval checkpoint.
4. Retire the private execution envelopes and their old preparation/receipt/helper
   consumers as above. Remove registered linked worktrees with Git's lifecycle;
   dispose only the reviewed superseded dirty paths. Embedded copies and zero-byte
   uv `.git` markers are separate from registered worktrees.
   The 24 loose paths in the inventory's `source-proof-helpers` group are the
   finite external helper candidates: remove those whose consumers are wholly
   retired here, after keeping the named census dependencies. Current snapshot
   tools, validator setup and any newly demonstrated live consumer stay intact.
5. Remove remaining disposable contents of all five groups; retire stale artifact
   links, obsolete launch/cutback instructions and already-incorporated source
   inventories. Keep concise truthful failure/qualification boundaries and useful
   current ADR/design decisions. No bulk archive or ongoing audit-history store.
6. Compare all eight current projects/media/settings and current host tables with
   the fresh baseline; verify current validator identities, runtime configuration,
   intended storage consumers, HTTPS health and functional recovery package.
   Record process/container identities and classify any differences: an unrelated
   normal restart or legitimate user edit is not cleanup damage. Investigate
   unexpected changes plausibly caused by cleanup; never overwrite newer user
   data to force baseline equality or restart a healthy service just for a check.
   Refresh recovery's tracked-doc content if this work changes documentation.
7. Report exact preservation destinations/refs, removed allocation, any narrowly
   deferred consumer and clean source state. Existing runtime, valued examples,
   current dependencies, outside valued backup roots and Spark data stay intact.

Routine in-scope preservation, export, source adjudication and supported worktree
operations continue under the approved batch without repeated milestone approval.
The optional reader implementation remains separate; no generation, paid provider
operation, source experiment resumption, deployment, push or GitHub CI is part of
this cleanup. No tests are needed merely to delete retired data; run checks
appropriate to any actual product-code change instead of repeating release gates
for a storage-only operation.

Independent read-only execution-limit review completed (requested GPT-6.1 Sol /
Medium; effective settings unverified). One correction replaced literal process
identity immutability with classified changes, preserved configuration/consumers
and functional checks. No other material findings or added approval gates.
