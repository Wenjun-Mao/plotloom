# Owned renderer fork — scoped qualification

Current evaluated-gate pin is4f9b2128, with exact scope and immutable native-report
boundary in the [evaluated-gate receipt](2026-10-09-evaluated-report-gates.md).
Later native Art3 and Board3 qualification are recorded in the
[Board3 receipt](2026-10-09-review-bound-bridge-and-board3-media.md) and
[recovery continuation](2026-10-09-board3-recovery-and-final-qualification.md).
The initial fork/checkpoint below remains historical, not current pending work.

Owner decision: [ADR0147](../adr/0147-owned-pinned-report-renderers.md). The fork
is implemented, independently reviewed and published. Parent integration is a
branch checkpoint; native dependency requalification and combined release gates
remain open. No normal8841 activation is claimed.

## Authority and root causes

Verified `Wenjun-Mao/shuohao-skills` is a fork of
`eternityspring/shuohao-skills`. Published branch `codex/plotloom-report-context`
resolves to `266af294da035324139202235430ffd68f5b877d`, based on the previously
qualified upstream `4322897e6d2bdaf66365534fd40194360c75a85f`. No later breaking
upstream release was adopted. Original LICENSE/NOTICE, file modification notices
and `PLOTLOOM-FORK.md` preserve scope and attribution. The initialized parent
submodule is clean at that exact commit.

- Art validation knew Cast but rendering did not. Current validation, gates and
  rendering share explicit `{ cast, lang }`; Plotloom's style caller supplies
  it. Missing context is reported truthfully, empty supplied Cast is distinct,
  and contamination still refuses rendering. No legacy signature adapter.
- Storyboard reports used hardcoded limits and inferred execution from planning.
  Displayed limits now come from effective frozen parameters. Segment/batch
  counts are planning, not dispatch evidence. The independent reviewer caught
  an unsupported “not dispatched” claim; final copy and bilingual regression
  remove it without inventing a different execution state.
- Outline reports printed raw fractional minutes and clipped KPI values. A
  millisecond-based display formatter handles carry and both languages; values
  wrap. Original JSON, gates and aggregate episode-target meaning remain intact.

## Executed fork checks

Art158, Storyboard254, Outline249, Characters355, Script154, existing combined
report92 and new owned contract72 checks PASS. The final72-check run was also
executed independently after the review finding was fixed. `git diff --check`
passes. The reviewer found no remaining blocking scoped source issues.

Contract checks cover CLI Cast context, missing/empty Cast, language precedence,
prompt/sheet/lighting/prop contamination, unchanged embedded/source JSON,
fractional/carry durations, raw aggregate calculation, alternate12-second and
1–8-second limits, and no fabricated executed/undispatched status in either
language or HTML/Markdown. Intentional fixture segments above the changed cap
still fail their original gate; limits were not weakened.

Desktop exercise:18 combinations (Art/Outline/Storyboard × Chinese/English ×
1700×900,1280×768,1280×460), zero document overflow and zero clipped target KPI
values.30 captures are retained under
`output/playwright/2026-10-09-owned-renderer-fork/` in the retained parent checkout.
The manager directly inspected10 critical top/gate/footer captures, not all30.
Duration/context/planning copy was readable in those frames. Reports were served
from a read-only disposable fixture directory; no private project root was served.
These are renderer fixtures, not native generation or creative acceptance.

## Parent and native boundary — October9,15:36UTC

The parent gitlink, current Art caller, legal notice and workflow docs adopt the
exact published pin. Parent style/context/storage/exchange checks must run after
the parent checkpoint commit because the exchange authenticates `HEAD`'s gitlink,
not an uncommitted index. On committed18a5216, the manager ran current
style/context, Art storage, exchange-pin and review-context diagnostics:
51 Python tests PASS in21.82s (one existing warning). Parent caller/pin paths
were also inspected; a separate additional parent integration reviewer did not
run because native agent capacity was unavailable. The fork's independent
review above is not represented as a separate parent review.

An actual read-only isolated8865 projection after adopting the fork reports
accepted Art r2 stale and accordingly changes Script/Storyboard/production/video
currentness. This is expected hash-contract invalidation, not fresh acceptance.
All42 asset paths/hashes remain exact, eight image jobs are delivered, seven
video jobs ingested, and run/specialist owners are idle. No retained report,
request, approval, media receipt or protected owner data was rebound or rewritten.
Normal8841's JS remains `3a8843193da3df6852f8b12731e33c90961dbe1339a9882b30fb2e03290555d5`.

Fresh Art preparation/review and explicit dependent rebuild are required before
Opening2's native uncertainty authorization/H3 and the rebuilt-route checks.
Historical test totals do not qualify this combined candidate.
