# Python optimization: Pro decision-support packet

Status: **DRAFT — local review-branch preparation, not published or handoff-ready.**
Root must review, publish the separate branch and verify anonymous access to the
exact source and packet revisions before handoff. No Pro review has run.

## Purpose, mode and decision

Use **one Pro consultation** for independent source-grounded reasoning: challenge
the diagnosis, explore or simplify viable optimization paths, and recommend the
smallest useful next experiment or owner decision. Deep Research adds little
currently because the uncertainty concerns this implementation and its contracts,
rather than broad external discovery.

The fixed whole-Python target is **151.73295 seconds**, still unmet. Do not assume
the proposed paths can reach it. Question the framing, target feasibility,
measurement interpretation or options if warranted; do not silently relax the
target or manufacture agreement. Retaining the current implementation or
reporting insufficient evidence is a valid conclusion. We seek decision support,
not an implementation plan, code changes or ratification of option B.

## Source anchors and access

- Repository: [Wenjun-Mao/plotloom](https://github.com/Wenjun-Mao/plotloom).
- Intended discovery branch:
  [codex/python-optimization-pro-review-20261015](https://github.com/Wenjun-Mao/plotloom/tree/codex/python-optimization-pro-review-20261015).
- Exact source and current-profile anchor:
  [`5f71239ac278b073b898924093dbd3e5f537e7a5`](https://github.com/Wenjun-Mao/plotloom/tree/5f71239ac278b073b898924093dbd3e5f537e7a5).
- Whole-Python measured revision:
  [`f1a3333abc7343f4130f6e0014f3aba4b0699354`](https://github.com/Wenjun-Mao/plotloom/tree/f1a3333abc7343f4130f6e0014f3aba4b0699354).
  The later source anchor adds only its factual roadmap receipt; executable
  inputs are unchanged.
- The packet's own full commit will be supplied separately after its local
  commit. Do not assume this branch or source is on `main` or publicly readable.

Access is **GitHub-only**. Inspect accessible published source/documents; do not
run code, tests, profiles or probes, access accounts/services, or submit changes.
Local worktrees, chat history and private runtime evidence are unavailable.
Raw logs, pstats, allocation/ownership records and machine/account details are
intentionally not published. The summaries below were verified by the author and
independently reviewed locally; they are **provided evidence**, not raw evidence
the consultant has inspected. Do not infer inaccessible contents.

State the full SHA actually inspected. If either exact anchor is inaccessible,
report that limitation and distinguish any summary-only reasoning; do not
silently substitute another branch or claim to have inspected the missing source.

## Provided current evidence and limits

Whole Python: **2,449 passed / 228 files**, unfiltered native coverage, unchanged
default **two workers**, no skips/xfails. Observed whole-command wall:
**557.6845981249935s**. This is current Python correctness and observed wall,
not attributable gain, 85% attainment, full release, hosted CI or product acceptance.

The current instrumented diagnostic passed exactly
`tests/test_autopilot_images.py::test_complete_pack_selects_all_subjects_and_unique_route_frames_without_human_facts`.
The unchanged fake-host workflow retains all **8 text / 29 image / 27 frame /
2 route / no-human-facts** assertions; these are not actual model/provider calls.
Natural preparation and the complete case stayed inside the diagnostic.

On checked CPython 3.12.13, the same profiled child measured
**64.35725916700903s block wall** and **63.540475s process CPU**. The block includes
pytest import, collection, setup, case, teardown and reporting, with instrumentation.
Process CPU includes all threads in that process, excludes descendants, and is
not a per-function CPU attribution. Serialization/shutdown are outside those
block clocks. Main-thread cProfile uses its default **elapsed** clock, including
waits; it is not a CPU profile. Coordination covered known participants, not
global host silence or matched performance isolation.

Rounded current source-relative attribution:

| Function/owner | Calls | Cumulative elapsed seconds |
|---|---:|---:|
| `ProjectStore.open` | 499: 346 open + 153 inspect | 19.989 |
| `assert_autopilot_contracts`, nested under open admission | 499 | 17.380 |
| `_assert_checkpoint_binding`, largely nested in that validation | 27,558 | 11.156 |
| `material_closure` | 1,483 | 19.629 |
| `_material_payload`, nested under `material_closure` | 1,483 | 16.695 |
| Shared `json.loads` | 2,332,377 | 8.347 |
| Shared `json.dumps` | 1,078,824 | 8.996 |
| Shared Pydantic `SchemaValidator.validate_python` | 574,469 | 6.881 |

Caller/callee context: ordinary open enters current-database admission and retained
autopilot validation; its binding checks, bridge-adoption and frame checks overlap.
Closure callers include run views (702), production closure (470) and command
validation (192). Most JSON-load calls come through SQLAlchemy JSON result
conversion; canonical hashing is the largest JSON-dump caller. These observations
identify investigation leads, not proof that the checks are redundant.

**Nested cumulative costs are NONADDITIVE.** JSON/Pydantic costs overlap the owner
rows; shared Pydantic functions are not model-exclusive. Instrumented timing is
not a benchmark or speedup. This one case is not automatically representative of
the whole suite. Historical view counts and elapsed whole-file costs are not
fresh whole-suite source attribution. No avoided-work floor, projected saving or
sum of scoped old gains explains the remaining target gap.

## Owning source, decisions and regression map

All source links below are immutable permalinks at the source anchor.

| Concern | Entry points and evidence |
|---|---|
| Ordinary admission | [registry][registry] `open/inspect`; [ProjectStore][handle] `open/_validate_opened_project`; [current schema][schema] `assert_current_project_database/assert_current_review_bindings` |
| Retained authority graph | [autopilot validation][validation] `assert_autopilot_contracts`; [bindings][bindings] `assert_checkpoint_binding/_assert_exec_attempt_binding/assert_frame_binding`; [bridge adoption][adoption] |
| Current authority and atomic commands | [run owner][run] `claim/view_in_session/validate_command`; [command transactions][commands]; [leases][leases]; [controller][controller] `_step` |
| Material identity and encoding | [closures][closures] `material_closure/_receipt_material_closures/_material_payload`; [canonical hash][hash] |
| Filesystem and receipt boundaries | [geometry lineage][lineage] `assert_geometry/_assert_geometry_bytes`; [attempt settlement][attempts] `update_exec_attempt`; [receipt contract][receipts] `assert_receipt_matches_attempt` |
| Existing bounded reuse | [ADR 0176][adr176] receipt-segment projection; [ADR 0177][adr177] invocation-local profile construction; [ADR 0179][adr179] RunView-local checkpoint derivation |
| Exact diagnostic workflow | [case][case]; [image fixtures][imagefixtures] `image_environment/run_pack`; [text fixtures][textfixtures]; [fake host][fakehost] |
| Transaction/corruption guards | [WAL observations][waltests]; [receipt revalidation][receipttests]; [schema/WAL admission][schematests]; [authority/ordinary open][authoritytests]; [geometry lineage][geometrytests] |
| Claims, receipt segments and view isolation | [claim transactions][claimtests]; [receipt projections][projectiontests]; [view guards][viewtests] |
| Test preparation and verification | [closed seeds][seeds]; [geometry seeds][geometryseeds]; [native runner][runner]; [completion validator][completion]; [ownership][ownership]; [development policy][development] |

Existing reuse is already implemented; do not propose it again as an unimplemented
saving. Preserve the distinction between historical provenance and current
usability. An unchanged run ID, revision or row is not proof of unchanged files,
peer writes, claim authority or receipt state.

## Binding invariants and choices open to challenge

Preserve complete workflow assertions, native coverage/default two workers,
physical fixture isolation, retained corruption detection, currentness, exact
claim/dispatch/receipt authority, UNKNOWN-outcome safety and genuine human facts.
No cross-operation authority cache, ordinary-open bypass, unchecked model
construction, coverage filtering or simulated acceptance is an acceptable shortcut.

Current SQL traversal, repeated pure construction, internal ownership boundaries
and eligible test preparation are implementation choices that may be challenged.
If a concrete alternative changes observable admission or failure semantics,
identify the required owner decision rather than assuming permission.

The raw read-only SQLite admission connection has **no explicit complete-pass
snapshot**. Active cursors and implicit transactions can nevertheless already
hold snapshots; do not claim every SELECT sees newly committed peer writes.
ADR 0177 and its WAL/cursor/caller-transaction guards preserve this nuance.
SQLite describes [implicit transaction/statement lifetime][sqlite-transactions]
and [read-snapshot isolation][sqlite-isolation].

For B, the proposed extension is a snapshot across **one
`assert_current_project_database` admission pass**, not an atomic
`ProjectStore.open`: separate opened-project repository checks follow after that
raw connection closes. Filesystem byte validation stays fresh. No graph may
survive into later commands, writes, flushes, commits, rollbacks, standalone or
reentrant public validation. Passive inspection must not silently become a
writable open. Current claim-return/following-read and receipt/protected-material
checks remain mandatory.

## Candidate directions, not approved winners

- **A — pure derivation reuse:** retain fresh reads and checks; reuse only
  type-specific, proven-pure construction from exact fresh inputs within one
  invocation. No generic validation memoizer or cached receipt authority.
- **B — per-admission read-snapshot graph:** share relational loading/construction
  within the explicitly bounded pass above. Examine its visibility, lifetime,
  failure-order and complexity costs; owner acceptance of a changed boundary is
  required. It is not currently approved or a measured best option.
- **C — eligible closed-seed fixtures:** avoid repeating prerequisites that are
  outside the case's asserted behavior; retain independent copies, real admission
  and fresh case-owned jobs. Existing seeds do not establish another eligible
  consumer, and complete-workflow tests keep their natural preparation.
- **Narrower hypothesis:** `_material_payload` encodes rows for hash sorting,
  then final payload hashing encodes their content again. Investigate whether
  exact canonical encoding can be reused within that construction while keeping
  every SQL read, closure call, table/column, order, hash and failure boundary.
  Equal hash values alone do not prove equal canonical bytes or safe reuse.

You may reject these directions, propose a simpler source-backed alternative,
or recommend retaining the current approach. Do not assume reducing a call
count removes its cumulative cost or requires a new cache/epoch framework.

## Requested decision-support result

Lead with what changes the next decision. State the exact inspected SHA,
file paths and symbols; separate direct source observations, provided evidence,
inferences and untested hypotheses. Cite consequential repository findings with
immutable source locators.

Compare useful alternatives, expected benefit boundaries, complexity, delay and
the cost of keeping the current approach without inventing seconds. Identify
which invariants are binding and which assumptions a proposal needs the owner to
change. Do not require a forced recommendation or universal report length.

Recommend the cheapest sufficient source inspection or bounded local experiment
for the material uncertainty, with proportionate falsifiers and acceptance
criteria. Relevant counterexamples include peer WAL changes with held cursors,
pending writes/rollback, changed claim or UNKNOWN dispatch, forged receipts,
external asset tampering, failed/reentrant validation, and seed contamination.
Explain which actually matter to your proposed scope; do not manufacture gates
or ask to run them yourself. Retain original error/authority boundaries unless
an explicit proposed contract change is identified.

Your review is advisory: it authorizes no implementation, test/profile run,
publication, account access, provider/native execution or automatic follow-up.
Independent agreement would not establish correctness, savings or release.

[registry]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/project_storage/registry.py
[handle]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/project_storage/project_handle.py
[schema]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/project_storage/current_schema.py
[validation]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/project_storage/autopilot_validation.py
[bindings]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/project/autopilot_bindings.py
[adoption]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/project_storage/bridge_adoption_validation.py
[run]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/project/autopilot.py
[commands]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/project/command_transactions.py
[leases]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/transactions.py
[controller]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/autopilot_service.py
[closures]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/project/autopilot_closure.py
[hash]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/contract_hash.py
[lineage]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/project/image_source_lineage.py
[attempts]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/persistence/project/autopilot_exec_attempts.py
[receipts]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/src/plotloom/codex_exec_receipt_contracts.py
[adr176]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/docs/adr/0176-receipt-command-local-material-projections.md
[adr177]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/docs/adr/0177-invocation-local-autopilot-profile-construction.md
[adr179]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/docs/adr/0179-run-view-local-checkpoint-evidence.md
[case]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_images.py
[imagefixtures]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/autopilot_image_fixtures.py
[textfixtures]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/autopilot_controller_fixtures.py
[fakehost]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/autopilot_fake_exec_host.py
[waltests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_profile_transactions.py
[receipttests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_profile_receipts.py
[schematests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_project_storage_current_schema.py
[authoritytests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_authority.py
[geometrytests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_geometry.py
[claimtests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_claim_transactions.py
[projectiontests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_receipt_material_projections.py
[viewtests]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/test_autopilot_view_checkpoints.py
[seeds]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/autopilot_seed_fixtures.py
[geometryseeds]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/tests/autopilot_geometry_fixtures.py
[runner]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/scripts/testing/run_python_suite.py
[completion]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/scripts/testing/python_suite_completion.py
[ownership]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/scripts/testing/module-ownership.json
[development]: https://github.com/Wenjun-Mao/plotloom/blob/5f71239ac278b073b898924093dbd3e5f537e7a5/docs/development.md
[sqlite-transactions]: https://www.sqlite.org/lang_transaction.html
[sqlite-isolation]: https://www.sqlite.org/isolation.html
