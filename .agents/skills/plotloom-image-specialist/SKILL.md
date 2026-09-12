---
name: plotloom-image-specialist
description: Deliver one frozen Plotloom P1.5 image or character-reference package with built-in ImageGen, without changing project canon, selections, or application code.
---

# Plotloom Image Specialist

Use this skill only for a single Plotloom package path explicitly supplied by the coordinator. The package is the authority for the task. Do not search for or infer another job.

## Scope and authority

- Read `request.json`, every provided reference image, and `completion-manifest.example.json` before generating.
- A P1.5 shot package may include `character_identity:<characterId>` references. View every such reference before calling ImageGen. Treat the role-to-character mapping as mandatory: preserve durable facial/build/anchor identity, while the frozen shot controls state, clothing, composition, action, and other shot-specific facts.
- A `parent_output` is refinement guidance only. It never replaces `character_identity` references or changes their roles.
- A character-reference proposal is exploratory. It has no storyboard Approval, Shot, or authority to select a reference; deliver candidates only.
- Use the built-in ImageGen tool. Do not use external image APIs, an API key, browser scraping, or a substitute renderer.

## Required delivery procedure

1. Confirm ImageGen is available. If it is unavailable, the package is unreadable, references are missing/tampered, or the request conflicts with these instructions, stop and report the blocking evidence to the coordinator. Do not create a partial completion receipt.
2. Create the requested still with ImageGen from the frozen request and the supplied references. Do not add characters that are not in `visibleCharacterIds`; do not make off-screen dialogue speakers visible. Do not generate video.
3. Write only JPEG or PNG outputs below the package’s `delivery/outputs/` directory. Do not edit source code, database files, canonical story data, package inputs, or any path outside the delivery directory.
4. Copy the manifest example to `delivery/completion.json` and fill it truthfully:
   - actual prompt and output byte hashes;
   - the manifest's normalized `toolEvidence.tool` value, exactly
     `codex_imagegen`, for a built-in ImageGen run. It is the package contract
     label, not the raw runtime tool identifier; retain the actual task ID and
     `available: true` alongside it;
   - `referenceUse.viewedReferenceHashes` containing exactly the frozen hashes for every `character_identity` reference, plus concise role-aware notes;
   - `executorProvenance.codeRevision` from the checked-out commit and `skillHash` from this `SKILL.md`; record model/reasoning fields only when actually known.
5. Re-read the final manifest and compare its `jobId` and `requestHash` to `request.json`. The only success signal is a complete, hash-valid delivery receipt. Tell the coordinator the package and completion paths; do not claim Approval, reference selection, or a reviewed keyframe.

## Prohibitions

- Do not modify `request.json`, template files, references, the exchange package, app source, migrations, tests, generated frontend assets, `.env`, credentials, or canonical content.
- Do not auto-select a candidate, approve a storyboard, create a Shot, infer identity from a name, or claim a face-recognition result.
- Do not treat a failed generation, an unsupported request, or missing reference evidence as permission to weaken the manifest contract.
