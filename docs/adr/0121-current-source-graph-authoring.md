# ADR 0121: One current source-bound graph authoring contract

Status: accepted under the owner-approved G0–G1 workbench scope, 2026-10-06.

## Problem and evidence

Source confirmation previously required equality with the planner topology, while
the professional editor independently wrote a complete canonical graph. Neither
could truthfully recover blank prose or pending connections. Binary map execution,
V1 stage readers and old run-snapshot defaults also kept retired contracts runnable.
The isolated G0 probe demonstrated planner-equality refusal, mandatory control-node
footage and rejection of empty screenplay episodes. ADR 0120 owns the bounded
footage correction; the pinned upstream validators remain unchanged.

## Decision

Both workbench modes edit one typed `story_graph/root` authoring draft. Its mapping
has an immutable current planner seed, explicit planner/author provenance, authored
topology, ordered stable sections, exact choices, join reconciliation and required
footage membership. Planner provenance requires equality with that seed's
structure and ordered footage membership. Prose remains author-owned. Changing
footage inclusion marks author provenance while retaining the original seed. Author
edits preserve the seed and must pass actual graph targets and current state checks.

The draft explicitly represents blank prose and nullable connection endpoints.
Saving it is recoverability, not admission. Source-map confirmation validates the
complete current mapping against exact source/outline revisions and hashes.
Canonical installation checks those identities, canonical revision and exact draft
revision/base/content in one transaction, then consumes that draft atomically.
Graph draft persistence accepts only the `root` identity on writes and reads;
an acknowledged graph buffer cannot sit outside that sole admission owner.
Generic manual StoryGraph stage writes and generic graph-draft consumption retire.
The independent canonical-shaped frontend graph editor and its cascade mutation
helpers retire with that write path. Current canonical graphs remain inspectable
through a read-only reader; both editing modes use the shared command owner.
Other stage writes and supported generation/bootstrap installation retain their
current typed validation, snapshots and concurrency guards. A canonical graph
without source provenance cannot be overwritten through source admission.

G1 freezes a context hash over current Brief, source/outline, accepted map and
graph/Bible identities. Draft saves and command confirmation require that exact
context. Read-only preview hashes bind the acknowledged draft revision, typed
command, immutable result and impact; apply recomputes under the write lease.
Content confirmation requires the exact acknowledged root draft, then updates
its context and revision atomically. Installation always requires and consumes
that draft. Explicit recovery on a changed base retains its authenticated seed
and content, marks author provenance and grants no historical approval authority.
Only-delete retains detached endpoint identity/title/kind with option prose and
effects in that same draft. Incomplete join inputs remain recoverable; strict
admission still requires complete current joins. Undo is session history of
confirmed draft transactions saved through the same CAS owner, never a rollback
of approval, production or media.

Commands preview against a session draft revision and apply one immutable result.
Edge identities, option prose and typed/fact effects survive exact insertion and
retargeting; join input contracts require explicit review. Detached/pending links
remain visible. Cancellation, stale confirmation and failed safety checks mutate
nothing. One Undo transaction restores authored content, links and selection.
Presentation hints never create routes or production authority. Canonical admission
or an externally changed base reconciles the draft and resets session Undo.
Initial selection belongs to the authored mapping's current opening, not the
retained planner seed's identity. The seed is provenance and may use different IDs.

Row reuse is an explicit current command: it attaches a detached existing node
without changing its identity/content/type or overwriting existing outputs. New
decision creation explicitly chooses whether to initialize two pending options or
reattach retained authored options. Pending scaffolds never silently consume the
capacity needed by a restoration command or replace retained prose/effects.
Identical endpoint retargeting is rejected as a meaningless transaction.
Changing an input by choosing another exact output is one `replace_input`
transaction: the prior input remains pending with its identity/prose/effects,
and the chosen output targets the selected node. Its displaced target survives.
Preview, safety comparison, confirmation and Undo cover both changed edges.

Installed production remains readable and protected by first-install-only guards.
Draft edits never rebind scenes/shots/media, approve candidates or dispatch jobs.
Any disposable demo rebuild must name its exact target and prove quiescence; no
general installed-production replacement or automatic reset is introduced.

Only current schemas execute. Retire binary maps, historical intent reconstruction,
V1 canonical classes/selection/validation, missing snapshot schema defaults,
historical timing/capacity replay and historical correction witnesses. Explicit
current frozen evidence is required; old receipts are not rewritten or upgraded.
Required footage membership also lives in frozen topology and timing contracts,
and is included in their hashes. Provider names and preserved current evidence are
not grounds for deletion.

## Alternatives, consequences and guardrails

Reject a second creator graph, wrapping the competing generic writer, fabricated
source provenance, permissive old/new readers and replacing the source-first gate
with canonical save. Breaking development schemas requires rebuilding only an
identified disposable fixture when necessary. Current user work, credentials,
snapshot/restore, exact currentness and unknown-dispatch safety remain protected.

G0 round-trip and production tests cover three options, insertion, a join, retained
effects, incomplete recovery, exact draft CAS, route-only controls and explicit
footage inclusion. G1 adds command safety/history and browser conflict evidence.
G2–G5 qualify the shared UI and release candidate; this ADR is not a claim that
those later slices have shipped.

## G5 selection receipt guard, 2026-10-06

A full native journey demonstrated that Undo's late receipt could overwrite a
node selected by the author after the operation started. Browser selection is
presentation state, not an authored graph mutation. Current command, Undo,
recovery and confirmation receipts now carry a selection-generation basis:
preserve a later explicit selection if it still exists in the committed mapping;
otherwise use the receipt's safe selection. Content/CAS/Undo semantics do not
change. Deferred-receipt regressions cover both retained and removed nodes.
