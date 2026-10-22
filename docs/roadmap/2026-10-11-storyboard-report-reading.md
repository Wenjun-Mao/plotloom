# Storyboard report reading refinement

Status: implemented, independently reviewed and locally qualified.

The owner requested that「阅读原始分镜报告（只读）」appear before「查看待审阅分镜」,
have more reading space, and pop out like the existing expanded report reader.
Root is the source owner; a bounded GPT-6 Luna / Max read-only reviewer supplies
an attended stable-candidate review.

Implement the shared static reader's opt-in enlargement with the existing
native dialog pattern and larger inline height, update Storyboard ordering and
next-step wording, and preserve source-bound report identity, admission,
sandbox/CSP, no-referrer policy and independent confirmation/production.
Script's current reading layout and all backend/runtime contracts remain unchanged.

Qualification is risk-scoped local frontend qualification: focused component
and affected browser regressions, unfiltered frontend unit tests and both type
checks, two deterministic builds with matching asset hashes, and direct pixel
inspection at 1280×460, 1280×768 and 1700×900. No full Python suite, provider
dispatch, valued-project edit, service restart or hosted CI is authorized by
this bounded presentation request. Stop after independent review, local
qualification, fresh static assets and scoped main publication; report hosted
qualification and owner acceptance separately.

The [verification receipt](../verification/2026-10-11-storyboard-report-reading.md)
records the focused and unfiltered frontend checks, deterministic assets,
desktop pixels and zero-write live reader check. Hosted CI was not dispatched;
owner acceptance remains with the next manual walkthrough.
