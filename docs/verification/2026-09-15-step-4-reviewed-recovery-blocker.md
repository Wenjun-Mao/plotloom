# Step 4 reviewed-candidate and recovery continuation

Captured 2026-09-15 from retained project `fef96fc8-86f8-4132-91bd-32d58f5bb504` at source checkpoint `b358066`. This secret-free operational receipt is not Step 4 completion, Codex-heard audio, lip-sync verification, a general dialogue-capability claim, human/product acceptance, Alpha qualification, or release evidence.

## Frozen contract and attributed review

| Job | Frozen shot / scene | SHA-256 | Dialogue and audio contract |
| --- | --- | --- | --- |
| `vj_86676092a8e84516922f650838c752e0` | `44598e70-49fc-519e-b71d-5c99f51dcd90` / `174495ff-40eb-5ba9-9840-c3027b95b1d5` | `1e95ed45f20f6287f6686a246f1e0164db6dd549d87472e30b1437cbd6302dc6` | `cueIds: []`; distant-train ambience only. |
| `vj_fffbcebbca8945fc99dbae42863f70b2` | `97c4a139-57fa-52b0-bf19-2dd5ef018391` / `5f0f0ba2-3515-5595-a797-5e2ad415a77b` | `45079df8f791cc3d32440b507a3c5d063bc52caf98ae750be216c22435b8854d` | `cueIds: []`; distant-train-and-light-wind ambience only. |

Both frozen shots require no dialogue; the user's reported absence of dialogue is contract-compatible. The user reviewed the two hash-verified review copies and said exactly:

> Yes, both video and audio are good, there is no dialogue though.

The normal project video-review route recorded that statement as **attributed human audiovisual feedback** under reviewer label `Attributed human audiovisual reviewer`, and selected each candidate:

- `f7d7195f-69d1-4c7e-ba7c-a713017f5d85` for the first job at `2026-09-15T23:27:18.020105+00:00`;
- `05ee01c0-039e-43eb-b05c-6a74617f5f27` for the second job at `2026-09-15T23:27:18.070696+00:00`.

Each persisted note limits feedback to its hash-verified candidate and says selection relies on user testimony, not Codex hearing. It asserts neither lip sync nor general dialogue generation nor broader product acceptance. Read-only SHA-256 checks of retained original bytes matched both listed hashes after selection.

## Native Chrome and sequence result

Native Chrome loaded the first selected candidate from Plotloom's normal range-serving endpoint and exposed the selected-player control; invoking it changed Chrome to its `Audio playing` UI state. That is playback-surface evidence only, not evidence that this agent heard audio.

The requested automatic cut and final-frame hold could not be exercised. The current selected-video player derives a sequence only from selected jobs with the same frozen `sceneId`. These candidates have the two distinct scene identities above, so Chrome rendered each as a one-item selected sequence (`1 / 1`) with previous/next disabled. No cross-scene transition or second-clip final hold exists to observe. This is a product composition boundary, not an in-app-renderer crash, byte-integrity failure, or provider failure.

## Recovery blocker

Safe close and snapshot were attempted through their normal production routes. Both returned:

```text
409 project_busy: image_publication_active
```

The project remains open (the normal reopen route returned `200`). Read-only inspection identified existing exported image job `ij_c6f81e5fd28441d7abf2a34e129221d9` as the active publication; the other two image jobs are delivered. It is the preserved incompatible-adaptation lineage from the prior media receipt. This continuation did not cancel, refresh, deliver, clean up, or otherwise alter that job or its staging.

Because a verified snapshot cannot be created while this operational blocker is active, no isolated restore was attempted. Restoring an open folder would violate the recovery contract, and no pre-selection snapshot can prove the new review/selection lineage. The two failed close/snapshot paths established the same blocker; no retry loop followed.

## Disposition

No ImageGen, upload, provider, dispatch, reconciliation, reservation, profile, configuration, or source action occurred. The pilot remains at four of four ImageGen calls and two of two H3 jobs; no original media byte or other project was overwritten.

Step 4 remains partial. Two separately scoped gaps remain:

1. The selected-player contract needs an approved cross-scene ordering rule, such as an explicit verified Story Graph edge/path projection, before it can claim a two-scene automatic transition and final hold. It should have a real-browser regression before another live proof.
2. The owner must choose a safe disposition for the exported image publication, or explicitly change the recovery contract, before close, snapshot, and isolated restore can proceed. This receipt does not imply cancellation or cleanup.

### Verification

- Direct SHA-256 checks matched both retained video artifacts; current API reads reported both `ingested`, `current`, and `selected`.
- Native Chrome received `206` range responses for the first selected clip and accepted its visible play action; no audio observation is inferred.
- Close and snapshot both returned the preserved `409` blocker. No broad code suite was run for this operational documentation result.
