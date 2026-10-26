"""Immutable image package projection and verification, separate from deliveries."""
from __future__ import annotations
from collections.abc import Iterable
from typing import Any, TYPE_CHECKING
from hashlib import sha256
import json
import os
from .image_exchange_files import _open_directory, _open_child_directory, _read_regular_at, _directory_names
from .image_job_contracts import ImageJobError, NativeTaskBinding, is_image_job_id
from .image_job_package import COMPLETION_TEMPLATE_FILENAME, project_image_package
from .image_job_package import canonical_json as _canonical_json
if TYPE_CHECKING:
    from .image_exchange_references import PackageReference


class ImagePackageCommands:
    def write_package(
        self,
        *,
        job_id: str,
        request: dict[str, Any],
        request_hash: str,
        references: Iterable[PackageReference],
        native_task_binding: NativeTaskBinding | dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Publish an immutable specialist-readable package once.

        A repeated Copy may observe the original package but can never replace a
        frozen request or a reference byte set.
        """

        root = self._root()
        if not is_image_job_id(job_id):
            raise ImageJobError("invalid_job_id", "image job identifier is invalid")
        job_root = root / "jobs" / job_id
        package = job_root / "package"
        reference_values = tuple(references)
        reference_entries: list[dict[str, str]] = []
        for reference in reference_values:
            if sha256(reference.content).hexdigest() != reference.content_hash:
                raise ImageJobError("reference_integrity", "frozen reference bytes do not match their declared hash")
            if "/" in reference.filename or "\\" in reference.filename or reference.filename.startswith("."):
                raise ImageJobError("reference_filename", "frozen reference filename is invalid")
            reference_entries.append({
                "role": reference.role,
                "filename": f"references/{reference.filename}",
                "sha256": reference.content_hash,
            })
        # The request hash covers the immutable request itself, not this mutable
        # transport projection. Verify it before writing or trusting a prior Copy.
        if sha256(_canonical_json(request)).hexdigest() != request_hash:
            raise ImageJobError("request_integrity", "frozen image request hash is invalid")
        package_request, instructions, template, _expected_entries = project_image_package(
            root=root,
            job_id=job_id,
            request=request,
            request_hash=request_hash,
            reference_entries=reference_entries,
            native_task_binding=native_task_binding,
        )
        files = {"request.json": _canonical_json(package_request), "COPY_ASSIGNMENT.txt": instructions}
        if template is not None:
            files[COMPLETION_TEMPLATE_FILENAME] = template
        files.update({f"references/{item.filename}": item.content for item in reference_values})
        from .image_package_publication import publish_image_package
        publish_image_package(root, job_id, request_hash, files)
        self.verify_package(job_id=job_id, request=request, request_hash=request_hash,
            references=[(item.role, item.filename, item.content_hash) for item in reference_values],
            native_task_binding=native_task_binding)
        return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}

    def verify_package(
        self,
        *,
        job_id: str,
        request: dict[str, Any],
        request_hash: str,
        references: Iterable[tuple[str, str, str]],
        native_task_binding: NativeTaskBinding | dict[str, Any] | None = None,
    ) -> None:
        """Recheck a copied package before accepting its untrusted delivery.

        Same-user same-host handoff cannot make a readable file permanently
        immutable with POSIX mode bits. Trusted Refresh therefore revalidates
        the complete transport projection against the database-frozen request.
        """

        root = self._root()
        if not is_image_job_id(job_id):
            raise ImageJobError("invalid_job_id", "image job identifier is invalid")
        reference_values = tuple(references)
        if sha256(_canonical_json(request)).hexdigest() != request_hash:
            raise ImageJobError("request_integrity", "frozen image request hash is invalid")
        reference_entries = [
            {"role": role, "filename": f"references/{filename}", "sha256": content_hash}
            for role, filename, content_hash in reference_values
        ]
        package_request, instructions, template, expected_entries = project_image_package(
            root=root,
            job_id=job_id,
            request=request,
            request_hash=request_hash,
            reference_entries=reference_entries,
            native_task_binding=native_task_binding,
        )
        package_fd = _open_directory(root, ("jobs", job_id, "package"), package=True)
        try:
            if _directory_names(package_fd, package=True) != expected_entries:
                raise ImageJobError("package_conflict", "existing package has unexpected entries")
            try:
                existing_request = json.loads(_read_regular_at(
                    package_fd, "request.json", max_bytes=1_000_000, package=True
                ))
            except json.JSONDecodeError as error:
                raise ImageJobError("package_conflict", "existing package request is malformed") from error
            if existing_request != package_request:
                raise ImageJobError("package_conflict", "existing package does not match the frozen image request")
            if _read_regular_at(package_fd, "COPY_ASSIGNMENT.txt", max_bytes=20_000, package=True) != instructions:
                raise ImageJobError("package_conflict", "existing package instructions do not match the frozen image request")
            if template is not None and _read_regular_at(
                package_fd, COMPLETION_TEMPLATE_FILENAME, max_bytes=20_000, package=True
            ) != template:
                raise ImageJobError("package_conflict", "existing package completion template does not match the frozen request")
            if reference_values:
                references_fd = _open_child_directory(package_fd, "references", package=True)
                try:
                    if _directory_names(references_fd, package=True) != {filename for _, filename, _ in reference_values}:
                        raise ImageJobError("package_conflict", "existing package reference set does not match the frozen request")
                    for _, filename, content_hash in reference_values:
                        content = _read_regular_at(
                            references_fd, filename, max_bytes=self.limits.max_import_bytes, package=True
                        )
                        if sha256(content).hexdigest() != content_hash:
                            raise ImageJobError("package_conflict", "existing package reference bytes do not match the frozen request")
                finally:
                    os.close(references_fd)
        finally:
            os.close(package_fd)
