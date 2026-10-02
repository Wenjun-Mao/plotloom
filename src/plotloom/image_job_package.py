"""Pure frozen image-package projection and specialist delivery instructions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .image_job_contracts import ImageJobError

PACKAGE_VERSION = 3
PINNED_PACKAGE_VERSION = 4
COMPLETION_TEMPLATE_FILENAME = "completion-manifest.example.json"
OUTPUT_BASENAME_INSTRUCTION = (
    "Copy each selected ImageGen JPEG or PNG unchanged using its exact returned basename; "
    "declare that same basename in outputs[].filename. The completion template filenames "
    "are placeholders, never required output names. "
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def package_version(request: dict[str, Any]) -> int:
    """Keep copied v1 packages readable while making v2 self-contained."""

    schema_version = request.get("schemaVersion")
    if schema_version == 1:
        return 1
    if schema_version == 2:
        return 2
    if schema_version == 3:
        return PINNED_PACKAGE_VERSION if request.get("specialistPreflight", {}).get("version") == "p1.5-pin.v1" else PACKAGE_VERSION
    raise ImageJobError("request_integrity", "frozen image request schema is unsupported")


def project_image_package(
    *,
    root: Path,
    job_id: str,
    request: dict[str, Any],
    request_hash: str,
    reference_entries: list[dict[str, str]],
) -> tuple[dict[str, Any], bytes, bytes | None, set[str]]:
    """Derive the complete, recheckable package from frozen database data."""

    version = package_version(request)
    job_root = root / "jobs" / job_id
    package = job_root / "package"
    if version == 1:
        delivery_instruction = (
            "Write complete JPEG or PNG files to delivery/outputs, then publish delivery/completion.json once. "
            "Do not write SQLite, modify this package, or include sensitive values."
        )
        instructions = (
            f"Plotloom image job {job_id}\n"
            f"Read: {package / 'request.json'}\n"
            f"Deliver only under: {job_root / 'delivery'}\n"
            "Use Codex built-in image generation. Preserve the supplied narrative facts, disclose the actual prompt, "
            "and publish completion.json only after every declared output is complete.\n"
        ).encode()
        template: bytes | None = None
    elif version == 2:
        delivery_instruction = (
            "Read completion-manifest.example.json before preparing delivery. Write complete JPEG or PNG files to "
            "delivery/outputs. "
            + OUTPUT_BASENAME_INSTRUCTION
            + "Then use that exact field shape to publish delivery/completion.json once. Do not write "
            "SQLite, modify this package, or include sensitive values."
        )
        instructions = (
            f"Plotloom image job {job_id}\n"
            f"Read: {package / 'request.json'}\n"
            f"Read completion template: {package / COMPLETION_TEMPLATE_FILENAME}\n"
            f"Deliver only under: {job_root / 'delivery'}\n"
            "Use Codex built-in image generation. The request contains the frozen creator direction, selected reviewed "
            "VisualIntent when this is a refinement, and the resolved authored shot context. Preserve those facts. "
            + OUTPUT_BASENAME_INSTRUCTION
            + "Disclose the exact actual prompt, and publish completion.json only after every declared output is complete.\n"
        ).encode()
        template = canonical_json({
            "schemaVersion": 1,
            "jobId": job_id,
            "requestHash": request_hash,
            "deliveryId": "replace-with-specialist-delivery-id",
            "actualPrompt": "replace-with-the-exact-prompt-submitted-to-Codex-imagegen",
            "outputs": [{
                "filename": "replace-with-exact-returned-basename.png",
                "sha256": "0" * 64,
                "role": request.get("kind", "original"),
            }],
            "toolEvidence": {
                "tool": "codex_imagegen",
                "taskId": "replace-with-Codex-task-id",
                "available": True,
            },
            "limitations": [],
        })
    else:
        proposal = request.get("target") in {
            "character_reference_proposal", "art_reference_proposal"
        }
        art_reference = request.get("target") == "art_reference_proposal"
        adaptation = request.get("kind") == "keyframe_adaptation"
        adaptation_contract = request.get("frozenSnapshot", {}).get("keyframeAdaptation", {}).get("outputContract", {})
        adaptation_instruction = (
            f" Adapt the supplied source_keyframe into one complete {adaptation_contract.get('width')}x{adaptation_contract.get('height')} "
            "composition. Preserve the reviewed person, setting, and camera intent; do not preserve, add, or treat padding as content. "
            "Every delivered output must use that exact geometry and the keyframe_adaptation role. "
            if adaptation else ""
        )
        delivery_instruction = (
            "Read completion-manifest.example.json before preparing delivery. "
            + (
                "View every role-mapped character_identity reference before generation and report its hashes in referenceUse. "
                if not proposal else
                (
                    "This is an exploratory art-reference study; it cannot replace accepted art or create a creative approval. "
                    if art_reference else
                    "This is an exploratory character-reference proposal; it cannot approve or select a reference. "
                )
            )
            + adaptation_instruction
            + OUTPUT_BASENAME_INSTRUCTION
            + "Write complete JPEG or PNG files to delivery/outputs, then publish delivery/completion.json once. Do not write "
            "SQLite, modify this package, or include sensitive values."
        )
        instructions = (
            f"Plotloom {'art-reference study' if art_reference else 'character-reference proposal' if proposal else 'identity-aware image job'} {job_id}\n"
            f"Read: {package / 'request.json'}\n"
            f"Read completion template: {package / COMPLETION_TEMPLATE_FILENAME}\n"
            + (f"Before ImageGen, run: uv run python scripts/pin_image_specialist.py --package {package}\n" if version == PINNED_PACKAGE_VERSION else "")
            + f"Deliver only under: {job_root / 'delivery'}\n"
            + (
                "Use Codex built-in image generation. View every supplied character_identity reference and preserve "
                "that person. When characterIdentity[].acceptedCast is present, preserve its appearance/image direction "
                "as cast-owned identity facts; do not replace it with freeform invention. The frozen canonical shot state "
                "still controls costume, pose, expression, lighting, and camera. parent_output is a separate edit guide "
                "and never replaces character identity. "
                if not proposal else
                (
                    "Use Codex built-in image generation for the frozen accepted-art subject. This result is an "
                    "exploratory candidate only: do not claim currentness, art acceptance, or a selected production asset. "
                    if art_reference else
                    "Use Codex built-in image generation for the frozen Story Bible character context. This result is an "
                    "exploratory candidate only: do not claim an approved Shot, storyboard Approval, or selected reference. "
                )
            )
            + adaptation_instruction
            + OUTPUT_BASENAME_INSTRUCTION
            + "Disclose the "
            "exact actual prompt and publish completion.json only after every declared output is complete.\n"
        ).encode()
        template_payload: dict[str, Any] = {
            "schemaVersion": 2,
            "jobId": job_id,
            "requestHash": request_hash,
            "deliveryId": "replace-with-specialist-delivery-id",
            "actualPrompt": "replace-with-the-exact-prompt-submitted-to-Codex-imagegen",
            "outputs": [{
                "filename": "replace-with-exact-returned-basename.png",
                "sha256": "0" * 64,
                "role": request.get("kind", "original"),
            }],
            "toolEvidence": {
                "tool": "codex_imagegen",
                "taskId": "replace-with-Codex-task-id",
                "available": True,
            },
            "executorProvenance": {
                "codeRevision": "replace-with-pinned-commit",
                "skillVersion": request.get("specialistPreflight", {}).get("skillVersion", "plotloom-image-specialist.v1"),
                "skillHash": "0" * 64,
                "model": None,
                "reasoningEffort": None,
            },
            "limitations": [],
        }
        if any(item["role"].startswith("character_identity") for item in reference_entries):
            template_payload["referenceUse"] = {
                "viewedReferenceHashes": ["replace-with-every-character-identity-hash"],
                "identityNotes": "describe how identity was preserved; this attestation is not creator approval",
            }
        template = canonical_json(template_payload)
    package_request = dict(request)
    package_request.update({
        "packageVersion": version,
        "requestHash": request_hash,
        "references": reference_entries,
        "deliveryInstruction": delivery_instruction,
    })
    expected_entries = {"request.json", "COPY_ASSIGNMENT.txt"}
    if template is not None:
        expected_entries.add(COMPLETION_TEMPLATE_FILENAME)
    if reference_entries:
        expected_entries.add("references")
    return package_request, instructions, template, expected_entries
