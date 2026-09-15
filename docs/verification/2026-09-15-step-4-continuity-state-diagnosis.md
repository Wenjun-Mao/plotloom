# Step 4 continuity-state contract diagnosis

Captured 2026-09-15 from read-only retained evidence. This is a diagnosis and
implementation proposal, not a retry, acceptance, or change to the retained
project. It covers project `ae4595cf-2bcc-480a-839b-af3a8901240c`, parent run
`2326517e-9e51-4771-aa15-eeeecb3382bd`, and exact-repair child
`e3ab40df-f6dd-4381-9a59-1e8f5db589de`.

## Finding

The immediate rejected values came from model responses, not the binder, but
the first response was driven into a contradictory frozen input contract and
the correction contract omitted the only authoritative replacement vocabulary.

The sealed Story Bible defines `loc_station` allowed states as:

```text
空无一人
林澈在场
站务员在场（未定）
```

The accepted Story Graph's direct edge into Scene Beats #7 is
`edge-fd80e698-1239-5a45-bd8f-73320eecbbe7`; its persisted state effect is
`loc_station_state: "站务员在场"`. That string is not in the Bible vocabulary.
The same edge also says its choice is `站务员在场`. The graph response was
accepted with no issues: its validator verifies finite JSON state effects but
does not validate an entity-state effect against the Bible.

Scene Beats #1--#6 each accepted on their first primary attempt and their
persisted location state is only `林澈在场`, which is in the Bible. Their incoming
graph edges contain no location-state effect. #7 is the first unit whose
target-context prompt includes the contradictory direct edge. #8's other
incoming choice has `loc_station_state: "空无一人"`, a valid Bible value, but #8
remained queued in both runs.

## Exact six-attempt evidence

Every failure is at `loc_station` (`entityStates[1]`), not at a generated ID
or a trusted canonical rewrite.

| Lineage / attempt | Model response value at every reported location-state path | Reported paths |
| --- | --- | --- |
| Parent primary | `站务员在场` | beat 0 entry/exit; scene 0 entry/exit |
| Parent correction 1 | `站台开放` | beat 0 entry/exit; scene 0 entry/exit |
| Parent correction 2 | `开放` | beat 0 entry/exit; scene 0 entry/exit |
| Child primary | `站务员在场` | beats 0--1 entry/exit; scene 0 entry/exit |
| Child correction 1 | `站台开放` | beats 0--1 entry/exit; scene 0 entry/exit |
| Child correction 2 | `站台开放` | beats 0--1 entry/exit; scene 0 entry/exit |

The parent failed attempts are `4a2e7a5a-…`, `5e75b652-…`, and
`00c00c96-…`; the child failed attempts are `6325c349-…`, `1d478b37-…`, and
`2ce398d5-…`. Each validation artifact reports only
`semantic.invalid_continuity_entity_state` at those paths. The raw response
values above equal the values inspected by the validator. The fragment adapter
performs schema and Bible semantic validation before `_bind_fragment`; the
binder only assigns trusted IDs/parents and copies each parsed continuity
state. It therefore did not inject these invalid values.

## Prompt, schema, and correction evidence

The parent and child primary prompts are `scene_beats_fragment` v3.12.0. Their
actual rendered messages contain the Bible's `allowedStates`, the instruction
that every state must literally belong to that entity's allowed states, and the
direct incoming edge with `loc_station_state: "站务员在场"`. Thus the primary
attempt had vocabulary guidance but two incompatible authorities. Following
the graph's requested effect explains its invalid choice; this is not a case
of an otherwise unconstrained model inventing a state.

All four correction prompts are `work_unit_correction` v3.11.0. They contain:

- the failed code/path pairs and the generic `continuity_values` directive;
- a response schema that constrains entity type and ID but leaves `state` as a
  non-empty string; and
- no Bible `allowedStates`, no Bible literal `站务员在场（未定）`, and no typed
  repair fact. Their `issueSelection.factBindings` and evidence-projection
  `facts` are both empty.

The directive says to use states allowed by the “target Schema”, but the target
schema does not carry allowed state values. It cannot make the correct literal
recoverable. The synonyms in the four correction responses are therefore
unconstrained replacements, not a validator or binder defect.

## Ownership and ruled-out alternatives

| Concern | Owner | Evidence / conclusion |
| --- | --- | --- |
| State vocabulary | Story Bible author; trusted validator enforces it | Bible has the three values above; `continuity_state_issues` correctly rejects all six nonmembers. Do not relax it. |
| Edge effect value | Story Graph author, constrained by trusted code before graph seal | The graph authored the invalid `loc_station_state` and was accepted. This is the upstream contract gap. |
| Primary response | Model | It reproduced the graph's invalid value despite also seeing the Bible. The contradiction, rather than absence of guidance, explains this failure. |
| Correction response | Model, within a trusted repair contract | The contract omits the allowed values; it supplied unrelated synonyms. This is a second, independent correction-authority gap. |
| Canonical IDs and continuity-state installation | Trusted binder | Rejected raw values and validation paths match; validation precedes binding. Binder injection is ruled out. |
| Join-required state conflict | Not implicated in #7 | #7 has no join contract and its compiled `requiredEntryFacts` is `{}`. The invalid direct edge is an ordinary upstream graph effect, not a required join value. |

The validator is not a cause: it protected the sealed Bible contract. Nor does
the retained record support a model-specific remedy, a fourth correction, or a
state choice by trusted code.

## Smallest durable implementation proposal (not approved here)

Before implementation, amend ADR 0022 because this changes ownership of graph
state effects and correction authority.

1. Give a Story Graph edge effect that represents a Bible entity state an
   explicit typed entity reference (rather than relying on an opaque
   `*_state` key convention). At Story Graph validation/sealing, verify the
   referenced entity and state against the frozen Story Bible. The graph above
   must then reject before any Scene Beats work is planned.
2. For an already schema-valid
   `semantic.invalid_continuity_entity_state`, derive a versioned,
   source-rebound repair fact from the frozen Bible and the rejected response:
   response-local path, entity type/ID, and that entity's complete ordered
   `allowedStates`. Narrow that exact response-schema path to the fact's enum,
   require the entity entry to remain present, and make the directive name the
   fact as its sole authority.
3. Keep `continuity_state_issues` and its canonical counterpart unchanged, and
   keep binding after semantic acceptance. Do not auto-select a member of
   `allowedStates`, rewrite retained output, or infer an edge value from prose.

This is deliberately two linked guards: graph validation prevents new
contradictory contracts; the repair fact gives a bounded correction the frozen
vocabulary for other rejected evidence. It is not safe to implement only a
stronger English/Chinese reminder or to insert a server-side replacement.

## Offline reproducer and regression targets

Use a minimal Chinese fixture with `loc_station.allowedStates` equal to the
three literals above, a non-join edge targeting a Scene Beats node with typed
location effect `站务员在场`, and a fragment that copies it into the four
continuity boundaries.

1. In `tests/generation/test_story_graph_topology.py`, add a focused graph
   adapter test proving that this edge is rejected before seal with an
   entity-state-vocabulary issue, while `站务员在场（未定）` is accepted.
2. In `tests/generation/test_work_unit_contracts.py`, add a correction compile
   test proving an invalid known entity state emits the typed allowed-states
   fact, narrows only each reported `state` path, and cannot be satisfied by
   deleting or changing the entity entry. Retain the existing primary-prompt
   assertion that the Bible's `allowedStates` is rendered.
3. In `tests/generation/test_correction_directives.py`, assert that the
   `continuity_values` directive requires that fact and fails closed when it is
   absent, stale, or does not match the frozen Bible/response path.
4. Re-run only those focused files plus the existing fragment/canonical
   vocabulary parity test. No retained database, response artifact, hash, or
   historical prompt is rewritten; a new correction-contract version and its
   hashes distinguish future evidence from these six attempts.

## Disposition

Step 4 remains blocked. The retained parent/child lineage and six raw response,
prompt, and validation artifacts are preserved. No provider call, database
write, source change, or live retry was performed for this diagnosis.
