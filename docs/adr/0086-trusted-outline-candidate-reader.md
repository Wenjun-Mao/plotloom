# ADR 0086: Render outline candidates as trusted UI over immutable data

Status: Superseded within this ADR by the creator-approved revision below, 2026-09-26.

## Current decision: isolated interactive original report

The creator rejected the loss of the original designed presentation. Restore
the immutable HTML as the primary expanded reader, with JSON fallback when no
report exists. Both iframe and HTTP CSP grant only `allow-scripts`, never
`allow-same-origin`. Inline scripts may switch views; external scripts and eval
remain blocked. CSP blocks connections, forms, nested frames, objects and
external resources, permitting only inline styles and data images. Downloads,
popups and top navigation have no sandbox grant. Suppress referrers. This change
is limited to outline reports and also protects direct endpoint navigation.

Keep acceptance outside the report. Preserve delivery bytes and explain that
upstream episode parameters are not confirmed episode counts or route duration.
The original export control may remain visible, but downloads stay restricted.

This is not complete containment: code can consume resources, show misleading
content inside its frame, and may navigate its own frame. Do not claim an
absolute network or availability boundary. Test headers and iframe permissions,
real tab switching, blocked parent/storage access and connections, and dismissal.
No provider calls or project acceptance are needed for verification.

The following records the superseded initial approach, not current authority.

## Context

The specialist HTML report has JavaScript-driven tabs, but our iframe and API
CSP intentionally prohibit scripts. Enlarging the iframe improved size but left
nonfunctional controls. Its episode-based template also presents structural
records as confirmed episode counts even for a single interactive short.

## Decision

The primary candidate reader renders the admitted outline JSON through React
text nodes. Plotloom owns the overview/detail controls, not the generated HTML.
All fields, including unknown fields, remain inspectable. The original report
stays sandboxed technical evidence with its disabled-interaction limit stated.

Use neutral “结构条目” labels for upstream episodes/ep references, explicitly
distinguishing them from approved episodes, branch counts and endings. Do not
infer story format from prose or add target durations to claim a route duration.
Preserve source order and identify the overview as record order, not playback.
The user still separately accepts the exact candidate through the existing API.
Neither reader controls nor labels modify the delivery or confirmed content.

## Alternatives and guardrails

We reject enabling arbitrary report scripts or rewriting the retained report.
We also reject silently converting its episodes into canonical scenes/branches.
Story-format controls and synopsis assistance are subsequent work, not part of
this presentation correction. Tests cover switching views, complete extra-field
display, escaped markup, retained sandboxing, and unchanged input data. Browser
checks cover scroll, modal dismissal and focus restoration.
