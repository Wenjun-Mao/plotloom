# ADR 0126: Static reading of archived Script, Art, Storyboard and Cast reports

Status: Accepted, 2026-10-07.

## Problem and ownership

F4's pinned upstream renderer clips scene content at300px and relies on scripts
for Show-all, copy and JSON export. Plotloom deliberately blocks those scripts
with both iframe sandbox and HTTP CSP. Actual Show-all clicks were inert; long
reports can therefore conceal content. This mismatch belongs to the report
reading contract, rather than scene JSON or provider generation.

## Decision

The host explicitly requests `report?presentation=static` and labels it a static
reading view. A presentation-only stylesheet applies the pinned renderer's own
print content semantics: fully reveal scenes and cast line books, suppress
script-dependent Show-all/copy/export controls. This is full static disclosure,
not working interactive buttons. It also suppresses the current
`sec-script`/`sec-cast` header notes that
promise clipping/expansion or six-row scrolling. Other duration/data notes remain.
The current F4 renderer has no tabs/hidden panes;
its five sections are always present. Product-owned current JSON/scene readers
and separate acceptance controls remain authoritative.

The endpoint's default `presentation=archive` retains its existing archived
report response. Stored delivery/report bytes and hashes are untouched; the
static response intentionally adds owned CSS and is not byte-identical archive
evidence. Existing accepted-report revision warnings remain in both projections.
No script or origin permission is granted. CSP remains sandbox/default-none,
inline styles/data images only; referrers are suppressed in the host.

## Alternatives and guardrails

Reject granting arbitrary archived scripts, persisting rewritten reports,
frontend omission of unreadable evidence and changing the pinned generation
renderer. A generation change would disturb the frozen execution contract and
would leave retained reports broken. This narrow projection is tied to the
current pinned F4 template; a future renderer change must update its reading
contract and regressions rather than accumulating compatibility selectors.

Tests cover long scenes/line books, all five sections, absence of actionable
scripted controls, unchanged archive response and persisted bytes, CSP/sandbox,
blocked inline script/network/parent mutation and disclosure reopen. Live pixels
and original report actions are separately qualified in the E2E ledger.

## Demonstrated Art report instance

An actual original F3A Copy click also had no effect under its intentionally empty
sandbox. Apply the same explicit static/archive query contract to Art. Hide the
pinned `.copy`/`.expo` and script-only lightbox, reveal prompt disclosures using
the renderer's print semantics and initially open native `.pr` details. Native
details remain usable for ordinary collapse/reopen. Script-only `.zoom` buttons
are disabled with their images/content preserved; host report enlargement and
asset-gallery zoom remain separate working controls.

A small HTML parser records only the exact owned start-tag offsets to add native
`open`/`disabled` attributes. It leaves every other archive byte, comment, escape,
script body and image unchanged in the presentation before appending CSS. No
historical selectors, document rewrite, stored mutation or script permission is
introduced. The host summary/title explicitly identify static reading. Regressions
cover actual pinned Art templates, retained text/images and native disclosures,
disabled script-only image zoom, host dialog close/Escape/focus and archive hashes.

## Demonstrated Storyboard report instance

Actual retained F5 Show-all and Copy clicks were also inert; its segment area
stayed clipped at760px. Extend the same named static/archive projection to the
current pinned Storyboard template. Its five sections have no script-switched
tabs or native prompt disclosures: cut-frame placeholders already show every
missing image's prompt, and H3 prompts are visible text with internal scrolling.
Reveal all segment cards and full H3 prompt text, suppress Show-all/copy/export
and lightbox, and remove zoom cursors from retained frame/subframe/batch images.
Preserve image tags/URIs and the existing data-only image CSP; no relative image
resource permission or new media is granted. Native segment anchors and host
disclosure close/reopen remain usable. Current structured review/acceptance is
unchanged. Genuine pinned long-segment/prompt/image-branch regressions remain
separate from live provider evidence and test archived hashes/security.

### Host-owned Storyboard enlargement (2026-10-11)

The owner found the rich original Storyboard report more useful than the
structured disclosure, and its generic 320px iframe too small. Put the original
report first, retain structured review beneath it, and offer the same large
native reading dialog as Art. The expandable static reader uses a 72dvh inline
preview and the existing 94dvh dialog; Script's existing inline reader is
unchanged. Guidance names the report and its actual enlargement control first.

Both views admit the same frozen static report URL through `ProjectReportFrame`,
with empty sandbox and no referrer. They do not grant archive scripts, navigate
to an unrestricted standalone report, alter stored bytes or accept a candidate.
Close/Escape restore focus; changing the frozen report or leaving its workflow
closes the dialog without restoring focus into a hidden workflow. Guard placement,
desktop geometry, long-content reading, no writes, archive hashes and isolation
in the existing report regressions.

### Static Storyboard summary sizing (2026-10-18)

Ubuntu Chromium reproduced the dialog overflow at an inner width of 1195px:
the five KPI tracks expanded to 1221px because description cells used nowrap
intrinsic minima, extending the document to 1253px. The static presentation
allows KPI items to shrink and descriptions to wrap, with visible overflow and
breakable long tokens. It preserves the renderer's column breakpoints and all
description text; no clipping, hidden content, archive rewrite or CSP permission
is added. Existing dialog/inline desktop regressions retain exact horizontal
bounds and now check that KPI descriptions have no clipped scroll area.

## Demonstrated Cast report instance

Actual F2 Copy, Expand and Search actions were inert under the same empty
sandbox. Its pinned screen template also hides non-selected character cards
and clamps the synopsis, while print semantics reveal all characters. The static
reader exposes every role, synopsis, relationship and prompt; suppresses scripted
search/roster/copy/export/expand/lightbox controls; disables relationship-node
buttons and makes their retained graph canvas inert. Native prompt disclosures
initially open and still collapse/reopen; images and relationship text remain.
The exact-start-tag parser handles only current owned prompt/zoom/graph controls,
using LF-based positions and fail-closed source-slice checks. Archive evidence,
structured Cast review and acceptance remain unchanged. A genuine pinned
four-role fixture qualifies hidden-member disclosure separately from the fresh
native one-role delivery, which does not demonstrate a multi-role native run.

Accepted Cast report access follows the retained revision's `candidateJobId`,
because acceptance clears the active candidate pointer while the accepted
revision and candidate report remain durable. The accepted read model exposes
report availability and whether accepted JSON differs from the stored delivered
cast. The UI can reopen the same static report after acceptance and author edits,
and identifies the delivered version when those contents diverge. Missing
reports stay unavailable. Report bytes, CSP, iframe sandbox, and the existing
static projection are unchanged.

## Demonstrated Branch report reopening

Outline and Branch candidates share `SourceOutlineCandidateRow`, with the
request's `stage` as the discriminator. The original Outline report read checked
project, job, status and HTML but omitted that discriminator, so a ready Branch
report could be returned under an Outline URL. Each report reader now checks
its own stage at persistence. Branch reading requires the explicit job ID, a
ready Branch candidate and stored HTML; the Branch state exposes `reportAvailable`
only in that condition.

The Branch report URL requires `presentation=static` and returns the retained
HTML unchanged under the standard no-script sandbox, `default-src 'none'`,
data-image-only policy and no-referrer headers. The existing report-frame read
admission and empty iframe sandbox govern navigation; no scripts, adoption,
installation or accepted-lineage behavior is added. Regression checks cover
ready-only availability, cross-stage rejection, unchanged report bytes, CSP,
and the explicit Branch panel control.
