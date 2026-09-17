# Checkpoint 3B compact semantic-to-Scene-Beats mapping receipt

This records a bounded offline feasibility observation. It is not production
integration, a prompt/schema/validator decision, Storyboard Approval, human
creative approval, a reliability claim, or checkpoint 3B acceptance.

## Missing receipt and frozen observation

Before this receipt, the compact experiment had only ignored local evidence in
`.local/relay/compact-scene-beats-feasibility/`; no tracked receipt stated its
scope or result. That record froze exactly two identical, stateless requests
against current profile v11/hash
`6f0e6d29521b4d19b2bf1e8dd7410de72355390e20d916289b8d8ad6e9567473`,
with no retry, repair call, or third request. Its source pointer is primary
Scene Beats prompt artifact `c749d5ca-b5d0-4551-a7fa-0a378202336c`, content
hash `a91ec56d7409dbd93038ba063253e211eec96c469526afdd35faaa4647e5e7a7`,
in `.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/trace-final.json`.

Each completed response is valid under the deliberately smaller exact
four-field shape: `observable_event`, `purpose`, `immediate_result`, and
`resulting_facts`. Both avoid repairing, restoring, or re-starting the already
repaired watch. Instead, each has Lin Xiaolan tear the transfer contract and
defer the sale; each records immediate debt/contract pressure, buyer
dissatisfaction, and sibling reconciliation. That is one narrow positive: the
two observations supplied a consequential continuation of the selected branch
without another watch-repair event. It does not establish consistency,
reliability, or an integrated Scene Beats result.

An earlier review inference is withdrawn: `老街小修表铺=继续营业` in the
free-text `resulting_facts` is not shown to conflict with frozen direct-entry
`loc_watch_shop=修复中`. The frozen Bible lists allowed location states but
does not establish exclusivity between those propositions. In any event,
`resulting_facts` remains free text: it is not a location enum, continuity
state, graph effect, or canonical project mutation.

## Current owner boundary and mapping result

The current `scene_beats.fragment.v13` response is a full fragment. Its model
owns local scene/beat handles and order, scene dramatic fields and references,
beat description/change/continuity, and any dialogue cues. Trusted code owns
the selected `storyNodeId`, canonical IDs, frozen duration allocation and cue
timing, and the Bible/Graph vocabulary and edge-entry checks.

| Compact field | Narrow proposed destination | Result |
| --- | --- | --- |
| `observable_event` | `beats[].visibleEvent` | Semantic candidate only; no beat identity or continuity is supplied. |
| `purpose` | `beats[].purpose` | Semantic candidate only. |
| `immediate_result` | `beats[].immediateResult` | Semantic candidate only. |
| `resulting_facts` | None | Free strings cannot be promoted to `entityStates` or continuity facts. |

The compact result does **not** say how many scenes/beats there are, supply
local IDs or contiguous order, name a scene/title/objective/location/characters,
provide a duration weight, write a beat description or dramatic change, or
provide entry/exit states, continuity anchors/delta, or a justified decision
about dialogue. Existing trusted context cannot author those missing creative
values. Conversely, the binder only derives canonical IDs and bounded timing
after a valid fragment exists; it cannot turn one summary into a complete
multi-beat scene.

The minimal future contract is therefore not a coercion of these four fields.
A separately approved Scene Beats authoring response would need to supply the
listed scene, beat, and continuity fields under the existing full fragment
contract, with explicit `dialogueCues` (which may be `[]`). The present binder
would retain its existing trusted ownership. `resulting_facts` must remain
non-canonical unless a separately defined typed destination contract authorizes
each value.

## Offline check and disposition

`uv run python .local/relay/compact-scene-beats-feasibility/diagnose_mapping.py`
read both frozen response envelopes and used the current
`SceneBeatsFragmentOutput` parser. Both retain the exact compact field set and
both fail at the same root boundary: required `scenes`, `beats`, and
`dialogueCues` are absent. The ignored output is
`.local/relay/compact-scene-beats-feasibility/mapping-diagnostic.json`.

No source/template/schema/profile change, provider call, project open, project
persistence write, canonical-stage mutation, or media/Approval action occurred.
Because the missing values are author-owned, no fake source-backed fragment was
invented and the normal binder/full validator was deliberately not exercised.

Tracker state: **compact mapping experiment recorded as insufficient for the
current Scene Beats parser/binder/validator; checkpoint 3B remains not
accepted**.

## Independent review

An independent attended, read-only Terra review inspected this receipt, its
roadmap entry, both frozen response envelopes, the ignored diagnostic, and the
current Scene Beats contract. It found no blocking issue: the four compact
fields fail the current fragment root boundary and cannot reach binding without
model-authored scene/beat/continuity content; the free-text facts have no
authorized canonical destination; and the Bible establishes no exclusivity
between free-text `继续营业` and typed entry `修复中`. It also confirmed that
the tracked scope is documentation-only. This is engineering review only; it
does not promote the observation to production or checkpoint acceptance.
