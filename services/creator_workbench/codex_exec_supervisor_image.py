"""Image evidence validation and trusted output copying for the Mac supervisor."""
from __future__ import annotations

import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

from codex_exec_supervisor_errors import CodexExecSupervisorError


@dataclass(frozen=True)
class _ImageAttemptCompletion:
    outputs: tuple
    image_facts: tuple
    remote_state: str
    reference_views: tuple
    image_call: object
    image_event: object
    reference_hashes: tuple


class CodexExecSupervisorImageMixin:
    def _complete_image_attempt(
        self, attempt, profile, package_request, job_root, environment, stream, session,
        current, exit_code, stdout_path, stderr_path,
    ):
        from plotloom.codex_exec_contracts import (
            CodexExecImageEvidence,
            image_arguments_hash,
        )
        from plotloom.codex_exec_files import scan_regular_tree
        from plotloom.codex_exec_runtime import (
            CodexExecRuntimeError,
            read_generated_image,
        )

        if attempt.reserved_image_outputs != 1 or len(session.image_calls) != 1 or len(session.image_events) != 1:
            raise CodexExecRuntimeError("serial image attempt did not produce exactly one ImageGen event")
        image_call, image_event = session.image_calls[0], session.image_events[0]
        if image_event.status != "completed" or image_event.saved_path is None:
            self._finish_failure(
                current, exit_code, stream.session_id, session, stdout_path, stderr_path,
                remote_state="failed", max_output_bytes=profile.max_output_bytes,
            )
            return None
        reference_hashes = self._match_image_references(job_root, package_request, image_call.reference_paths)
        reference_views = self._match_image_reference_views(
            job_root, package_request, session.reference_views, image_call
        )
        content, image_hash = read_generated_image(
            Path(image_event.saved_path),
            codex_home=self._codex_home(environment),
            session_id=stream.session_id,
            max_bytes=profile.max_output_bytes,
        )
        self._copy_image_to_delivery(job_root, Path(image_event.saved_path).name, content)
        image_path = f"delivery/outputs/{Path(image_event.saved_path).name}"
        prompt_hash = sha256(image_call.prompt.encode("utf-8")).hexdigest()
        arguments_hash = image_arguments_hash(
            prompt_hash=prompt_hash,
            reference_hashes=reference_hashes,
            transparent_background=image_call.transparent_background,
            num_last_images_to_include=image_call.num_last_images_to_include,
        )
        image_facts = (CodexExecImageEvidence(
            attemptId=attempt.attempt_id,
            sessionId=stream.session_id,
            callId=image_call.call_id,
            callOrdinal=image_call.ordinal,
            eventId=image_event.event_id,
            eventType="image_gen.generation",
            eventStatus="completed",
            argumentsHash=arguments_hash,
            promptHash=prompt_hash,
            referenceHashes=reference_hashes,
            transparentBackground=image_call.transparent_background,
            numLastImagesToInclude=image_call.num_last_images_to_include,
            outputHash=image_hash,
            outputRelativePath=image_path,
        ),)
        outputs = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
        return _ImageAttemptCompletion(
            outputs=outputs,
            image_facts=image_facts,
            remote_state="completed",
            reference_views=reference_views,
            image_call=image_call,
            image_event=image_event,
            reference_hashes=reference_hashes,
        )

    @staticmethod
    def _match_image_references(job_root, package_request, reference_paths):
        references = package_request.get("references")
        if not isinstance(references, list):
            raise CodexExecSupervisorError("Codex Exec image request has no typed frozen reference inventory")
        expected_paths = []
        expected_hashes = []
        package = job_root / "package"
        for item in references:
            if not isinstance(item, dict) or set(item) != {"role", "filename", "sha256"}:
                raise CodexExecSupervisorError("Codex Exec image reference has an unsupported package shape")
            relative = PurePosixPath(item["filename"])
            if (
                relative.is_absolute() or relative.as_posix() != item["filename"]
                or len(relative.parts) < 2 or relative.parts[0] != "references"
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                raise CodexExecSupervisorError("Codex Exec image reference is outside its frozen package")
            path = (package / relative).resolve(strict=True)
            if not path.is_relative_to(package.resolve(strict=True)):
                raise CodexExecSupervisorError("Codex Exec image reference escapes its frozen package")
            expected_paths.append(str(path))
            expected_hashes.append(item["sha256"])
        if tuple(reference_paths) != tuple(expected_paths):
            raise CodexExecSupervisorError("ImageGen references differ from the exact frozen package bytes")
        if len(expected_hashes) != len(set(expected_hashes)):
            raise CodexExecSupervisorError("Codex Exec frozen image references must have distinct byte hashes")
        return tuple(expected_hashes)

    @staticmethod
    def _match_image_reference_views(job_root, package_request, reference_views, image_call):
        from plotloom.codex_exec_contracts import CodexExecReferenceViewEvidence

        references = package_request.get("references")
        if not isinstance(references, list):
            raise CodexExecSupervisorError("Codex Exec image request has no typed frozen reference inventory")
        if len(reference_views) != len(references):
            raise CodexExecSupervisorError("every frozen package reference must have one exact image view")
        package = job_root / "package"
        evidence = []
        for reference, view in zip(references, reference_views, strict=True):
            if not isinstance(reference, dict) or set(reference) != {"role", "filename", "sha256"}:
                raise CodexExecSupervisorError("Codex Exec image reference has an unsupported package shape")
            relative = PurePosixPath(reference["filename"])
            if (
                relative.is_absolute() or relative.as_posix() != reference["filename"]
                or len(relative.parts) < 2 or relative.parts[0] != "references"
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                raise CodexExecSupervisorError("Codex Exec image reference is outside its frozen package")
            absolute = (package / relative).resolve(strict=True)
            if not absolute.is_relative_to(package.resolve(strict=True)) or view.path != str(absolute):
                raise CodexExecSupervisorError("Codex Exec view path is not its exact frozen package reference")
            if view.output_ordinal >= image_call.ordinal:
                raise CodexExecSupervisorError("every frozen reference must be emitted before ImageGen")
            evidence.append(CodexExecReferenceViewEvidence(
                role=reference["role"],
                packageRelativePath=reference["filename"],
                referenceHash=reference["sha256"],
                contentSha256=view.content_sha256,
                contentSizeBytes=view.content_size_bytes,
                callId=view.call_id,
                eventId=view.event_id,
                callOrdinal=view.call_ordinal,
                eventOrdinal=view.event_ordinal,
                outputOrdinal=view.output_ordinal,
            ))
        return tuple(evidence)

    @staticmethod
    def _copy_image_to_delivery(job_root, filename, content):
        if PurePosixPath(filename).name != filename or not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raise CodexExecSupervisorError("ImageGen returned an unsupported output basename")
        delivery = job_root / "delivery"
        if delivery.is_symlink() or not delivery.is_dir():
            raise CodexExecSupervisorError("Codex Exec delivery directory is unsafe")
        if any(delivery.iterdir()):
            raise CodexExecSupervisorError("image delivery was modified before its trusted host copy")
        outputs = delivery / "outputs"
        outputs.mkdir(mode=0o700)
        output_fd = os.open(outputs, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=output_fd)
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            os.fsync(output_fd)
        finally:
            os.close(output_fd)
