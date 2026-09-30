# H3 ComfyUI 0.38 maintenance adoption

**Result:** The separately authorized corrected landscape pair passed, and
ComfyUI 0.38.0 is now live on Spark. The old image, stopped container and original
user directory remain available for rollback. No merge, push or director contact.

This is a bounded maintenance adoption, not a claim of generally better video
quality, all-geometry qualification, or a repair for Voice Lab's CUDA failure.
The [original five-call receipt](2026-09-30-h3-comfy038-runtime-qualification.md)
remains historical evidence, including its input-selection mistake.

## Authority and corrected comparison

After the owner reported no noticeable quality difference across the displayed
original pairs, the proposed next step was one corrected landscape pair followed
by maintenance adoption if it passed. The owner replied “agreed”. The
[plan addendum](../roadmap/2026-09-30-h3-comfy038-runtime-qualification.md)
limits this follow-up to **two submissions total**, one per runtime. Both were
used; no failure, unknown outcome, replay or additional call occurred.

The original padded doorway still did not match its astronaut prompt. The
correction uses frame 62 of the original candidate landscape video: a clean
1280×704 spacecraft still, extracted without resizing, cropping or padding.
The operator inspected the actual pixels before freeze: seated female astronaut,
white suit/helmet, cabin and Earth through the window. The new prompt matches
that scene. This is a convenient matched regression input, not independent
evidence of general scene quality. Original cases and receipts were not changed.

Both new runs used quality 1, V1.2 Turbo4/Euler/6/3, seed `20260930`, 124 frames,
the same image/prompt and normalized graph hash
`a561efdb37a1544cfa2626571a2598675462e6ff5d2c105bda68e2f13970a831`.
Each runtime was freshly started; both cache lists are empty.

| Check | ComfyUI 0.35 baseline | ComfyUI 0.38 candidate |
| --- | --- | --- |
| Backend elapsed | 198.188 s | 162.132 s |
| Output | 1280×704, 124 H.264 frames, 24 fps | Same |
| Native audio | AAC, 32 kHz | Same |
| Container duration | 5.167 s | Same |
| Full video/audio stream decode | Passed | Passed |

The single corrected pair was approximately 18% faster. This is an observation,
not a throughput benchmark. Three matched sampled frames and additional
candidate sequence frames showed no material visual regression, scene inset,
new visible subtitle, or obvious seam. Whole-video human review of this new pair
has not been recorded; the owner's no-difference report concerns the original
displayed pairs. Neither constitutes a general motion, acting or voice guarantee.

Genuine receipts: [baseline](supporting/h3-runtime-038-corrected-landscape-2026-09-30/baseline-receipt.json)
and [candidate](supporting/h3-runtime-038-corrected-landscape-2026-09-30/candidate-receipt.json).
The [input binding](supporting/h3-runtime-038-corrected-landscape-2026-09-30/input-binding.json)
records the reviewed still hash and extraction provenance without prompt bodies.
The private review page now includes the corrected pair first:
`/Users/wjmao/plotloom-canaries/2026-09-30-h3-runtime-038/index.html#corrected-landscape`.
Media remain untracked; no packages were added to Downloads.

## Catalog disposition and promotion

Read-only inspection found no production asset rows, references, metadata or
tag bindings, but 24 standalone tag definitions. There was no identified bound
user metadata to migrate. Nevertheless, the original catalog was **not** upgraded
in place or deleted: a quiescent `cp -a` copy became `data/user-v038`, and only
that copy migrated from `0006_add_loader_path` to `0008_drop_asset_meta`.
Both SQLite integrity checks pass. The new catalog has zero asset/tag rows;
the original retains all 24 tag definitions. This disposition is specific to
this empty catalog, not permission to discard another installation's metadata.

Promotion rechecked idle Comfy, gateway and Voice Lab queues, completed frozen
receipts, exact candidate identity and available preservation targets. It
preserved the old container as `spark-comfyui-v035-rollback-20260930` and started
the tested image as `spark-comfyui` with the stable new user mount. Input, output,
model and cache mounts, GPU stack, runtime policy and checkpoint/LoRA/recipe
contracts were unchanged. `spark-comfyui:latest` now identifies the tested image;
the preserved baseline tag still identifies the old image.

Current deployment and rollback identities are in the
[runtime overlay manifest](../../services/minimax_h3_gateway/h3-runtime-038-adoption.v1.yaml).
The reproduction guide includes the separate mount configuration and exact
[rollback procedure](../../services/minimax_h3_gateway/docs/h3-reproducible-setup.md#7-update-rollback-and-reboot).
The original installation inventory is deliberately not rewritten.

## Restoration and verification

The adopted container passed a real `docker restart` smoke check with the same
image, Comfy commit and mount. It is healthy with `unless-stopped`; this was not
a host reboot test. Gateway, Voice Lab and Qwen Image returned `ok`; the gateway
reported voice-reference readiness and zero queued/active jobs. Comfy was empty.
Embedding and comment-playground containers were left running throughout.

Voice Lab SQLite remains intact: creation 5 completed/1 failed, reuse 9
completed/1 failed, and two published voices whose source/H3 file hashes match
their stored hashes. No voice selection or regeneration was performed.
The [adoption proof](supporting/h3-runtime-038-corrected-landscape-2026-09-30/adoption-proof.json)
captures those checks. Stopped containers' cached health fields are not live
readiness assertions; the original baseline had already passed its restored
readiness check before this transition.

The independent read-only reviewer found no material issue in the two-call
scope, frozen hashes, call-cap admission, candidate mount isolation or rollback
preservation. The follow-up added an explicit candidate-user argument and a
bounded call cap to the operator harness, plus a separate correction entrypoint;
the original default five-call behavior is unchanged.

Executed focused locked Python checks for runtime qualification, prompt-study
guards and voice references: **43 passed**, one existing Starlette deprecation
warning. Scoped Ruff, build-wrapper shell syntax, receipt JSON/hash assertions,
relative documentation links, review-page media links and patch checks passed.
Full Python/frontend/E2E/wheel gates were not rerun: this changes operator tools
and documentation, not shipped gateway/frontend/package behavior.

**Closed:** bounded runtime maintenance adoption. **Still open:** broader
co-resident memory reliability and the separately scoped Voice Lab CUDA issue.
No additional inference, model switch, Plotloom integration or director delivery
is authorized by this receipt.
