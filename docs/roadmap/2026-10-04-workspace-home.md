# Workspace Home control

Status: Implemented, independently reviewed, locally qualified, published and
verified on normal 8841, 2026-10-04. Full remote CI is running; creator usability
acceptance is separate. See the [delivery record](../verification/2026-10-04-workspace-home.md).

Make the upper-left Plotloom brand a keyboard-accessible **首页** control that
returns to the existing start screen. Home is navigation, not project Close:
retain the existing draft gate, keep saved content and background jobs, and do
not submit lifecycle mutations. Distinguish explicit Home intent from local
blank/sample page changes, which also have no persisted project ID.

Implement the shared navigation intent and branded control; verify clean,
unsaved, durable-draft and history cases with the established frontend checks;
obtain independent read-only review; publish and inspect normal 8841 without
editing existing project data. Stop at qualified, activated delivery.

The Chinese manual and broader contract audit remain deferred. No generation,
cancellation, project deletion, V1 change or backend schema change belongs here.
