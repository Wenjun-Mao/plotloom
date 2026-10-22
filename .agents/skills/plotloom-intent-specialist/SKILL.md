---
name: plotloom-intent-specialist
description: Deliver one frozen native Plotloom dramatic-intent suggestion package and derived HTML report without changing canon or approvals.
---

# Native intent specialist

Use only the exact package supplied by the coordinator. Read request.json,
COPY_ASSIGNMENT.txt, every inputs/*.json, completion-manifest.example.json and
the local contract named by upstreamSkillPath completely before writing.

Verify checked-out HEAD equals executionPin.upstreamRevision; compare the local
contract SHA256 to upstreamSkillHash and this skill's SHA256 to
specialistSkillHash. On mismatch stop and report the blocker. Do not switch
checkout, model, API provider or credentials to finish the assignment.
Use the coordinator's exact execution directory rather than the chat's original
working directory. Require `git status --porcelain -- src/plotloom
scripts/native_bridge_intent.py docs/creative-workflow/native-bridge-intent.md
.agents/skills/plotloom-intent-specialist` to be empty before executing. Do not
repair or commit execution source yourself.

Author only the sibling delivery/intent.json with apply_patch. Follow the exact
frozen target set and suggestions-only schema. Validate and render from the
repository root using uv run --locked python scripts/native_bridge_intent.py
validate <absolute-intent.json> --request <absolute-package/request.json> and
the same command with render redirected to delivery/report.html. The renderer
owns report derivation. Do not hand-edit it or introduce remote content.

Write completion.json once and last, following the frozen template with actual
hashes, checked-out code revision, contract/skill pin, truthful model/reasoning
when known and limitations. Re-read exact identities, filenames and hashes.
Do not modify any published delivery file, package, source, project state,
approval, selection, media, code or tests. Do not invoke an API, image or video
provider. Do not infer human review or creative acceptance. Report the delivery
path and any limitations through the existing native task completion.
