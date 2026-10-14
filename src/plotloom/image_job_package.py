"""Pure frozen image-package projection and specialist delivery instructions."""

from __future__ import annotations

import json
from pathlib import Path
from shlex import quote
from typing import Any

from .image_job_contracts import ImageJobError, NativeTaskBinding

PACKAGE_VERSION = 3
PINNED_PACKAGE_VERSION = 4
PRESENTATION_PACKAGE_VERSION = 5
IDENTITY_PACKAGE_VERSION = 6
CODEX_EXEC_PACKAGE_VERSION = 8


def presentation_amendment_instruction(request: dict) -> str:
    decision = request.get("frozenSnapshot", {}).get("shotPresentation")
    if decision is None:
        return ""
    instruction = ("The source-bound shotPresentation explicitly amends physical presentation. "
                   "Use its effectiveShot and review as authority; source is retained evidence, never active direction. ")
    if decision["review"]["messagePresentation"] != "source":
        instruction += ("The first image shows a large front-facing popped-out preview outside the phone with "
                        "the complete exact UNSENT draft already present. The phone has no readable text. "
                        "Sending belongs to subsequent video action, never the first image; no already-sent first image. ")
    return instruction


def runtime_presentation_instruction(request: dict) -> str:
    if request.get("frozenSnapshot", {}).get("shotPresentation") is None:
        # Retained, immutable packages must still re-project byte-for-byte.
        return "Never generate player choice questions, option buttons or UI; runtime owns that presentation. "
    return (
        "Never generate runtime branching-choice UI, including player choice questions or branch-option buttons; "
        "runtime owns that presentation. Depict only the authored or explicitly reviewed message/interface treatment. "
        "Render message words only from the frozen visibleTexts, preserving them exactly; "
        "do not invent additional message text or replies. "
        "Nonverbal interface cues must follow the frozen physical presentation. "
    )


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
        preflight_version = request.get("specialistPreflight", {}).get("version")
        if preflight_version == "p1.5-pin.v2":
            contract = request.get("specialistPreflight", {}).get("executionContract")
            if request.get("executionContract") != contract:
                raise ImageJobError(
                    "request_integrity",
                    "image request and specialist preflight execution contracts differ",
                )
            if contract == "codex_exec.v1":
                return CODEX_EXEC_PACKAGE_VERSION
            if contract == "codex_specialist.v3":
                return IDENTITY_PACKAGE_VERSION
            raise ImageJobError("request_integrity", "image request execution contract is unsupported")
        if request.get("frozenSnapshot", {}).get("presentationContract") == "physical-visible-runtime.v1":
            return PRESENTATION_PACKAGE_VERSION
        return PINNED_PACKAGE_VERSION if preflight_version == "p1.5-pin.v1" else PACKAGE_VERSION
    raise ImageJobError("request_integrity", "frozen image request schema is unsupported")


def codex_exec_reference_view_instruction(package: Path, references: list[dict[str, str]]) -> str:
    """Bind each required source view to its exact package path and image emission call."""
    if not references:
        return (
            "No frozen reference files are supplied. Do not call view_image and omit referenced_image_paths from ImageGen. "
        )
    entries = []
    paths = []
    for item in references:
        if set(item) != {"role", "filename", "sha256"}:
            raise ImageJobError("request_integrity", "Codex Exec package reference has an unsupported shape")
        absolute = package / item["filename"]
        paths.append(json.dumps(str(absolute), ensure_ascii=False))
        entries.append(f"- {item['role']}: {absolute}\n")
    calls = "".join(
        f"{index}. `image((await tools.view_image({{path: {path}}})).image_url);`\n"
        for index, path in enumerate(paths, 1)
    )
    return (
        "Before ImageGen, emit every frozen reference as image content, once each and in this package order. "
        "For each entry, make one separate exec call with the exact expression below, and wait for its result:\n"
        + "".join(entries)
        + calls
        + "Pass these same absolute paths, in the same order, to ImageGen's referenced_image_paths argument. "
        "A path argument alone is not a view; do not describe or print a reference instead of emitting its image. "
    )


def project_image_package(
    *,
    root: Path,
    job_id: str,
    request: dict[str, Any],
    request_hash: str,
    reference_entries: list[dict[str, str]],
    native_task_binding: NativeTaskBinding | dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes, bytes | None, set[str]]:
    """Derive the complete, recheckable package from frozen database data."""

    version = package_version(request)
    repository_root = Path(__file__).resolve().parents[2]
    binding: dict[str, Any] | None = None
    if version == IDENTITY_PACKAGE_VERSION:
        try:
            parsed_binding = NativeTaskBinding.model_validate(native_task_binding)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "image_native_task_binding_invalid",
                "new image packages require an explicit native task binding",
            ) from error
        if request.get("executionContract") != "codex_specialist.v3":
            raise ImageJobError("request_integrity", "native task binding requires codex_specialist.v3")
        binding = parsed_binding.model_dump(mode="json", by_alias=True, exclude_none=True)
    elif version == CODEX_EXEC_PACKAGE_VERSION:
        if request.get("executionContract") != "codex_exec.v1" or native_task_binding is not None:
            raise ImageJobError("request_integrity", "Codex Exec image packages cannot carry a native chat binding")
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
            "composition. Preserve the frozen person, setting, and camera intent; do not preserve, add, or treat padding as content. "
            "Every delivered output must use that exact geometry and the keyframe_adaptation role. "
            if adaptation else ""
        )
        delivery_instruction = (
            ("The trusted host publishes completion.json from the exact CLI session and output bytes. "
             if version == CODEX_EXEC_PACKAGE_VERSION else
             "Read completion-manifest.example.json before preparing delivery. ")
            + (
                codex_exec_reference_view_instruction(package, reference_entries)
                if version == CODEX_EXEC_PACKAGE_VERSION else
                "View every role-mapped character_identity reference before generation and report its hashes in referenceUse. "
                if not proposal else
                (
                    "This is an exploratory art-reference study; it cannot replace accepted art or create a creative approval. "
                    if art_reference else
                    "This is an exploratory character-reference proposal; it cannot approve or select a reference. "
                )
            )
            + adaptation_instruction
            + (f"Produce one unchanged original with aspect {request['frozenSnapshot']['requestedGeometry']['aspectRatio']}, "
               f"targeting {request['frozenSnapshot']['requestedGeometry']['width']}x{request['frozenSnapshot']['requestedGeometry']['height']}. "
               "Disclose actual geometry; do not crop or pad outputs. This is an AI provisional material, without human visual or identity approval. "
               if not adaptation and request.get("frozenSnapshot", {}).get("requestedGeometry") else "")
            + ("Use the frozen shot action/composition and resolved visibleEvent fields as physical presentation authority. "
               "visibleTexts are exact nonspoken diegetic words: preserve their original text in the image. "
               + presentation_amendment_instruction(request)
               + runtime_presentation_instruction(request)
               + "No text compositor is implied by this request; disclose any inability to render the exact authored words. "
               if version in {PRESENTATION_PACKAGE_VERSION, CODEX_EXEC_PACKAGE_VERSION} or (
                   version == IDENTITY_PACKAGE_VERSION
                   and request.get("frozenSnapshot", {}).get("presentationContract") == "physical-visible-runtime.v1"
               ) else "")
            + OUTPUT_BASENAME_INSTRUCTION
            + (
                "Do not write image files or completion markers into delivery. The trusted Codex Exec host "
                "copies the exact image bytes from the completed built-in ImageGen session event into "
                "delivery/outputs and publishes completion.json after validating the event, arguments and "
                "output bytes. Do not "
                if version == CODEX_EXEC_PACKAGE_VERSION else
                "Write complete JPEG or PNG files to delivery/outputs. Prepare delivery/completion-draft.json, "
                "then publish it exactly once with the command in COPY_ASSIGNMENT.txt; the publisher verifies the "
                "native task and ImageGen execution IDs and writes completion.json last. Do not write "
                if version == IDENTITY_PACKAGE_VERSION else
                "Write complete JPEG or PNG files to delivery/outputs, then publish delivery/completion.json once. "
                "Do not write "
            )
            + "SQLite, modify this package, or include sensitive values."
        )
        instructions = (
            f"Plotloom {'art-reference study' if art_reference else 'character-reference proposal' if proposal else 'identity-aware image job'} {job_id}\n"
            f"Read: {package / 'request.json'}\n"
            + (f"Read completion template: {package / COMPLETION_TEMPLATE_FILENAME}\n" if version != CODEX_EXEC_PACKAGE_VERSION else "")
            + (
                f"Before ImageGen, run: uv run python scripts/pin_image_specialist.py --package {package}\n"
                if version in {PINNED_PACKAGE_VERSION, PRESENTATION_PACKAGE_VERSION} and request.get("specialistPreflight")
                else f"Before ImageGen, run: uv run --locked --no-sync python {quote(str(repository_root / 'scripts' / 'pin_image_specialist.py'))} --package {quote(str(package))}\n"
                if version == IDENTITY_PACKAGE_VERSION and request.get("specialistPreflight")
                else ""
            )
            + f"Deliver only under: {job_root / 'delivery'}\n"
            + (codex_exec_reference_view_instruction(package, reference_entries) + "\n"
               if version == CODEX_EXEC_PACKAGE_VERSION else "")
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
                    "Use Codex built-in image generation for the frozen accepted Cast characterContext and visualDirection. "
                    "View every supplied parent_output before generation. It is an explicit editing input that may show an "
                    "older design; the frozen accepted Cast appearance/image direction owns the current design. "
                    "Do not load a Story Bible or revive the parent's old proposal. This result is an "
                    "exploratory candidate only: do not claim an approved Shot, storyboard Approval, or selected reference. "
                )
            )
            + adaptation_instruction
            + ("Use the frozen shot action/composition and resolved visibleEvent fields as physical presentation authority. "
               "visibleTexts are exact nonspoken diegetic words: preserve their original text in the image. "
               + presentation_amendment_instruction(request)
               + runtime_presentation_instruction(request)
               + "No text compositor is implied by this request; disclose any inability to render the exact authored words. "
               if version in {PRESENTATION_PACKAGE_VERSION, CODEX_EXEC_PACKAGE_VERSION} or (
                   version == IDENTITY_PACKAGE_VERSION
                   and request.get("frozenSnapshot", {}).get("presentationContract") == "physical-visible-runtime.v1"
               ) else "")
            + OUTPUT_BASENAME_INSTRUCTION
            + (
                "Disclose the exact actual prompt. "
                f"Complete {job_root / 'delivery' / 'completion-draft.json'} from the template, then publish with: "
                f"uv run --locked --no-sync python {quote(str(repository_root / 'scripts' / 'publish_image_completion.py'))} "
                f"--package {quote(str(package))} --manifest {quote(str(job_root / 'delivery' / 'completion-draft.json'))}\n"
                if version == IDENTITY_PACKAGE_VERSION else
                "Do not write image files or completion markers into delivery. The trusted host records the exact "
                "literal ImageGen prompt, reference arguments and completion event. The trusted Codex Exec host "
                "copies the exact image bytes from that event into delivery/outputs and publishes completion.json "
                "after validating the event, arguments and output bytes. "
                "Do not create a completion manifest, executor pin or extra delivery files.\n"
                if version == CODEX_EXEC_PACKAGE_VERSION else
                "Disclose the exact actual prompt and publish completion.json only after every declared output is complete.\n"
            )
        ).encode()
        parsed_binding = NativeTaskBinding.model_validate(native_task_binding) if version == IDENTITY_PACKAGE_VERSION else None
        binding_id = str(parsed_binding.task_id) if parsed_binding and parsed_binding.task_id else "replace-with-CODEX_THREAD_ID-from-the-pinned-native-task"
        template_payload: dict[str, Any] = {
            "schemaVersion": 3 if version == IDENTITY_PACKAGE_VERSION else 2,
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
                **(
                    {
                        "nativeTaskId": binding_id,
                        "imageGenExecutionId": "replace-with-ImageGen-execution-id-not-native-task-id",
                    }
                    if version == IDENTITY_PACKAGE_VERSION else
                    {"taskId": "replace-with-Codex-task-id"}
                ),
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
        template = None if version == CODEX_EXEC_PACKAGE_VERSION else canonical_json(template_payload)
    package_request = dict(request)
    package_request.update({
        "packageVersion": version,
        "requestHash": request_hash,
        "references": reference_entries,
        "deliveryInstruction": delivery_instruction,
    })
    if binding is not None:
        package_request["nativeTaskBinding"] = binding
    if version == CODEX_EXEC_PACKAGE_VERSION:
        package_request["executorBackend"] = "codex_exec"
    expected_entries = {"request.json", "COPY_ASSIGNMENT.txt"}
    if template is not None:
        expected_entries.add(COMPLETION_TEMPLATE_FILENAME)
    if reference_entries:
        expected_entries.add("references")
    return package_request, instructions, template, expected_entries
