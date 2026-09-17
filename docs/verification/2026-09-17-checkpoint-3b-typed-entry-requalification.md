# Checkpoint 3B typed-entry continuity requalification receipt

Captured 2026-09-17 at local `main` revision `0083e62b2c593508262372446c8075e0dcb3e828`. This is one isolated current-contract runtime requalification after the engineering correction accepted at that revision. It is not developer-free UI creation evidence, Storyboard Approval, human creative acceptance, or checkpoint-3B acceptance.

## Isolation and retained input

The retained 3B project `700648eb-cfc8-4de0-8fab-f40bad86a4d4` was read through the normal local project API and never opened for writing. Before creating a new project, its Graph r1 was read-only compiled under `edge_entity_entry_states.v1`: graph input hash `ae01389f9ab5a9a3d3ffc54fa4a46d18c612224f5f87528a1ab5402252d8bb09`, contract hash `1a855aa302e15c1607d974bd5b4c61ace7036de2883636ff34ed42ee5b301e7d`, five target nodes and 16 typed requirements. It is compatible with the prospective admission contract.

One new project, `4d03b871-02c5-41c8-9881-b248aee7e529`, was created through `POST /api/v2/projects` with only exact copies of the retained Brief, Bible r1 and Graph r1 as the supported initial-stage prefix. There was no SQL write, file cloning, proposal change, Graph/Bible regeneration, copied Scene Beats/Storyboard head, profile/environment change, or media action.

| Compared content | Retained hash | Isolated-project hash | Result |
| --- | --- | --- | --- |
| Brief normalized projection | `2de735d55e68a8ab5d3aed93eabbd289dd8b87b7419b55188deb378e8656bbf3` | same | exact |
| Story Bible r1 | `18a824db33cd62d56d3335a7d2c32ae04f3db71bafd518fe3ef88f2902aa5d4a` | same | exact |
| Story Graph r1 | `d8c6f87caabeb192a85b4e69d9af685358386310f895d1a4f3cc7e5adfdd8860` | same | exact |

The old project’s API responses and complete stage projection had identical SHA-256 values before and after (`777047…69b9` and `1b1fa4…861b`, respectively). The only identity difference is the new project id and associated canonical revision identities.

## One bounded continuation

Run `4a18f347-aaf5-4eb7-9cc7-ae268c8c9259` requested exactly the contiguous current stages `scene_beats` and `storyboard`, under frozen default profile version 11 / hash `6f0e6d29521b4d19b2bf1e8dd7410de72355390e20d916289b8d8ad6e9567473`. It started at 13:00:00Z and succeeded at 13:17:17Z. This was the sole fresh downstream run.

All eight Scene Beats and eight Storyboard units sealed. The runtime’s already configured bounded corrections were visible and preserved, rather than manually invoked: Scene Beats unit `unit-scene_beats-0005-0e47a89d86d334c9` corrected primary `semantic.cue_order`; Storyboard units `unit-storyboard-0001-540705203885b24a` and `unit-storyboard-0003-4b9f9174efdad729` corrected `semantic.required_entity_not_in_shot` and `semantic.cue_duration_exceeds_shot`. All three correction attempts succeeded. There were no quarantines, exact-repair calls, hidden retries, second runs, or media dispatches.

| Current stage | Revision / hash | Scope |
| --- | --- | --- |
| Bible | r1 `18a824db33cd62d56d3335a7d2c32ae04f3db71bafd518fe3ef88f2902aa5d4a` | preserved prefix |
| Graph | r1 `d8c6f87caabeb192a85b4e69d9af685358386310f895d1a4f3cc7e5adfdd8860` | preserved prefix |
| Scene Beats | r1 `2f25067fd8ed0916f3b506787b3f01cbb95eb5b950bbc581dd9ff7b70980e4e4` | 8 scenes, 19 beats, 16 cues |
| Storyboard | r1 `0fd9f6c1614d1e06c2b439946bf1d00d7377a78017072656a85b8d2410fbd771` | 14 shots, 19 beat links |

The final canonical `storyboard.v2` review has 515 required passes and zero failures. It has no active Approval and no decisions. The attended workbench loaded the installed Scene Beats and its settable scene/beat/cue fields; a browser reload again showed the same eight scenes, 19 beats, canonical dialogue, and both downstream stages `SEALED READY`. This verifies a technical installed/editable/reload result, not developer-free UI project creation.

## Causal inspection and quality disposition

The direct typed-entry correction works at its specified boundary. Sell edge `edge-5228f825-88ca-5e3d-b946-595d6e675caa` assigns `prop_pocket_watch=被遗弃` and `prop_order_note=被丢弃`; the first target scene `8f724579-c71e-54d7-aff1-1f5cf0744467` (node `node-6defdee8-9bf0-5950-97e3-59870412c84a`) carries both values in its entry state. The repair edge `edge-38df4ab3-05c6-591f-bfa5-c069e23c0156` likewise arrives at scene `63c6e618-8ba5-511a-9793-864a1fbb3226` with `修复中` / `被阅读`. Later state transitions are allowed by ADR 0056; the contract deliberately does not propagate path state across a join.

An attended independent Terra read-only review of these exact canonical payloads independently found the following quality failures. The sell target immediately depicts Lin Yuan holding the supposedly abandoned watch in beats `463e984e-67cd-5e3f-8aff-d2aebf47bc25` and `22ecb4e3-9b45-5b43-9dc7-81df7b707564`, and their primary storyboard shots `26294f56-3be4-5d56-bbcf-e4ce15957c8d` and `515d01d6-ba1c-5143-ba23-b51c404ce2c9`. Neither beat supplies the required recovery/recommit transition, and the discarded note has no visible causal handling. Both branches then enter join `join-e6e48238-c01f-5dba-8997-989fb5d976ee` / scene `1327fd71-a33b-55ff-b738-9da8e8b5b56a` with no typed entry state. Its beats `873dd75a-9ca4-58bc-9fda-9b9b3d1f2000` / `a7bdd1d9-ff25-5f58-be47-9720f2cecd6f` resume generic watch handling, and next-decision shot `46da4b75-d491-5c75-8354-a2d8c7aa0a5f` resets watch/note to `未完成` / `被发现` without a bridge from either incoming condition. Consequently, all four reachable root-to-ending routes (repair-or-sell early branch × sell-or-keep final branch) contain that causal discontinuity.

That unexplained reset carries into sale edge `edge-eaefdecf-d7d4-5ddf-8a48-31f49f653adc`, then sale-ending beat `a1058ac5-5ffa-5a73-aeb6-15ab5a7b99a0` and shot `7ef007c3-3d2c-5758-b043-6c17f0caf21e` hand a repaired watch to the customer with no repair bridge. The keep ending has the reciprocal sequencing flaw: its edge `edge-880188d8-c6e6-55cc-b3ee-66eaa33bc616` and scene `9891bf58-58ea-5753-8be4-d77f50454b5d` already state `已修复`, while beat `b523bcf6-0205-5e42-b0cc-b61d7577d84c` and shot `5c4a9390-7317-55d2-9095-7c9eeacfef49` perform the repair afterward. The shared join/final decision also repeat the pressure-and-watch confrontation already staged in both early routes, rather than creating a new consequence.

The review did **not** treat cue/audio scheduling as a defect: `cueIds` own speech, optional `audioPlan` does not need to repeat it, and a silent one-shot extra is not mechanically invalid. Nor does stage-level rebuild imply shot-local regeneration. Those are not explanations for the demonstrated causal problems.

**Disposition:** the engineering correction is requalified, but checkpoint 3B remains **not quality-qualified** and checkpoint 3 remains unaccepted. The minimal demonstrated next fix is author-owned causal content, not a new runtime framework: revise the sell path to visibly carry `abandoned/discarded` through a recover-or-recommit-and-repair bridge before any repaired handoff, and make the shared join/final content preserve or explicitly reconcile the two route consequences rather than silently resetting them. Re-review a fresh exact candidate only after that content change; do not infer quality acceptance from the 515 gates.

## Verification boundary

This was a docs/evidence-only slice. The retained run trace, API projections, hashes, and attempt lineage remain under `.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/`. No broad product suite was run. `git diff --check` is the proportional repository verification after the documentation update. The owned localhost runtime is stopped before Relay finish.
