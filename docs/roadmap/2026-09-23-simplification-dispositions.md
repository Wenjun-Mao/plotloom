# Simplification audit disposition register

Status: reconciliation for documentation Batch A, 2026-09-23. This is an
evidence/decision register, not implementation approval for B, C, or deferred
cleanup. The four immutable source reports and their baselines are named in the
[tracker](2026-09-23-repo-simplification.md); the insertion sheet restates the
independent SIM findings and is **not** independent corroboration. `Use` means
apply only the bounded documentation correction; `Test` means a later owner must
prove the candidate on current main; `Park` needs a product/contract decision or
population evidence; `Discard` withdraws the reported inference. Paths here
are current evidence anchors, not promises that old line numbers still match.

| Source IDs | Current evidence / corrected reading | Disposition and batch |
| --- | --- | --- |
| ADR-SIM-01; A1/A2/A3/A4; F26 | `canonical_schema.py:StableId` admits non-UUID authored IDs; `docs/adr/` had no entrypoint and two different `0040` files. Missing status or a later reference does not make an entire historical ADR false. | **Use A:** scoped 0004 note, authority index, full-slug 0040 links. **Park** universal status retrofit/renumbering; do not rewrite frozen IDs. |
| ADR-SIM-02; A9/A16 (0014); F8 | `persistence/project/drafts.py`, the project-folder draft routes, and frontend autosave keep CAS receipts; `sessionStorage` is unsent safety; canonical Save remains explicit. The old media-task worker is retired, but hard-stop refusals remain. | **Use A:** scoped 0014 draft note. **Park** broader 0006/0012 lifecycle decision; no media deletion. |
| A5/A13/A14; F3/F4/F12 | [ADR 0048](../adr/0048-retire-shared-repository-runtime.md) and `tests/test_shared_runtime_retirement.py` retire `legacy_repository`; project repository is current. Historical 0042 forwarding/lease corrections remain evidence. Manifest format 11 refuses old formats while two exact same-format transitions still exist. | **Use A:** scoped 0042 authority note. **Test C/deferred:** constructor patch only with creation/open/read-only/transition/restore coverage. **Discard** general migration-policy conflict and forwarding-is-rot inference. |
| A6/A16 (0044/0052/0062–65); F2/F17 | `project_storage/format.py` admits format 11; `video_candidate_transition.py` has two exact predecessor states. Historic format numbers are not current admission instructions. No current writer alone does not prove historic readers deletable. | **Park** folder-generation map and reader population audit; no data reset, schema deletion, or historical text rewrite in A. |
| A7/A8/A10/A15/A16 (0032–34/0038/0040/0049/0050); F25 | `video_backends/minimax_h3/adapter.py` now owns catalog **v6** and qualified `{5:124,8:192}`; `.env.example` has v6, while README, development, and operations instructions needed current-duration correction. [ADR 0050](../adr/0050-unified-h3-generation-contract.md) removed standalone H3 asset/job creation. [ADR 0036](../adr/0036-minimax-h3-profile-catalog.md) already scopes its retained-profile paragraph as V2 history. | **Use A:** repair the live H3 operator instructions, scope 0038/0040/0050 and index the successor chain. **Discard** audit's v4 literal as current and demand to erase 0036 history. **Park** wider profile/version mirror redesign. |
| A11; F5/F6/F9/F10 | `api/project_folder.py` accepts only H3 video; `persistence/project/media_video.py` recognizes old Wan paid-policy requests and refuses them when accounting is absent. `None` is part of fail-closed behavior, not proof of cap bypass. | **Park** provider-policy status/retirement decision; preserve the refusal and identification logic. **Discard** "unenforced allowance"/automatic deletion inference. |
| A12/A16 (0009–29/0053/0059/0063/0064); F18/F23 | Version literals, route reachability, and old cohort prose need individual owner checks. A Chinese UI label need not contain English `Accept and continue`; 0064's 90/90 route timing agrees with depth allocation. | **Park** per-claim semantic audit, not blanket ADR token replacement. **Discard** absent-writer/table conflation, label-as-absent-boundary, and 60s-per-section correction. |
| SIM-01/SIM-02 | `runtime.RunContext.providers` and `ProviderPorts()` still have production and test constructors; `recover_runtime_jobs` has two direct old tests, while active startup has its own reconciliation. No consumer/export/installed-wheel proof yet. | **Test C:** separate, bounded caller/packaging characterization before either removal; preserve provider resolver, artifact context, and live startup recovery. Not approved to edit code in A. |
| SIM-03/SIM-04; F13/F14/F15 | Capability false states still express loading/failure/retry/unsaved behavior. Profile snapshot identity is read in frozen/read-only contexts. `stable_hash` does not itself reject credentials; required/all schema walkers differ; only `allowed_entity_states` is byte-identical. | **Park** initialization and identity-contract design. **Discard** branch-is-dead, hash-has-admission, all-walkers/all-helpers-identical, and demonstrated-ADR-violation inferences. |
| F1/F20/F21 | CI workflow remains manual-dispatch only; existing build/test/wheel gates are real. Lint/build-entrypoint leads require focused baseline and shipped-artifact browser evidence. | **Test B:** narrow tooling proposal. Automatic push/PR triggers remain a separate director decision. **Discard** "bundle build absent" claim. |
| F7/F11/F16/F19/F22/F24/F27 | Unused-looking modules, config, route/UI clones, imports, and `projectIdFromLocation` are static leads; F27 records deliberate non-findings. | **Park** per-symbol consumer and behavior checks; do not combine into a mass deletion or refactor. |
| F26; A1/A16 | `docs/roadmap/README.md` is the current planning entrypoint; the capability matrix is explicitly superseded. | **Use A:** clarify [ADR 0008](../adr/0008-capability-based-adoption-tracking.md) and docs entrypoint. **Discard** archived matrix as current authority. |

Audit amendments govern their original numbered rows: F9's paid-policy guards,
F13's credential-admission distinction, F14's divergent policies, F15's single
identical pair, A10's already-scoped history, A13's three migration mechanisms,
and the N2 row-class-versus-allowlist correction must not be silently reverted.
`Use` rows above do not authorize the audit's proposed code deletions or provider
calls. Re-evaluate all `Test`/`Park` rows against the then-current source before
their own bounded implementation assignment.
