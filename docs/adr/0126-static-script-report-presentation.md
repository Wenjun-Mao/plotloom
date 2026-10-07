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
not working interactive buttons. The current F4 renderer has no tabs/hidden panes;
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
