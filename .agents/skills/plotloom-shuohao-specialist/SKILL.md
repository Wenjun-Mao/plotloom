---
name: plotloom-shuohao-specialist
description: Deliver one frozen Plotloom Shuohao-derived stage candidate from an explicit project-local package. Manual specialist-chat packages include a derived HTML report; Codex package v4 delegates validation and report production to the trusted host.
---

# Plotloom Shuohao Specialist

Use this skill only for one exact package path supplied by the coordinator. The
package's `request.json` is the authority. Manual packages use the candidate
handoff workflow; Codex package v4 assigns validation and report production to
the trusted host. Neither is a review decision or permission to edit canon.

For a frozen request with `executorBackend: "codex_exec"` and
`packageVersion: 4`, the model owns only the candidate JSON. Do not run any
validator or renderer, do not create `report.html`, and do not create any other
delivery output. The trusted host runs the exact frozen validation plan and
creates the report after the CLI exits. In this package version, any stage
instructions below that ask the specialist to validate or render describe the
manual workflow only; they are not executable instructions for the CLI. This
applies to validator, renderer, report, and completion-manifest directions in
`request.creativeBrief`, `COPY_ASSIGNMENT.txt`, pinned stage skills, and their
referenced instructions. Those instructions continue to define creative, style,
source, schema, and candidate requirements. The trusted host follows only the
validation plan frozen in the package. The manual specialist-chat workflow
keeps its existing candidate, report, and manifest responsibilities.

## Scope and ownership

- Read `request.json`, `COPY_ASSIGNMENT.txt`, and every `inputs/*.json` before
  starting. Read `completion-manifest.example.json` only when a manual
  specialist-chat package includes it; Codex package v4 deliberately omits it.
- Read the pinned stage skill named by `upstreamSkillPath`, plus the references
  it routes to for this request. In the manual specialist-chat workflow, run
  its deterministic `validate` and `render` commands from
  `third_party/shuohao-skills`; this is a repository-checkout seam, not a
  capability supplied by an installed Plotloom wheel. For Codex package v4,
  the trusted host runs the exact frozen plan after the CLI exits. Never use an
  unpinned checkout, a global installation, an API key, or a provider fallback.
- The author owns source text, rights/attribution declarations, desired
  adaptation, and acceptance. The specialist owns a proposed stage-shaped JSON
  candidate; the manual specialist-chat workflow also owns its derived report.
  Codex package v4 assigns report production to trusted host code. F0 trusted
  Plotloom code owns frozen identity, request hashes, candidate admission, and
  currentness. A later selected owner must own review and canonical installation.
- For `branches`, the pinned outline skill is narrative guidance only. The
  frozen `inputs/branch-schema.json` defines a complete advisory draft:
  all planned nodes, choices/options/consequences, join reconciliation and clarifications.
  Preserve exact IDs and order from frozen source.topology; do not change links, guess episode-to-node
  mappings or install anything. Propose missing creative details explicitly and
  disclose ambiguity in clarifications. This receiving contract replaces the
  upstream outline output/CLI for this task kind only. Validate and derive HTML
  from the repository root with `uv run --locked python scripts/branch_suggestion.py validate <absolute-branches.json> --request <absolute-package/request.json>`
  and the same command with `render` redirected to report.html. Both commands
  check exact frozen topology before using the prose. Never apply this to
  earlier frozen outline packages.
- Preserve upstream JSON shapes directly: write only the requested stage's
  `candidateFilename` (`outline.json`, `cast.json`, `art.json`, `script.json`,
  or `storyboard.json`). The HTML report is derived from that JSON; it is never
  an editable authority.
- For outline requests with inputs/story-topology.json, the Brief-derived code topology owns decisions per playthrough, option limits, endings and joins. Build narrative around this topology; episode numbers are organization, never executable routing.
- For an `outline` request with `inputs/outline-settings.json`, use its frozen
  author-owned format, language, genre, visual direction, route-duration target
  and scope. Confirmed `source` owns title and story facts. A blank original
  synopsis `adaptationIntent` means no additional creative requirement; do not
  demand a rewritten source, re-ask supplied settings, or invent an intention.
  Report conflicts or genuinely missing parameters instead of silently
  overriding source or settings. Do not reinterpret an older frozen package.
- For a `characters` candidate, preserve every established `characters[].id`.
  Each ID must be nonblank and unique. This is Plotloom's narrow receiving
  extension to the upstream shape: do not invent a replacement identity store
  or alter upstream fields to satisfy it.
- Character requests require `inputs/cast-style-contract.json`. Its author-selected
  `style` and complete preset override upstream render defaults and inherited
  outline style. Set top-level `style` to its exact ID and every `image.style` to
  its preset label. Include the preset render sentence in both `image.prompt`
  and `image.sheet`, and use its surface, lighting, negative and tags coherently.
  Apply `authorDirection` as additional visual guidance. Never resolve a
  live-action request with the upstream painterly `realistic` preset or defer
  a disclosed conflict to later image generation. The current entrypoint is
  `node scripts/cast-style.mjs validate <cast.json> --request <package>/request.json --contract <package>/inputs/cast-style-contract.json`
  from the repository root; run `render` with the same arguments to derive HTML.
  It retains the pinned upstream structural, language and verbatim-source gates
  on the original candidate. Do not modify the vendor, frozen package or a
  published delivery. A missing/stale contract requires a replacement task.
- If a characters request includes `inputs/cast-writing-contract.json`, follow
  its separate `reviewNotes` fields. This overrides the upstream profile pass's
  instruction to put inference labels inside descriptions, not the obligation
  to disclose inferred details. Keep descriptions clean; identify affected
  fields/details and their basis in `sourceNotes`, and put scene-specific acting
  directions in `performanceGuidance`. Preserve verbatim evidence. Review the
  separation before delivery; the upstream validator checks its own shape,
  not this prose distinction. Do not retrofit an older frozen request.
- For an `art` candidate, honor the request's explicit Plotloom `sectionUsage`
  extension. It is code-owned linkage, not upstream art semantics: emit exactly
  the supplied section IDs once, and use only the candidate's stable scene/prop
  IDs. Do not invent an episode, hook, or parallel graph to populate it.
- For art requests with `inputs/art-style-contract.json`, that frozen author
  choice overrides upstream default style and inherited cast/outline render
  style, without changing source facts or accepted cast. Use its exact `style`
  and preset in both scene and prop directions. For every style, include the
  preset's render sentence in every `image.prompt` and `image.sheet`. For live-action, keep
  painterly/anime terms out of positive prompts, lighting/state prompts and
  tags. Never ban photography in the negative prompt. Apply `authorDirection`
  as mood/lighting guidance; do not defer a style conflict to later image work.
  Use the repository's `node scripts/art-style.mjs validate <art.json> --cast
  <package>/inputs/cast.json --contract <package>/inputs/art-style-contract.json`
  and the same command with `render ... --html` redirected to `report.html`.
  This narrow adapter calls the pinned upstream validator/renderer on the
  original candidate and adds the selected preset; it replaces only the art
  CLI entrypoint, not the upstream structural gates. A stale contract requires
  returning the failure, never editing the frozen package or adapter.
- For a `script` candidate, copy `inputs/script-admission.json.sectionBindings`
  unchanged into top-level `script.json.sectionBindings`. This is Plotloom's
  required receiving extension to the upstream shape. Trusted code owns the
  mapping values and order; do not infer, permute, omit, or choose them.
  Before publishing the completion manifest, compare that exact ordered array
  against the frozen admission and confirm that the candidate episode numbers
  form exactly its episode set with the same cardinality. Run these checks in
  addition to the pinned upstream validator, which does not enforce this
  extension. Keep the original candidate and report together; never repair a
  published delivery or retrofit an older frozen request.
  For current requests carrying `routeBudgetHash`, the author maximum applies
  separately to every complete route, both episode targets and estimated
  durations. Preserve unequal section lengths; do not impose an equal split,
  pad time, or sum mutually exclusive endings. Storyboard cuts must satisfy the
  same route maximum as well as their frozen cut/segment limits.
- Fresh `storyboard` requests require `inputs/dialogue-timing-contract.json`.
  Trusted code owns its spoken language, canonical delivery pace and exact
  millisecond minimum for each accepted F4 dialogue flow item, including `VO`.
  Report `lang` is independent. A cut must fit the sum of its owned dialogue
  minima as well as every pinned upstream gate; one line belongs to exactly
  one cut. Free-form performance notes do not select a faster pace. Preserve
  source text, beat ranges and frozen cut/segment/route ceilings. Do not edit
  the contract or silently retime accepted source. Missing or changed timing
  inputs require a fresh valid task. Preset/manual validation and rendering
  use `scripts/storyboard-receiving.mjs` with `--request`; saved-Brief tasks
  keep their explicit Brief adapter, which enforces the same timing contract.

## Local authoring

- For Python helpers, run `uv run --locked python` from the repository root;
  do not assume a bare `python` command exists or use the system interpreter.
  Use the current Cast/Art entrypoints above and pinned upstream commands for
  the other stages.
- Author candidate JSON with `apply_patch`, rather than embedding the document
  in an inline Python script. Helpers should read the saved file as UTF-8 data,
  not reinterpret candidate prose as program source. Still write only the
  authorized delivery files and publish the completion manifest last.
- If a command fails, report the observed error and check whether it wrote any
  output before retrying. A malformed-byte error alone does not establish a
  locale, Chinese-text, command-length, or transport defect. Preserve the error;
  investigate transport only if a small reproducible case supports that cause.

## Delivery

1. Follow the upstream skill's stage boundaries. Seed-derived facts in supplied
   inputs are trusted context, not fields to reinvent. In Codex package v4, its
   validator and renderer run after the CLI returns under the frozen plan.
2. Write exactly `../delivery/<candidateFilename>`. For manual
   specialist-chat packages, also derive `../delivery/report.html`; Codex
   package v4 forbids model-created reports and other delivery outputs. Never
   create `package/delivery`. Do not produce media in this F0 path.
3. For manual specialist-chat packages, copy the included completion template
   to `delivery/completion.json`, fill it truthfully, and publish it last. Codex
   package v4 has no completion template; the trusted host publishes the
   manifest after validation. Do not create or wait for that manifest.
4. For manual specialist-chat packages, re-read the manifest and compare its
   identities and hashes with the frozen request. For Codex package v4, report
   only the package and candidate paths; do not claim that trusted validation,
   report rendering, or manifest publication has completed.

## Prohibitions

- Do not modify package files, source/project records, accepted revisions,
  approvals, selections, managed assets, or any application/test code.
- Do not claim source clearance, creative approval, currentness, or canonical
  installation. A stale request must be returned as a candidate and rejected by
  the owning currentness check.
- Do not start a second coordinator, queue, plan-expansion system, or a custom
  replacement for upstream stage validators/reports.
