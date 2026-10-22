# Specialist source consolidation into main — 2026-10-22

Status: source consolidation and local cleanup completed. The director reviewed
the qualified candidate, fast-forwarded main to `8603b665`, verified retained
evidence, and removed the specialist worktree and local branch.

## Authority and preserved inputs

Wenjun authorized reconciling the H3/voice/gateway/dashboard specialist source
into main and removing its branch/worktree, explicitly without another owner
confirmation. CI and push stay off. He also made integration-related disk growth
an explicit exception to the director's approximately 90 GB whole-project cap;
needed source/evidence must not be deleted to fit that earlier cap.

The director finished its real creator UI E2E, composite local qualification and
activation before handing off sole source ownership. Pinned main:
`4bb7d6046a0c4f4ec9f7894be2b31b5807e92a90`; specialist parent:
`47df5fb5e19a73831d9e5584cf8e3e8c877af641`. Installed Plotloom remains on
`b21505a0`; this source consolidation does not activate a new runtime. Spark
serving artifacts, models, releases, user projects, credentials, host/accounting
and historical UNKNOWN evidence are outside the write scope.

## Reconciliation

- Merge pinned main into the existing specialist checkout, retaining both full
  ancestries. The director will fast-forward main to the reviewed result; no
  history rewriting or new worktree is needed.
- Preserve main's authoritative extraction-test split, environment-template
  assertions and improved search pruning. Add Lab to the explicit service union
  alongside gateway and creator_workbench in `test_service_source_contract.py`.
  Allow only named top-level local environment/build/cache paths in gateway and
  Lab; reject nested or undeclared hidden files. Creator workbench keeps its
  existing source-only policy.
- Register added native gateway tests, the dashboard fixture and the static
  runtime import guard in the existing test-ownership manifest. The Lab keeps
  its independently locked test environment.
- Preserve main's ADR and roadmap indexes, appending service entries. Renumber
  specialist decisions using the director-reserved block below. Update navigation
  links and specialist numeric references; retain original identifiers in the
  renamed decisions. Experimental results, revisions and historical limitations
  are not reclassified by renumbering.
- Product source, frontend/generated assets, root locks, creator_workbench and
  CI configuration must remain byte-identical to pinned main. Gateway and Lab
  runtime source must remain byte-identical to the deployed specialist source.

| Original specialist ID | Integrated ID | Decision |
| --- | --- | --- |
| 0090 | [0205](../adr/0205-h3-ref2va-per-job-voice-reference.md) | Per-job Ref2VA |
| 0091 | [0206](../adr/0206-spark-voice-lab-candidate-boundary.md) | Lab candidate boundary |
| 0092 | [0207](../adr/0207-voice-lab-projects-and-published-voice-identity.md) | Projects and published identities |
| 0093 | [0208](../adr/0208-voice-lab-observed-job-progress.md) | Observed progress |
| 0094 | [0209](../adr/0209-voice-lab-independent-engines-and-delivery.md) | Independent engines/delivery |
| 0095 | [0210](../adr/0210-h3-runtime-qualification-and-catalog-isolation.md) | Runtime qualification |
| 0096 | [0211](../adr/0211-voice-lab-shared-host-operating-boundary.md) | Shared-host operation |
| 0097 | [0212](../adr/0212-published-voice-performance-takes-and-shared-admission.md) | Published takes/shared lane |
| 0098 | [0213](../adr/0213-h3-video-only-vae-precision.md) | Video-only VAE precision |
| 0099 | [0214](../adr/0214-read-only-gateway-dashboard.md) | Read-only dashboard |
| 0100 | [0215](../adr/0215-h3-dashboard-submission-boundary.md) | Dashboard H3 forwarding |
| Unnumbered | [0216](../adr/0216-media-services-monorepo-boundaries.md) | Independent service maintenance |

## Qualification ownership and scope

The specialist owns one integration check run; independent review inspects the
stable diff and evidence. Reuse the director's unchanged product qualification
and specialist's deployed service/provider/browser evidence. No automatic full
run or new generation is required merely to combine histories. Fresh checks
cover service admission, test ownership, extraction/wheel/H3 transport consumers,
the complete gateway tests, dashboard Node tests and independently locked Lab
tests. Exact selectors are retained in the
[native command manifest](supporting/2026-10-22-specialist-integration-selectors.json).

| Fresh check | Result |
| --- | --- |
| Native `scripts/verify.py focused`, 22 exact Python files | 322 passed, 1 existing Starlette/httpx warning; 22.969 s including collection checks |
| Native module ownership discovery | Passed: 3,923 Python / 1,473 Vitest / 351 Playwright cases; no test bodies executed |
| Independently locked Voice Lab (`uv run --locked --group test pytest -q`, Lab cwd) | 80 passed, 1 existing Starlette/httpx warning |
| Dashboard Node suites (`test_dashboard_ui.mjs`, `test_dashboard_generation_ui.mjs`) | 14 passed |
| Changed-document local-link check | 72 Markdown files / 642 local links checked; no missing targets |
| Diff/identity checks against pinned main and specialist | Protected product/runtime paths unchanged; patch check passes against pinned main |
| Independent stable-diff review (requested GPT-6.1 Sol / Medium; effective settings unverified) | No material code findings; one documented command corrected to include the moved service-admission test |

The focused selection includes the complete gateway Python suite and current
Plotloom H3 transport tests, source/extraction/wheel isolation, the new import
boundary and service guard, and native module-manifest regression tests. The
ownership checker validates all native inventories without claiming all bodies
ran. The native focused extraction test built/probed the current Plotloom wheel.
No additional full product suite, provider trial, browser journey, image rebuild
or serving cutover was run for this history reconciliation. Their unchanged
source/runtime evidence is reused under the director's explicit handoff.

Two operator adjustments preceded qualification: a combined file-read response
exceeded its output limit before any edit, so conflict reconciliation used a
local deterministic rewrite; and checking incoming main changes against the old
specialist parent found existing blank-EOF whitespace on main. Actual integration
whitespace and source identity are checked against pinned main, preserving those
already-qualified files instead of making unrelated edits. Neither adjustment
weakened tests or changed product behavior.

## Disk and cleanup ownership

Read-only baseline: specialist checkout approximately 701 MiB; retained main
checkout 5.1 GiB. Merge preview increased tracked blob bytes from 80,337,305 to
89,007,476 (approximately 8.27 MiB; unresolved index text made that provisional).
Final committed tracked blobs increased from 80,363,729 bytes at pinned main to
89,043,711 bytes at the reviewed candidate: 8,679,982 bytes (8.28 MiB), covered by
the owner's integration exception.

Before supported worktree removal, the director preserves wanted ignored files
privately with hashes: `.local`, `.playwright-cli`, `frontend/test-results`, root
`dist` and Lab `dist`. No additional root `.env`, untracked nonignored files or
runtime symlink coupling was found. Local venvs, node_modules, test/lint caches
and bytecode are rebuildable. All valued branch history must first be an ancestor
of main. Other worktrees, installed P and Spark data are not cleanup targets.

## Director integration and cleanup

The director independently checked clean source ownership, both parent
ancestries, the protected product/service byte comparisons and the final diff.
Main fast-forwarded to `8603b665e0b8e3e3fb7b2956c43834444568b2ae`; merge commit
`752732fb1286ae46daf5f67bfb0867c507831004` retains both the original specialist
history and pinned main. The only subsequent main edit is this closeout record.

All 230 wanted artifact files were copied into the private local directory
`.local/specialist-integration-20261022-preserved/worktree-evidence/`. Every file
passed SHA-256 verification, and a checksum-based rsync comparison found no
differences. The [source manifest](../../.local/specialist-integration-20261022-preserved/source-files.sha256)
hash is `89de01ba9adf46e856d958f9861aad6864814a5dafaf0703a410b9d136391ffb`.
It includes the [focused check log](../../.local/specialist-integration-20261022-preserved/worktree-evidence/.local/specialist-integration-focused.log),
browser captures and build outputs. No extra credentials or symlinked artifacts
were found. The specialist froze all files and stopped its owned test sessions;
the director confirmed no process used the checkout before removal.

Supported `git worktree remove --force` removed the exact specialist checkout at
`/Users/wjmao/projects/HU/plotloom-h3-ref2va-gateway`. The fully merged local branch
`codex/h3-ref2va-gateway` was then deleted; its history remains reachable through
main. Both worktree registration and local branch absence were verified. Remote
refs were unchanged. Rebuildable environments/caches were discarded; retained
source and copied evidence remain recoverable. The removed checkout occupied
762,972 KiB and the preserved evidence directory occupied 213,656 KiB at that
boundary, a 536 MiB allocation reduction before accounting for main's source
growth. This is allocated-file accounting, not a filesystem free-space guarantee.

Installed P remains clean at `b21505a0`, with the same healthy container
`181d239fb9e2` and bridge PID 66847. All three health routes returned ok.
The [post-cleanup state comparison](../../.local/specialist-integration-20261022-preserved/after-cleanup-state.json)
against the post-activation baseline found exact preservation of all four
projects, settings, host/accounting and UNKNOWN records, with no controller-claim
changes. No service restart, provider call, CI or push occurred during source
integration or cleanup.
