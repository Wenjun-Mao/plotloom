# Checkpoint 3B semantic-plan-to-Scene-Beats expansion receipt

This is a bounded, disposable continuation of the compact semantic experiment.
It is not a production integration, prompt/schema/validator decision, canonical
installation, Approval, human creative acceptance, reliability claim, or
checkpoint 3B acceptance.

## Question and frozen design

The compact mapping receipt established that the four-field semantic response
could not itself satisfy `scene_beats.fragment.v13`: scene, beat, continuity,
and dialogue content remains model-owned. This test asks the narrower follow-up:
can each of the two already-frozen compact plans be supplied as draft prose
alongside the exact original full keep-ending Scene Beats input, then expanded
into a valid current fragment without correction machinery?

The source primary artifact is `c749d5ca-b5d0-4551-a7fa-0a378202336c` in
`.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/trace-final.json`, content
hash `a91ec56d7409dbd93038ba063253e211eec96c469526afdd35faaa4647e5e7a7`.
Both original messages were retained byte-for-byte (message SHA-256 values are
in the manifest). A third generic user message supplied exactly one compact
plan and asked for a full fragment. It says that frozen Bible/Graph/entry/schema
authority outranks the draft, free-text `resulting_facts` is not an entity state
or enum, and missing scene/beat/continuity/dialogue material remains model-owned.
It does not name a preferred repair, shop, watch, or other story-specific
resolution.

Before dispatch, the ignored manifest and full secret-free request payloads
were frozen in `.local/relay/semantic-plan-expansion/`:

| Frozen plan | Expansion request SHA-256 | Provider request ID | Usage |
| --- | --- | --- | --- |
| `independent-1` | `78c0134ad6412c9185b8033a3ccfc8e93f2752a838ba641a42bfc3c42805e029` | `chatcmpl-qAoySzoKOaPWj8n4IFl13mzJmWzj6QGq` | 6,880 input / 2,303 output tokens |
| `independent-2` | `5b7ab32f5e337bcdd449cb29c757d39afaab9d0ffde959d8cc31cf5bd77fa774` | `chatcmpl-psmlOyYaIiCdbxvMEDSSVpoQRUFVTlS1` | 6,884 input / 2,310 output tokens |

Exactly two independent calls completed, one per plan. There was no retry,
correction, third call, repair/restart action, profile/environment change,
canonical write, media action, or Approval action. Both used current default
profile v11/hash `6f0e6d29521b4d19b2bf1e8dd7410de72355390e20d916289b8d8ad6e9567473`:
`qwen3527b`, temperature 0.2, 8,192 Scene Beats tokens,
`chat_template_kwargs`, and disabled reasoning.

## Offline structural evidence

For each response, the experiment ran the current exact
`SceneBeatsFragmentOutput` parser; the current fragment semantic validator with
frozen Bible, Graph, dialogue timing/capacity, join, and typed edge-entry
dependencies; trusted binding; and `validate_stage_payload` for a hybrid
Scene Beats aggregate. The hybrid retained the frozen source aggregate from
`.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/new-stages-final.json` and
replaced only the target ending fragment in memory. It was never persisted.

| Response | Shape | Fragment semantics | Binder | Hybrid full owner validation |
| --- | --- | --- | --- | --- |
| `independent-1` | pass | pass | pass | pass (1 scene, 2 beats, 2 cues) |
| `independent-2` | pass | pass | pass | pass (1 scene, 2 beats, 2 cues) |

The validation harness deliberately uses a fresh, in-memory experiment plan,
so its `stagePlanHash` and work-unit ID are not a claim that it replayed or
replaced the historical source run. Its dependencies, source primary messages,
profile, and source aggregate are frozen retained evidence. The hybrid pass
shows current owner compatibility for these replacements; it does not establish
whole-graph or join quality, pipeline installation, or statistical reliability.

## Content observation and independent review

Both outputs preserve the already-true `prop_pocket_watch=已修复` state through
scene and beat entry/exit. They realize the consequential contract-deferral
action and then its debt/relationship consequence, rather than performing a
new watch repair or restart. Past-tense references to the repaired watch are
not treated as failure. The compact plans' free-text fields are not converted
into entity-state enums; the full primary source independently supplies the
ending's contract, buyer-dissatisfaction, debt-risk, and reconciliation context.

An independent attended Terra read-only review of the frozen source context,
both expansion payloads, rubric, and structural evidence found no concrete
blocking coherence issue. It confirmed that both first scenes retain the typed
entry states; neither repairs, restores, or restarts the watch; and each has a
coherent contract-tear → sale-suspension/risk → sibling-reconciliation chain.
The first response visibly shows the buyer's dissatisfied departure. The second
records dissatisfaction as a consequence rather than showing it, which is
thinner but not contradictory because the frozen target summary itself supplies
that fact. Neither output creates a new `entityStates` enum or promotes the
compact plan's `继续营业` text into a location enum; its added free-form facts
and continuity deltas are model-authored fields, not Bible enum assignments.

This is independent engineering/creative review, not human creative Approval.

## Disposition and proposed next slice

This experiment is structurally positive only until the independent content
review is recorded. It remains isolated evidence, not checkpoint acceptance.

If director review accepts both structural and content observations, the
smallest existing-pipeline integration proposal is one explicitly selected
Scene Beats work unit: make the compact plan an auditable, non-canonical
authoring input to that unit's existing full fragment request, retain the
current parser/binder/full validators unchanged, and install nothing until a
separate integration assignment defines source ownership and acceptance. This
is a proposal only; no production code, template, schema, profile, or retained
project data changes here.
