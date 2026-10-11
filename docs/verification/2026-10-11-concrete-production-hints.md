# Concrete production hints

Qualified candidate: the main commit containing this receipt, against trusted
`927d441eb647804d4202aeeabffd487b02b9867b`. Contract: ADR 0155.

The owner needs clickable control names, not only the stage name
`制作与审阅`. Keep the graph-node/Production-tab entry stable across the small
tab switch. Name the left-side `剧本` entry when no current usable script exists;
after script/storyboard confirmation, name the return to `创作工作台`, reopening
`制作`, and `分镜与投产整包评审`. The prerequisites remain conditional: canonical
stage heads do not prove accepted script/storyboard currentness.

Actual diff review: one advisory wording expression, regression assertions,
ADR/receipt, and regenerated `workbench.js`. No changed API, request payloads,
backend, persistence, admission, auth, provider/prompt behavior, dependencies,
build tooling or package contract. Use risk-scoped frontend qualification;
unchanged backend evidence is reused, not described as freshly rerun.

- Final `quick`: 1,128 tests in 137 files, frontend/E2E type checks, locked
  dependencies and API unused-import check passed in 13.398s.
- Final `focused`: 55 unit/component cases in recommended-workflow and
  workspace-workflow-guide, plus all 3 recommended-workflow-guide browser cases,
  passed in 22.064s. The browser follows Script → Creator → Production →
  package review, preserving node selection, source/admission and empty runs.
  It retains both-view geometry at 1280×460, 1280×768 and 1700×900, dirty/pending
  edit precedence and guarded navigation. Desktop screenshots were inspected.
- Two deterministic builds produced an identical seven-file sorted path/hash
  tree: `7010b8a4f4aaede3fa6583f7f907c10667119ec4b6afba628ec9b194b9317d7a`.
  `workbench.js`: `1a5e9311b8e8c04f159dff9240d49ff2b897949965f62d8775538d7eb574d918`.
- Independent read-only review is clear after adding the return/reopen path and
  clarifying current usable script versus retained acceptance. An initial test
  compared visible text with text including closed details; the corrected
  assertion compares the actual next-hint region. No product bypass or weakened
  layout/currentness assertions were introduced.

No full Python suite, unfiltered browser suite or new hosted run was launched
for this wording-only follow-up. Required combined-candidate hosted qualification
remains with the isolated M0–M5 owner; run 38109502813 covers the prior baseline,
not this refinement. Normal8841, Safari and the owner project were not operated.
