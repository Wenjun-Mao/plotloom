# ADR 0099: Source-review activation revalidates authority

**Status:** Accepted

## Context

The live creator saved an opening-only Script edit as r3. The server correctly
marked retained Storyboard review r1 stale, but the workbench still displayed
accepted r1 bound to Script r2 after navigation and a same-project server
refresh. Source, Art, Script and Storyboard panels stay mounted behind hidden
sections; their project-ID-only reads cached earlier acceptance indefinitely.
The reader's fresh load correctly refused that stale binding.

## Decision

The source workflow supplies each panel its visibility and the aggregate project
refresh identity. On entry and same-project server refresh, a shared activation
owner revalidates that panel's server-owned review state. Actions remain disabled
while that read is pending or failed; retry is explicit. Only the latest owned
read may publish state. Existing project epochs still confine mutations and
responses to their original project and mounted owner.

Activation, explicit retry, mutation completion and delivery completion use the
same read owner and readiness verdict. A superseded read publishes neither
payload nor failure; a failed latest read disables authority-dependent actions
even when a previous successful payload remains visible.

Revalidation preserves mounted editor buffers. It does not remount panels,
discard unsaved requirements or scoped drafts, accept retained evidence, resend
generation, or alter upstream bindings. Storyboard retains its old evidence
under the server's stale label and prevents production preparation while stale.
Dirty Script and Art text retains the revision, content hash and binding under
which editing started. Status or accepted-head changes disable saving that draft
without rebinding it. Retained text remains visible, with explicit discard and
replace-with-current actions; refreshed state cannot silently replace dirty text.
Stale prepared/ready candidates remain inspectable and cancellable, but cannot
be sent or accepted. Dispatch inhibition is separate from result checking, so
retained tasks can still be observed or safely reconciled without a new call.

Each stage's current review seam is the active candidate when present, otherwise
the retained accepted revision. API status and stale reasons derive from that
same binding, including a first candidate with no accepted revision. Script and
Cast now follow the existing Art/Storyboard projection. A current replacement
candidate remains usable over stale retained accepted evidence; that old evidence
is preserved and does not confer authority on downstream consumers. Dispatch and
acceptance still independently validate the exact candidate binding. Adding a
frontend stale-reasons fallback was rejected because accepted-first reasons would
also block legitimate replacements.

## Consequences and guardrails

Conditional remounting was rejected because it discards drafts. Polling, a
Storyboard-only special refresh, and trusting old acceptance until an action
fails were rejected because they leave the shared source-workflow contract
unfixed. Navigation adds one bounded read of the visible owner; there is no
background polling or new persistence/event system.

Real backend browser regressions cover scoped Script save to sibling stale
review, same-project refresh, pending/failed-read action guards and retry, and
unsaved scoped-draft retention. Existing delayed-response/project-switch tests
remain required. No production timing, media dispatch or creative acceptance
contract changes.
