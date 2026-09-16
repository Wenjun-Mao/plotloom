# Step 4 retained playback and recovery proof

Captured 2026-09-16 UTC against the accepted source candidate `ab7fc46` and
retained project `fef96fc8-86f8-4132-91bd-32d58f5bb504`. This is operational
proof for the retained two-clip fragment only. It is not a claim that Codex
heard audio, that either clip has dialogue or lip-sync, that the whole route is
complete, or that the product, Alpha, or release is accepted.

## Retained selected media and review lineage

| Job | Frozen shot / scene | Stored SHA-256 | Persisted selected video review (`v2_video_reviews.id`) |
| --- | --- | --- | --- |
| `vj_86676092a8e84516922f650838c752e0` | `44598e70-49fc-519e-b71d-5c99f51dcd90` / `174495ff-40eb-5ba9-9840-c3027b95b1d5` | `1e95ed45f20f6287f6686a246f1e0164db6dd549d87472e30b1437cbd6302dc6` | `f7d7195f-69d1-4c7e-ba7c-a713017f5d85` |
| `vj_fffbcebbca8945fc99dbae42863f70b2` | `97c4a139-57fa-52b0-bf19-2dd5ef018391` / `5f0f0ba2-3515-5595-a797-5e2ad415a77b` | `45079df8f791cc3d32440b507a3c5d063bc52caf98ae750be216c22435b8854d` | `05ee01c0-039e-43eb-b05c-6a74617f5f27` |

Director acceptance checked these selected video review IDs directly in both
original and restored databases. The earlier table mistakenly listed the
distinct same-person keyframe reviews; no persisted review data was changed.

Both jobs read as `ingested`, `current`, and selected before and after
recovery. Their frozen `cueIds` are empty: the first carries distant-train
ambience and the second distant-train/light-wind ambience. The retained human
review attribution remains intact; this receipt does not turn that attribution
into a Codex audiovisual judgment.

## Publication disposition and native playback

Read-only inspection found the incompatible exact-size image job
`ij_c6f81e5fd28441d7abf2a34e129221d9` in `exported` state with no delivery
receipt or current writer. It alone was cancelled once through the normal API
at `2026-09-16T00:27:29.223776+00:00`, with the exact reason
`incompatible exact-size adaptation abandoned in favor of approved gateway crop`.
It then read `cancelled`, non-current, and with zero deliveries; both delivered
image jobs remained current with their one delivery each. No late publication
was processed.

In Chrome, I selected the valid graph route `路径 2 · 拾起怀表 → 放入内袋 →
放入内袋`. The product projected the two selected clips in order, `深夜站台等待
→ 发现微光与犹豫`, and honestly reported four missing route clips: `拾起与凝视`、
`凝视照片与无声承诺`、`凝视与抉择`、`郑重放入`. Native playback automatically
advanced from clip 1/2 to 2/2. At completion Chrome showed the second clip's
5.167-second scrubber position and the product reported its final frame held
until an explicit restart; previous was enabled and next disabled. Chrome's
`Audio playing` indicator is browser-playback evidence only, not evidence that
Codex heard or evaluated sound.

## Close, snapshot, isolated restore

The normal production close and reopen routes returned revisions 2 and 3.
Exactly one authorized product recovery snapshot was then created:

- ID: `297e8319-fd17-48c9-8b00-fa2cffcafaae`
- source: `outputs/.snapshots/fef96fc8-86f8-4132-91bd-32d58f5bb504/20260916T002902088877Z__297e8319-fd17-48c9-8b00-fa2cffcafaae`
- manifest: project format version 8, 32 files

This is the authorized recovery copy, not an additional backup or archive. It
was restored into the ignored project-local Relay root
`.local/relay/77eb3db4-9e0f-42c1-9375-f174c9d7662d/recovery-proof/outputs`.
The isolated runtime ran with its H3 gateway disabled, so it could not dispatch
new video work. Its API retained both selected jobs, their stored hashes,
frozen shot/scene identities, and selected-review IDs; normal range serving
returned `206` for retained video bytes. Chrome also played a restored selected
clip through its native controls (again, playback evidence only).

## Boundary and disposition

No ImageGen, upload, generation, provider, reservation, dispatch, profile,
configuration, deployment, or unrelated project change occurred. The source
candidate was not changed; this continuation records the authorized
operational evidence only.

Step 4 is complete for its approved retained two-clip playback and recovery
deliverable. The four missing clips and a complete branching player remain
Step 5 work under separate authorization.

### Verification

- Retained and restored API reads matched both selected job IDs, review lineage,
  frozen identities, and listed stored SHA-256 values; retained media range
  requests returned `206`.
- Chrome observed the explicit-route transition and final-frame hold on the
  production runtime, then native restored-media playback on the isolated
  runtime.
- No broad suite was run: this was a docs-only operational continuation on the
  already accepted source candidate.
