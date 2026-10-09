# Evaluated report gates — scoped E22 correction

The whole Create → Revise → Recover run remains PARTIAL. This checkpoint fixes
report truthfulness and two action-scope copy defects, not creative/media quality.

## Diagnosis and ownership

The actual native Storyboard report for job
`ch_e4a837719ac743a1aa38c876170b4c0f` displayed 17/17 passes even though the
optional recipe-library gate was skipped. `ok` represented nonblocking admission,
not execution. The same abstraction affected Art, Script and Outline reports.
The owning gate builders now provide required boolean `evaluated` metadata;
summary/rows/CLI distinguish executed, passed, failed and skipped. Missing optional
context is skipped, supplied empty context is evaluated, mandatory failures still
block admission. Gate inventory, candidate JSON and admission outcomes are unchanged.
Storyboard duration now explicitly totals all entries, not one playback route.
See ADR0147 for the independently copyable local-helper contract.

The production bridge also incorrectly attributed any action restriction to
project-wide read-only status. Its copy now names the restricted proposal action
and asks the author to check permissions/current review. Script guidance no
longer limits arbitrary current chapters to an opening and endings. Restrictions
themselves were not weakened.

## Published fork and executed checks

Owned fork: `Wenjun-Mao/shuohao-skills`, pin
`4f9b2128c82adf623f594ba714c97d0afcfc16a2`, branch
`codex/plotloom-evaluated-report-gates`. Original legal notices, modified-file
notices and PLOTLOOM-FORK.md retain attribution. No compatibility fallback.

- Five stage selftests PASS: Art159, Script154, Outline249, Characters355,
  Storyboard254; owned renderer72 and evaluated-presentation71 PASS.
- Independent review reproduced these checks, compared sixteen cases with the
  prior fork's inventory/admission/validator outcomes and found no scoped issue.
- Frontend983 PASS across119 files; TypeScript and deterministic build PASS.
- Focused Python65 PASS; subsequently strengthened archive byte/SHA regression
  and its16-test module PASS. Existing Starlette warning only.
- Scoped browser8 PASS: accepted-review currentness and Script/Storyboard
  archived static readers. An earlier command matched only the6 currentness
  cases; it is not represented as report-reader coverage.
- Full Python1463 PASS qualified parent4644870 before this presentation delta.
  It is historical evidence, not a later full-gate claim.

## Actual visual inspection and immutable evidence

Root inspected six corrected pure-render captures, top and quality gates at
1700×900,1280×768,1280×460. All had zero document overflow; the badge and summary
show16/16 executed passes plus1 skipped, with a neutral skipped marker and reason.
The aggregate20-second KPI explicitly says it is not one complete route.
Captures: `/private/tmp/plotloom-evaluated-report.Spb3yv/`.
This is separately rendered QA data, not a substituted frozen delivery or native
execution under the new pin. Only a disposable local report directory was served;
its console had a favicon404, not an application error.

The native delivery remains frozen at fork266af29 and report SHA-256
`8ac6996b83a13a280c525b20ff9b887bd10ee77b246bb6be92f2ef173f30f449`.
Independent pure rendering preserved that hash; the old report's count limitation
remains recorded. A permanent API regression checks archive bytes/SHA before and
after static-reader requests, retaining CSP and the original historical claims.
No old request, receipt, report, accepted binding or media was rewritten.

## Remaining qualification

Fresh parent integration checks and broader current-browser gates are next.
Accepted Art3/Script3 are not assumed stale merely because a report fork changed;
owning currentness must be read before any dependent action. Storyboard acceptance,
explicit production rebuild, native uncertainty review/H3, revised-route playback
and remaining Recover/E22 cases still require execution. Normal8841 and protected
owner projects remain outside this isolated correction.
