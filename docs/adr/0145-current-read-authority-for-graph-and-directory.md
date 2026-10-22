# ADR 0145: Current read authority for graph and directory actions

Status: implemented candidate; qualification and limits are recorded in the
[bounded receipt](../verification/2026-10-09-graph-directory-read-recovery.md).

## Cause and decision

An initial graph GET failure was projected as preserved content and a command
error. Missing graph state passed the optional read-only check. Professional
Source reading could therefore enable confirmation/application without graph
authority. Failed same-project refreshes retained editable state and prepared
previews. Separately, graph autosave admitted writes using only project connection
and conflict state, so guarding graph buttons could not stop queued timers or blur.
Directory failures discarded known rows, had no explicit retry, and shared their
error owner with lifecycle mutations. These defects were demonstrated through
GET-only browser faults against native8865 and confirmed in the owning source.

The graph provider owns explicit `loading/ready/failed` read status and a separate
read error. Only a successful current, editable graph read admits local edits and
new commands. A read started during command acknowledgement revokes the command's
admission; existing dispatched writes may still retain their valid ACK/outcome.
Project/epoch, read-generation, latest-ACK, receipt CAS and selection ownership
remain enforced. Stale-but-ready explicit recovery is intentionally admitted;
ordinary stale editing remains blocked. Successful canonical read-only views are
ready reads, not failures.

All provider graph GETs, including the read after successful content confirmation,
use this one authority path. A failed follow-up read does not relabel a successful
confirmation as failed. Its saved receipt/content basis remains pending until a
current read can verify the exact revision, canonical base and binding before
rebasing Undo; late/superseded reads cannot update it or downgrade a newer ACK.

The workspace passes the provider's synchronous admission to the authoring
autosave owner for `story_graph` only. Every new write from timers, blur or drain
checks it; pending/failed reads preserve unsent buffers without starting a new
graph write. Draining an empty scope requires no graph read. A drain joins an
already-admitted flight and accepts its valid ACK, but cannot save newer input
after admission is revoked. The full browser sweep exposed the earlier guard's
placement before the empty-queue check: an unmounted graph editor blocked Close
and snapshots for unrelated scopes, with no lifecycle request sent. Project
ownership, conflict and suspension guards still apply to drains. Unrelated text
and media scopes remain under their existing owners; lifecycle quiescence is not
a read-status mechanism.

Graph and Source retries perform GETs only. Source reading is shared by both graph
views and excludes late project/binding results. Directory reads own separate
errors and exact retry arguments, retaining same-filter rows/cursors and blocking
their actions until a successful read. Filter changes remove prior-filter rows;
append retry uses the failed cursor. Closing invalidates late replies. Lifecycle
action errors do not invalidate a successfully read directory.

## Alternatives and guardrails

Button-only guards leave autosave writes possible. A global project write freeze
blocks unrelated scopes. Treating retained content as current authority loses the
read boundary. Automatic retries obscure recovery ownership. None is adopted;
there is no compatibility adapter or retry framework.

Provider/autosave integration, in-flight ACK, command admission, Source ownership,
directory paging and three-size GET-only browser checks guard the contract. Native
after-activation acceptance and wider Create → Revise → Recover coverage remain
separate from this software qualification.
