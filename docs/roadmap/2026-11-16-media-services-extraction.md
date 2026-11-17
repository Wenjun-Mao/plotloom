# Independently maintained media services, with Plotloom as an HTTP consumer

## Current status

Updated: 2026-11-16. Owner: this extraction director, sole source writer with read-only support/review. Baseline: local Plotloom `cd11f2c6`, including optional-audio `f251e6b4`; extracted source `85a964ff` with original history mapping retained. Result: independent complete service suites and installed gateway/dashboard smokes pass; actual Plotloom HTTP submit/poll/download/401/UNKNOWN journey passes; local source/manual ownership handoff prepared. Blocker: public Plotloom publication scope awaits Wenjun’s choice because origin/main is 158 older commits behind. Next action: final local qualification, image/browser/wheel proof and private-repository publication/fresh-clone proof; hold only the affected public push. Stop when all acceptance rows and scoped cleanup are complete. Forecast remains 4–7 hours, not a cap.

Preserve the preexisting tracked edits in `docs/roadmap/README.md` and the Shuohao cross-framework replication plan, plus untracked story/generated assets. Production state has not been changed. Source extraction is now in progress in the separate candidate checkout.

## Acceptance

| Claim | Required evidence | Fresh media | Status / evidence |
|---|---|---|---|
| Independent backend source home | Private `Wenjun-Mao/media-services`; qualified remote revision; gateway, dashboard and Voice Lab install/test/build from a fresh remote clone without Plotloom source/environment or author-shell `PYTHONPATH` | No | Planned; no repository created |
| Current implementation and relevant history survive | Current/historical path manifest; runtime-file hash comparison to the frozen local revision with intentional changes explained; filtered commit map and representative pre/post-rename history; optional 0–3 reference-audio implementation present | No | Baseline includes `f251e6b4`; extraction proof pending |
| Services and consumer still work | Provider-free API/persistence/dashboard journeys; shared lane/restart/UNKNOWN/retention checks; installed-artifact smokes; affected complete final-request comparisons; real Plotloom HTTP adapter against the installed extracted gateway for submission/polling/fixture-result retrieval and applicable error/uncertain-outcome handling | No by default | Reuse prior live evidence only for unchanged inputs; actual new-root consumer/service integration proof pending |
| Ownership is handed over | Old authoritative gateway/Lab source and backend-only tests retired in Plotloom; useful consumer tests/selectors retained; published pointers identify the new owner; maintained tools need no sibling Plotloom service checkout | No | A second repository alone is insufficient |
| Colleagues retain service use and instructions | Existing URLs/auth workflow preserved; existing H3/Qwen guide URLs accessible; Voice Lab/take guide accessible in the existing manuals too; links/examples checked without private-repo access | No | Colleagues are service users, not source collaborators; no invitations |
| Runtime and valued state survive | Source-only operations leave serving artifacts, databases, queues, published voices/takes, retained media, inference environments and weights unchanged; any demonstrated serving/source-path dependency has a scoped correction and preservation/readback evidence | No | No deployment assumed necessary |
| Publication and cleanup complete | Scoped checkpoints and published revisions in both repos; private visibility confirmed; no secrets/models/runtime data in extracted history/builds; no CI triggered; task-owned disposable resources cleaned after retaining useful evidence | No | Current Plotloom workflow is manual-only; recheck before publication |

## Agreed direction

The gateway has grown into a shared media backend, making a separate source repository useful. Wenjun selected:

- Move the gateway and dashboard together, and include Voice Lab.
- Name the repository `media-services`.
- Use a private GitHub repository under `Wenjun-Mao`: `Wenjun-Mao/media-services`.
- Use the proposed local checkout `/Users/wjmao/projects/HU/media-services`, beside Plotloom.
- Keep source access private to Wenjun. His real colleagues only use the running service; their usage guides must remain accessible without the private repository. This later clarification supersedes the brainstorm's proposed colleague source access.
- Carry forward the earlier proposal to preserve relevant Git history and leave Plotloom with its client integration.

The intended benefit is clear backend ownership and independent maintenance, testing and releases. Plotloom and direct internal API users remain consumers of the same working services.

## Source-backed starting point

The design starts from local main `f251e6b4`, which contains the implemented optional reference-audio endpoint. Later planning must refresh the source identity and preserve any intervening work. Local history matters: unpublished local changes must not be lost by starting solely from a GitHub clone.

The earlier [ADR 0216](../adr/0216-media-services-monorepo-boundaries.md) kept the services in Plotloom while strengthening package/build ownership. It anticipated eventual extraction of the media-services subsystem together. The new user direction changes repository ownership; the established runtime boundaries remain useful. [ADR 0212](../adr/0212-published-voice-performance-takes-and-shared-admission.md) owns shared admission, and the [operations map](../operations/media-services.md) describes the current deployments.

Current facts:

- Gateway and dashboard already have one service-owned Python package/lock and separate entrypoints/images. The dashboard reads gateway SQLite/output files directly in read-only mode, so they belong in the same source project.
- Voice Lab has its own package, lock, database and engine environments. Production runtime communication with the gateway is authenticated HTTP in both directions; neither imports the other's Python runtime.
- The gateway owns the single managed generation lane for H3, Qwen image and Voice Lab work. Source separation must preserve that execution ownership and uncertainty handling.
- Joint Voice Lab tests and operator tools do use sibling gateway source paths and inspect both services' state. Moving the services together keeps that qualification work with its owning subsystem.
- Some gateway tests, backend manuals, ADRs and deployment tooling currently live outside the gateway subtree. A directory-only copy would miss part of the maintained product.
- Plotloom's H3 adapter owns its client catalog/HTTP transport, not gateway or inference storage.
- Plotloom's GitHub repository is currently public. Its visibility stays unchanged. Existing colleague-facing manuals remain accessible there; private source/operator docs belong in the new repository.
- The proposed local destination does not exist. A read-only GitHub lookup for the target returned404; availability and account access must be checked again before creation.

## Approaches considered

| Boundary | Benefit | Cost / consequence |
|---|---|---|
| Gateway and dashboard only | Smaller first extraction | Voice Lab and shared queue/restart tests remain split across source repositories |
| Gateway, dashboard and Voice Lab together | Backend protocols, joint tests and operations stay under one source owner | More source/documentation paths must be assigned to the new repository |

Wenjun chose the second boundary. This remains a repository containing distinct services, packages and inference environments.

## Proposed ownership map

| Home | Contents |
|---|---|
| `media-services` | Gateway, dashboard, Voice Lab; owned H3/Comfy and Qwen integration code; deployment/install recipes and pinned manifests; service and joint-contract tests; canonical developer/operator manuals; relevant technical decisions and verification records |
| Plotloom | Authoring application/UI, story assets, creative policies and application-specific skills; its HTTP adapters, consumer tests and concise integration note; accessible colleague-facing service usage guides |
| External runtime/storage | Running databases, published voices/takes, generated videos/images, credentials, inference environments, model weights and retained large QA/research media |

All model weights remain under `/home/wjmao/models`. Existing data lifecycles remain distinct: transient gateway deliveries/inputs versus durable Voice Lab identities and takes.

## Proposed technical defaults

These are engineering recommendations, not additional user-specified requirements:

1. Make the first extraction a source-ownership and path correction. Preserve working API URLs/contracts, package/entrypoint names, model/runtime versions and service/storage locations. Source references in maintained tools will need correction; a storage or deployment redesign is outside this slice.
2. Initially retain the existing service directory names and independent locks. A possible layout is:

   ```text
   media-services/
     services/minimax_h3_gateway/
     services/qwen3_tts_voice_lab/
     tests/
     docs/
   ```

   The plan can choose exact test/doc placement while preserving clear owners and runnable commands. No single shared inference environment is proposed.
3. Give source and implementation/operator manuals one canonical home in the private repo. Keep colleague usage guides in the existing Plotloom manual hierarchy, with their H3/Qwen URLs preserved; the private README links back to them. Each manual has one canonical copy. A private link must not be the only instructions available to a service user.
4. Keep Plotloom's runtime integration over HTTP. Avoid a permanent vendored service copy, cross-repository Python imports or a new shared SDK merely to support extraction. The implementer can choose ordinary local development tooling within this boundary.
5. Preserve relevant source history for the moved files and record their relationship to the Plotloom baseline. Keep historical evidence truthful; update maintained commands rather than rewriting old receipts to claim they used new paths.
6. Give the new repository service-owned verification and release instructions. It should be possible to install, test and build its services from a clean checkout without Plotloom source or dependencies. Keep shared FIFO/restart/UNKNOWN and private dashboard-schema contracts covered together. Plotloom continues to verify its own adapter compatibility when affected contracts change.
7. Retire the old authoritative service source in Plotloom as part of the eventual verified extraction, so the repositories have unambiguous ownership. Avoid maintaining two active source copies.

## What success means

- The owner can clone/install/build/test the backend independently using its own locks and documentation; colleagues keep using the service without source access.
- Backend work can be maintained and released from `media-services`, with compatibility checks for actual consumers.
- Plotloom consumes the existing service interfaces, and direct API users retain their documented workflow.
- Shared generation admission, state ownership, voice/take retention and protected unknown outcomes retain their current semantics.
- Relevant history, the latest optional-audio work and current user-valued assets survive the move.

Voice-identity/continuity listening from the optional-audio qualification remains separately unassessed. This extraction does not resume the caption investigation or add a media-quality experiment.

The retained workbench runtime at `/Users/wjmao/Library/Application Support/Plotloom/creator-runtime/plotloom` stays untouched. Historical backend files inside this deployed snapshot are not another maintained source owner. The separate client-IP logging activation remains pending; keep Tailnet stopped and do not bundle a workbench restart into extraction. Plotloom need not gain ordered-image or voice-reference application features as part of moving their backend implementation.

## Concrete ownership and historical paths

At `9ed6a194`, the service prefixes contain 173 tracked files: 102 gateway/dashboard and 71 Voice Lab. Gateway has 26 additional root-level test/support files; Lab already has 14 test/fixture files within its prefix. Counts help inventory completeness; they do not justify omitting newly discovered owned files.

| Disposition | Paths and responsibilities |
|---|---|
| Move implementation | `services/minimax_h3_gateway/`, `services/qwen3_tts_voice_lab/`: packages, workflows/static resources, locks/manifests, deployment recipes, tools and owned tests; keep colleague guides accessible as below |
| Move gateway tests | Entire `tests/services/minimax_h3_gateway/`, including conftest/browser fixture, Node UI, shared FIFO/restart, dashboard-schema and voice-take contracts |
| Move operator/developer documents | Full H3/Qwen operator manuals in `docs/operations/`; detailed backend release content from `docs/operations/media-services.md`; service-local setup/operations docs; selected backend ADRs and qualification receipts |
| Retain accessible client manuals | Existing `docs/operations/minimax-h3-gateway-client-guide.md` and `qwen-image-gateway-client-guide.md`; relocate `services/qwen3_tts_voice_lab/docs/voice-takes-client-guide.md` into Plotloom's `docs/operations/` and repair inbound links. Preserve any other colleague-facing Lab workflow instructions there too |
| Keep Plotloom implementation | `src/plotloom/video_backends/minimax_h3/`, consumer tests/catalog fixtures, app/UI/story assets/creative policy/application skills, and `services/creator_workbench/` |
| Adapt Plotloom guards/tooling | `tests/test_media_service_boundaries.py`, `tests/test_service_source_contract.py`, `scripts/testing/module-ownership.json`, `scripts/testing/python_suite_timings.json`; retain actual consumer coverage and remove stale backend-owner selectors |
| Update maintained entrypoints | Root README, docs/operations indexes, concise media-services integration note and application guidance. Coordinate an already-dirty index with its owner before scoped edits |

Known source couplings include Lab `tests/fixtures/shared_lane.py` and `tools/prepare_shared_cutover.py`, and gateway VAE adoption/deploy tools deriving build paths from the repository root. Joint operator tools may inspect both service databases under existing authority but must not need Plotloom source. Keep the dashboard's read-only gateway SQLite/output relationship explicit and tested.

Audit all owned trees and maintained inbound references, not only these examples. Root Python/frontend manifests showed no local service-package dependency. Implementation fixtures move with their owner; retain consumer-owned fakes/contracts needed by Plotloom.

The history manifest must include:

- Gateway's earlier `src/plotloom/h3_gateway/`, introduced at `6893b954`, moved to its service package at `fae60b2a`.
- Earlier `tests/test_h3_gateway.py`, now `tests/services/minimax_h3_gateway/test_app.py`.
- Voice Lab's current prefix, introduced at `d59c40cf`; no earlier source-directory alias found.
- Selected backend ADRs: current 0033, 0039, 0072, 0073 and 0205–0215. Current 0205–0215 were formerly numbered 0090–0100 in the service branch before integration; include their exact old paths when filtering. Current 0216 originated as `docs/adr/media-services-monorepo-boundaries.md`.
- Historical aliases of selected backend documents/receipts, checked against actual history. Keep relevant failed results/limitations truthful. Do not include all application files merely because a mixed commit touched both owners.

Keep consumer aliases `src/plotloom/minimax_h3_transport.py` and `tests/test_minimax_h3_transport.py` with Plotloom. Shared ADR 0035's consumer boundary and ADR 0095's creator-workbench ownership remain represented there; preserve/supersede the historical monorepo decision rather than rewriting it. Select root documents explicitly using current contracts and README links. Shared decisions can be referenced rather than duplicated maintained prose. This record remains the coordination plan in Plotloom.

## Execution sequence

1. **Freeze and coordinate.** After execution approval, refresh HEAD, dirty state, remote divergence and destination availability. Coordinate a stable source window with the Plotloom director. Preserve intervening work and unpublished local commits; a remote-only clone can omit the current implementation. Record the committed source identity and owned paths. Never broadly stage untracked/story assets. Resolve actual concurrent-edit overlap while independent work continues.

2. **Extract history in isolation.** Use an isolated local `git-filter-repo` installation if needed; it is not installed in preflight. Fresh-clone the frozen **local** source with `--no-local` and filter only that disposable clone, including historical aliases. Retain original-to-filtered commit mapping, representative history checks and current-file comparisons. Never filter the retained checkout or force-push Plotloom. Inspect selected current files and historical objects for secrets, private runtime configuration, model/media artifacts and unrelated content before publication; handle actual credential findings under existing rules.

3. **Prove an independent slice early.** Use candidate-owned locked CPU environments, fake providers and temporary SQLite/media state for an API submit/poll/dashboard-read journey. Unexpected live dispatch must fail. Build/install gateway/dashboard non-editably and run existing packaging smokes from a temporary cwd without source `PYTHONPATH`. Check packaged workflows/static resources and viewer non-mutation. Fix actual path/resource gaps in their new owner, then repeat the affected clean-context journey before broad qualification.

4. **Finish source/test/operator ownership.** Correct sibling fixtures, import/build roots and docs; preserve independent locks and engine environments. Move gateway tests and adapt existing service commands into a normal top-level README and concise backend verification/AGENTS instructions instead of copying Plotloom's full application runner. Carry appropriate license/attribution metadata. Keep build contexts service-owned and compare moved runtime resources to baseline. Avoid unrelated refactors; evaluate responsibilities before substantial edits above 400 source lines and prefer a cohesive extraction when adding responsibility above 500.

5. **Prepare the Plotloom handoff.** Keep HTTP adapter/catalog and actual consumer tests. Reframe Plotloom guards for remaining ownership and absence of backend dependencies; move backend import guards with their source. Update selectors/timings/fixtures without silently dropping application checks. Preserve H3/Qwen guide URLs, relocate the Lab take guide into existing manuals and repair inbound links. Give each manual one home. Correct maintained source/build references; retain immutable artifact paths and historical receipts truthfully.

6. **Qualify and review the stable candidate.** One execution owner runs the checks below; an independent reviewer inspects the stable diff, manifest and evidence. Continue covered repairs after internal review without another user sign-off. Diagnose failures and rerun failed/downstream affected checks, reusing unchanged evidence. Repeat full qualification only for invalidated inputs or a diagnosed failure requiring it; never weaken assertions.

7. **Publish the new owner, then retire old source.** Confirm the target is absent or demonstrably task-owned; never overwrite an unexpected repo. Create the private owner-only repository and publish qualified history. Verify privacy/remote revision, then run normal documented service test/install/build and shared-service journeys from a fresh **remote** clone without Plotloom source/environment. After that proof, publish Plotloom's scoped source retirement and pointers through a reconciled fast-forward that does not trigger CI. Its removal candidate may be prepared/tested earlier. Both published revisions and accessible client manuals are required for complete handoff; no force-push.

8. **Complete references and cleanup.** Confirm maintenance commands use the new source and colleague entrypoints remain valid. Do not restart independent installed artifacts merely to change source ownership. If an actual serving/source-path dependency is demonstrated, record the affected row and use the existing coordinated release procedure for the smallest correction with preservation/readback evidence. Keep one worker per role; never clear UNKNOWN or cancel colleagues' jobs to pass a check. Retain useful history maps/manifests/receipts, then clean only task-owned disposable clones, environments, test state and build buffers. Finish scoped checkpoints and update this record with evidence/limits.

The [GitHub split-repository guidance](https://docs.github.com/en/get-started/using-git/splitting-a-subfolder-out-into-a-new-repository) and [git-filter-repo documentation](https://github.com/newren/git-filter-repo/blob/main/Documentation/git-filter-repo.txt) support isolated filtering. Path filtering does not automatically follow renames. Filtered commits receive new identities, related by the retained mapping.

## Verification

Adapt existing tooling rather than create a new framework:

- Gateway: service-owned `uv sync --project services/minimax_h3_gateway --locked --extra gateway --group test --no-editable`, complete service pytest with its conftest boundary, Node dashboard UI tests and a browser/API/SQLite read-only journey using retained fixtures.
- Artifacts: existing `tools/packaging/verify_install.sh`/isolated role smokes from temporary cwd; independent service-context gateway/dashboard image builds and smokes. Preserve qualified Python patch versions. Reuse prior image proof only if actual build inputs are unchanged; report architecture differences. Building is separate from deployment.
- Voice Lab: its own `uv sync --locked --group test`, full pytest and wheel build; isolated CPU wheel/entrypoint/resource proof with inference disabled/faked. Run existing shared FIFO, gateway-first/Lab-first restart, typed voice/take HTTP and state-preservation fixtures from the new root. Keep inference dependencies out of gateway/dashboard environments.
- Final-request fidelity: existing complete graph/resource comparisons for optional 0–3 audio references and 1–9 images, including image-only omission. Reuse [optional-audio live qualification](../verification/2026-11-16-h3-optional-reference-audio.md) only for unchanged inputs; label new-root fake/replayed proof honestly.
- Plotloom: focused adapter/transport and revised ownership guards first; inspect actual module selections through the existing runner. Run `uv run --locked --no-sync python scripts/verify.py full` once on the stable retirement candidate because root source/test ownership and verification tooling change. The prior full attempt took about an hour and needed targeted repairs; preserve actual failures and apply evidence-reuse rules. Hosted CI is neither required nor authorized.
- Consumer/service integration: on the stable Plotloom retirement candidate, connect its actual HTTP adapter/transport to the actual gateway installed from the qualified extracted revision. Submit a currently supported Plotloom request, poll and retrieve a retained fixture result; exercise applicable typed-error and uncertain-outcome behavior. Fake only inference/provider execution, using temporary state. Separate fake-consumer or service-only tests do not establish this claim. Repeat the affected journey after a repair; this adds no new API feature, GPU generation or deployment.
- Fresh remote clone: follow normal README commands without sibling mounts or author-only imports. If repaired, repeat the affected journey from a clean environment. A fresh native context can follow the docs; no separate human colleague onboarding trial is required.
- Manual access: resolve maintained local/published cross-repository links and check usage guides without private-repo authentication. Private operator/source docs can use Wenjun's credentials; never record bearer tokens.

Record command scope, source, platform/environment and results. Component tests alone do not prove consumer compatibility; health checks do not prove native provider or creative acceptance. If fresh generation is genuinely needed, first name the blocked acceptance row, why retained proof cannot answer it, changed inputs and expected information, then apply existing authority. No new experiment is scheduled.

## Permissions and ordinary decisions

Covered now: read-only inspection, this plan, internal factfinding/two planning reviews, and explicitly requested contact with the existing Plotloom director **after** reviews. Planning alone does not authorize source/runtime migration.

**Execution authorized:** Wenjun’s subsequent ‘Go’ covers this reviewed extraction: isolated local tooling/clones, scoped edits/tests/commits, private repository creation/publication, compatible Plotloom retirement/pointer publication and task-owned temporary cleanup. Ordinary in-scope placement decisions, internal reviews, repairs and safe integration steps need no repeated approval.

The CI-off instruction remains. Current local and remote Plotloom workflow accepts only `workflow_dispatch`; Actions being enabled does not itself make a push start a run. Recheck actual remote events/automation/rules immediately before publication in both repositories. Do not dispatch CI, copy the application workflow into the new repo, change settings/add skip markers or prepare CI changes. If a concrete publication would trigger CI, hold only that push and bring the exact action/revision to Wenjun. Do not call remote handoff complete while old source remains authoritative remotely.

No public exposure, visibility change, collaborator invitation, model/data relocation, API redesign, inference upgrade, destructive production cleanup or resumed caption study is included. Material changes to outcome/risk/authority go back to Wenjun; native confirmations still apply. Source-path blockers do not authorize unrelated infrastructure work.

## Estimate, review points and recovery

Forecast: **4–7 hours of execution**, including mapping/extraction/manuals, service/consumer checks, review fixes, final qualification, publication/fresh-clone proof and cleanup. Existing locked environments and Docker are assumed usable; no serving-path defect or new GPU generation is scheduled. The roughly one-hour Plotloom full gate is included. Waiting on other writers, network/authentication or a user decision is additional external waiting. This is a forecast, not a deadline or time cap.

Review direction after the independent installed/API slice and before retiring Plotloom source. Bring review forward for missing history, hidden Plotloom dependencies, live-state coupling or an apparent API/deployment redesign. Direct owns implementation review once authorized; these checkpoints are internal steps, not routine user approval gates.

Until publication, the isolated candidate is disposable and original Plotloom history remains intact. Preserve mapping/evidence before cleaning clones. Repair forward or revert only task-owned commits on failure; do not reset unrelated work or rewrite published history. Existing serving artifacts remain the operational recovery point. If a necessary runtime correction is demonstrated, follow the existing [release/rollback procedure](../operations/media-services.md), checking actual queued/running/uncertain work at cutover. No second worker or storage migration for convenience.

## Planning reviews and director alignment

1. Outcome/completeness: independent read-only **GPT-6.1 Terra / Xhigh**, following Wenjun's review preference. Challenge an all-checks-pass-but-goal-fails case and actionable execution gaps. Resolve justified findings before review 2.
2. Avoidable restrictions: separate fresh-context read-only **GPT-6.1 Terra / Medium**. Check invented gates, repeated permissions, artificial ceilings and ordinary decisions unnecessarily left to the user. Preserve real evidence/user/native constraints. Send material success/evidence changes back to reviewer 1.
3. Then contact the existing Plotloom director (`01a1902a-80b6-7d80-a166-9c980850982f`) with the reviewed plan and exact revision for source/consumer/manual/deploy-reference alignment and overlapping work. This is coordination, not implementation authorization. Incorporate factual corrections and recheck material changes; record the actual response.

Review 1 found a missing explicit connection between the real Plotloom transport and the installed extracted gateway: independent fixture suites could pass while their actual HTTP contracts disagreed. The acceptance row and verification now require that provider-free submission/poll/result journey, including applicable error/uncertain handling, on the stable candidate. The reviewer rechecked the correction on content SHA-256 `3246fa54d1da7dc8b890335e2919bf4eea8fcbb25e7f4b3ff480ba10171f80f0` and found no remaining outcome/completeness gap. Review 2 independently examined that corrected version and reported no actionable avoidable restrictions; it retained the evidence and real user/operational constraints.

The Plotloom director reviewed content SHA-256 `6d1c82be7049c7a7f44976a5db490e687941555bf091bfe64720841c229374d1` and confirmed alignment, with no missing consumer contract or additional blocker. Their factual clarifications are included above: preserve the retained workbench runtime and separate pending activation; do not add application features merely for extraction. Preserve unrelated dirty roadmap hunks; a scoped extraction pointer is acceptable during authorized execution. The H3 replication-plan needs no extraction edit. That chat reported no active source edits or Spark reservation, which does not establish global idleness; recheck actual state before any necessary cutover. Coordination was read-only. Planning does not start Direct or a native Goal.


## Execution checkpoint

Wenjun approved execution with ‘Go’. The retained source was frozen at `cd11f2c6`. An expanded explicit history manifest preserves current/renamed service paths and directly relevant historical receipts; the current package/runtime files are unchanged. Source histories were filtered only in disposable clones. Client manuals have accessible Plotloom homes; canonical developer/operator instructions are in the new repository.

Executed locally: 343 gateway tests, 80 Voice Lab tests, 25 new-owner guards, 15 dashboard Node UI tests, 70 Plotloom consumer/ownership checks and 19 extraction/module-ownership checks passed. Early installed gateway/dashboard wheel smokes ran outside the checkout with zero generation. The actual HTTP consumer journey passed submit/poll/exact 442,497-byte download, 401 and preserved UNKNOWN without retry; retained MP4 SHA-256 `0a32548a3f40437f17a5e39a5734437a662c30a59467b85beaf6220fb0c43e7b`. Setup repairs are recorded under `.local/media-services-extraction-20261116/harness-repairs.json`; assertions were not weakened and the repaired journey ran from fresh temporary state. Provider generation was faked; this is not new native-generation or creative-quality evidence.

A Terra/Medium implementation checkpoint found two stale new-owner maintenance commands (old Plotloom checkout wording and a custom-node test command). Both were corrected. Current maintained local documentation links resolve. Selected history inspection covered 748 blobs, with no model/media/database path, object over 5 MiB or credential-shaped value found. Final gates and publication are still pending; these checkpoints alone do not establish complete handoff.

Remote preflight found public Plotloom `origin/main` at `9de44e18` (2026-10-27), 158 commits behind the frozen local baseline, including unrelated app/story work. Wenjun was asked whether to publish only extraction changes against that remote or all pending local history; no answer is assumed. Private backend publication and local qualification remain authorized independently. CI remains off.
