# Native dramatic intent writing contract v1

Read the exact frozen package. Context contains the Brief, admitted story nodes,
script scenes and cuts. `source.proposal` owns proposal revision/hash, source
inputs and canonical replacement target. `inputs/targets.json.entries` owns
every target ID, source coordinates, source hash and source excerpt. Never emit
or change those bindings; output only each exact `id` and `suggestedText`.

Write concise Chinese dramatic intent. A scene objective explains what the
character wants to achieve in the scene; a beat purpose explains the dramatic
function of the action, reaction or dialogue. Do not merely copy the source
excerpt or describe the camera. Preserve story facts, scene/beat boundaries,
shot counts and durations. Do not invent facts to resolve ambiguity. Put concrete
limitations in the completion manifest. Suggestion text stays within 800
characters per target. The whole request has at most 64 targets and 60,000
characters of context and targets.

Write `intent.json` as `{"entries":[{"id":"exact-target","suggestedText":"建议"}]}`.
Return every target exactly once, without additional fields. Derive `report.html`
using `scripts/native_bridge_intent.py render`, after its `validate` command
passes. Publish completion.json last with actual hashes and pinned local code,
contract and specialist skill identity. Candidate, report and completion are the
only delivery files. A report is evidence to read, not approval or authority.

The author separately saves the whole package and reviews presentation before
confirming production. Delivery cannot approve intent, install canon, start media,
or change a frozen package. Late or stale results are retained evidence only.
