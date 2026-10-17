---
name: plotloom-image-specialist
description: Deliver one frozen Plotloom P1.5 image or character-reference package with built-in ImageGen, without changing project canon, selections, or application code.
---

# Plotloom Image Specialist

Use this skill only for a single Plotloom package path explicitly supplied by the coordinator. The package is the authority for the task. Do not search for or infer another job.

## Scope and authority

- Read `request.json`, every provided reference image, and `completion-manifest.example.json` before generating.
- A P1.5 shot package may include `character_identity:<characterId>` references. View every such reference before calling ImageGen. Treat the role-to-character mapping as mandatory: preserve durable facial/build/anchor identity, while the frozen shot controls state, clothing, composition, action, and other shot-specific facts.
- When a `character_identity` mapping includes `acceptedCast`, its cast revision,
  hash, and appearance/image direction are frozen identity facts. Apply them
  with the supplied reference; do not silently replace that direction with
  freeform prompt invention. The cast still does not override the frozen shot's
  state, clothing, composition, action, or other shot-specific facts.
- Treat a `character_identity` reference as identity-only: do not transfer its pose, framing, crop, camera, lighting, setting, or action. Honor the frozen shot's requested framing, and do not reframe it or add hands or props outside it merely to make a continuity fact visible.
- A `parent_output` is refinement guidance only. It never replaces `character_identity` references or changes their roles.
- A `scene_continuity` is one frozen reviewed frame from another shot in the same project. View it before ImageGen and retain its scene appearance and object layout only where compatible with the target shot. The target shot/presentation owns action, framing, lighting and current object states. This role is independent of `parent_output` and `character_identity`; it grants no approval, adoption or fidelity claim.
- A `source_keyframe` appears only in a `keyframe_adaptation` package. It is
  the frozen composition that must be extended or recomposed into the exact
  frozen target profile; it is not permission to preserve black padding or to
  change the requested target geometry.
- A character-reference proposal is exploratory. It has no storyboard Approval, Shot, or authority to select a reference; deliver candidates only.
- Use the built-in ImageGen tool. Do not use external image APIs, an API key, browser scraping, or a substitute renderer.

## Required delivery procedure

1. Before ImageGen, run the pin command emitted in `COPY_ASSIGNMENT.txt` from the assigned Plotloom checkout. It validates the configured native task UUID, package binding, P1.5 preflight, schema/package, execution contract, and skill versions; it rejects uncommitted pinned execution code/skill and writes `delivery/executor-pin.json` once with the exact checkout revision, this skill's hash, and `nativeTaskId`. For a configured dispatch, `CODEX_THREAD_ID` must equal the UUID in `nativeTaskBinding.taskId`. A manual copy uses `nativeTaskBinding.mode = current_task`, and binds to the `CODEX_THREAD_ID` running this preflight. Do not generate if preflight fails or if the package pin already exists.
2. Confirm ImageGen is available. If it is unavailable, the package is unreadable, references are missing/tampered, or the request conflicts with these instructions, stop and report the blocking evidence to the coordinator. Do not create a partial completion receipt.
3. Create the requested still with ImageGen from the frozen request and the supplied references. When `requestedGeometry` is present, follow its original-image aspect and target dimensions; preserve returned bytes and disclose actual geometry. For a `keyframe_adaptation`, deliver only the exact `frozenSnapshot.keyframeAdaptation.outputContract.width` × `height` geometry, retain the frozen source keyframe's person, setting and camera intent, and use the `keyframe_adaptation` output role. A `machine_provisional` source has no human visual/identity approval; do not invent reviewed intent or an identity pass. Do not carry black padding into the new still. Do not add characters that are not in `visibleCharacterIds`; do not make off-screen dialogue speakers visible. Do not generate video.
4. The preflight creates private `0700` delivery transaction directories. Capture each exact built-in ImageGen output path returned for this assigned task. A path is eligible for cleanup only when it is a direct, non-symlink child of `$CODEX_HOME/generated_images/$CODEX_THREAD_ID`; never infer paths, glob `generated_images`, or clean a parent directory. Copy selected JPEG/PNG files to `delivery/outputs/` using their returned basenames.
5. Fill `delivery/completion-draft.json` from the example, keeping the identities separate:
   - `toolEvidence.nativeTaskId` must exactly match `nativeTaskId` in `executor-pin.json`;
   - `toolEvidence.imageGenExecutionId` is the distinct execution/output ID returned by ImageGen. Never put that execution ID in the native task field;
   - include the actual prompt and output byte hashes;
   - set `toolEvidence.tool` to exactly `codex_imagegen` and `available` to `true` for a built-in ImageGen run;
   - when the package supplies `character_identity` or `scene_continuity` references, set `referenceUse.viewedReferenceHashes` to exactly their frozen hashes and add concise role-aware notes; omit `referenceUse` when it supplies neither;
   - copy `executorProvenance.codeRevision`, `skillVersion`, and `skillHash` from the executor pin; record model/reasoning fields only when actually known.
6. Publish once using the command emitted in `COPY_ASSIGNMENT.txt`. The publisher validates the native task binding, distinct ImageGen execution ID, manifest, output set, and hashes before it writes `delivery/completion.json` as the final marker. Do not create or edit `completion.json` by hand, rerun the publisher after success, or alter a completed manifest/output.
7. After publication, run `uv run --locked --no-sync python scripts/cleanup_imagegen_staging.py --package "<package-path>" --staging-root "$CODEX_HOME/generated_images/$CODEX_THREAD_ID" --staged "<exact-returned-output-path>"` once, including one separately quoted `--staged "<exact-returned-output-path>"` argument for every declared output. The helper copies only missing matching outputs, validates the manifest identity, exact output set, and byte hashes, then removes only those exact source files. If it refuses or reports leftovers, preserve every staging file and report the paths/reasons to the coordinator. A missing staged file is idempotent only after its matching durable delivery output validates.
8. Re-read the final manifest and compare its `jobId` and `requestHash` to `request.json`. The only success signal is a complete, hash-valid delivery receipt. Tell the coordinator the package and completion paths plus cleanup result; do not claim Approval, reference selection, or a reviewed keyframe.

## Prohibitions

- Do not modify `request.json`, template files, references, the exchange package, app source, migrations, tests, generated frontend assets, `.env`, credentials, or canonical content.
- Do not auto-select a candidate, approve a storyboard, create a Shot, infer identity from a name, or claim a face-recognition result.
- Do not treat a failed generation, an unsupported request, or missing reference evidence as permission to weaken the manifest contract.
- Do not delete a tool-staging path before a complete manifest and matching project-local delivery exist. Preserve user-provided inputs, ambiguous ownership, active references, failures, incomplete deliveries, and different bytes.
- Same-UID hostile writers are outside this same-host specialist contract. Other cooperating writers must finish and release the private task directories before the cleanup helper's locked verify/copy/unlink transaction.
