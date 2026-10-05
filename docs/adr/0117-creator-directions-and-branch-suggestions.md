# ADR 0117: creator directions and advisory branch suggestions

Accepted 2026-10-04 for the approved creator UI batch. The topology portion is superseded before release by ADR 0118 after the owner approved Brief-driven branching.

The Brief's nullable text cannot restore selections, and the route form starts
empty even when an accepted outline describes a choice. Report access also
depends on the active candidate instead of the accepted version.

The author owns grouped direction selections and the existing free text (now
optional detail). Store selections as group/value pairs, preserving order and
custom values without parsing prose. Trusted code composes both into generation
direction; persisted free text remains unchanged. All story and visual consumers
use the same composition. No default creative choice is applied.

Use a separate explicit `branches` native text task for existing or new accepted
outlines. Reuse the frozen handoff, receipt, reservation and candidate envelope;
its kind discriminates branch payloads from outline payloads in the existing
candidate table. It never changes the outline head. The pinned outline skill
provides narrative context; the package's branch schema and local validator/
renderer replace its outline output shape. No upstream episode-to-node inference
or prose splitting is allowed. An integrated outline extension was rejected
because it would require regenerating existing accepted outlines.

The model owns opening/endings prose, playback question, option labels and
consequences. Code binds fixed topology IDs, frozen source/outline hashes and map
revision, validates complete nonblank content, identity and currentness before
send/delivery/adoption, and preserves saved maps and local edits. The author
explicitly loads a suggestion into an editable draft and confirms it through the
existing map save/install gates. No task send, creative acceptance or route
installation is automatic. Ambiguities are disclosed in the derived report.

Accepted reading binds the retained candidate ID and accepted content. Missing
HTML falls back to that structured content in a read-only dialog. Returning from
revision requires the current accepted/source revisions and discards only the
current publication candidate, never native execution ownership. It is forbidden
after a source change; cancelled/late jobs retain existing settlement semantics.

Sequential foreground result checks retry transient reads with capped backoff;
identity/integrity errors stop automatic checks with recovery guidance. Neither
timeouts nor errors release reservations. Regression checks cover persistence,
generation composition, stale suggestions, dirty drafts, return, report identity,
transient recovery and late responses.
