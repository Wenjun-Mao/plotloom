"""Concrete same-host package and delivery exchange for P1 image jobs.

The canonical job is persisted before this module is called.  This adapter owns
only configured, confined filesystem exchange and never accepts a browser path.
"""
from __future__ import annotations

import errno
import json
import os
import stat
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from .image_job_contracts import ImageDeliveryManifest, ImageJobError, is_image_job_id
from .managed_media import ManagedMediaLimits, ObservedImage, inspect_import_image


PACKAGE_VERSION = 3
PINNED_PACKAGE_VERSION = 4
COMPLETION_FILENAME = "completion.json"
COMPLETION_TEMPLATE_FILENAME = "completion-manifest.example.json"
EXECUTOR_PIN_FILENAME = "executor-pin.json"


@dataclass(frozen=True)
class PackageReference:
    role: str
    filename: str
    content_hash: str
    content: bytes


@dataclass(frozen=True)
class ValidatedOutput:
    filename: str
    role: str
    observed: ObservedImage
    content: bytes


@dataclass(frozen=True)
class ValidatedDelivery:
    manifest: ImageDeliveryManifest
    manifest_hash: str
    outputs: tuple[ValidatedOutput, ...]


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class ImageJobExchange:
    """A one-root, per-job exchange with no path authority from callers."""

    def __init__(self, root: Path | None, *, limits: ManagedMediaLimits) -> None:
        self._configured_root = root
        self.limits = limits

    @property
    def configured(self) -> bool:
        return self._configured_root is not None

    def validate_configured(self) -> None:
        """Fail early before repository admission when no safe exchange exists."""

        self._root()

    def _root(self) -> Path:
        if self._configured_root is None:
            raise ImageJobError(
                "image_exchange_not_configured",
                "PLOTLOOM_IMAGE_EXCHANGE_ROOT must be configured for Codex image jobs",
            )
        root = self._configured_root.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ImageJobError("image_exchange_invalid", "configured image exchange root is not a directory")
        return root

    @staticmethod
    def _no_follow_flags(*, directory: bool = False) -> int:
        """Return an OS-enforced no-follow open mode for untrusted delivery paths."""

        no_follow = getattr(os, "O_NOFOLLOW", None)
        if no_follow is None:
            raise ImageJobError("image_exchange_invalid", "image exchange requires no-follow filesystem support")
        return os.O_RDONLY | no_follow | (getattr(os, "O_DIRECTORY", 0) if directory else 0)

    @staticmethod
    def _path_open_error(error: OSError, *, package: bool = False) -> ImageJobError:
        if error.errno == errno.ELOOP:
            return ImageJobError("delivery_symlink", "image-job paths must not traverse symlinks")
        if package:
            return ImageJobError("package_conflict", "existing package paths are not safe regular entries")
        if error.errno == errno.ENOENT:
            return ImageJobError("delivery_incomplete", "delivery file is not present")
        return ImageJobError("delivery_path_invalid", "delivery entries must be regular non-symlink files")

    @classmethod
    def _open_directory(
        cls, root: Path, parts: tuple[str, ...], *, create: bool = False, package: bool = False
    ) -> int:
        """Open a descendant directory one no-follow component at a time."""

        try:
            directory_fd = os.open(root, cls._no_follow_flags(directory=True))
        except OSError as error:
            raise cls._path_open_error(error, package=package) from error
        try:
            for part in parts:
                try:
                    child_fd = os.open(part, cls._no_follow_flags(directory=True), dir_fd=directory_fd)
                except FileNotFoundError:
                    if not create:
                        if package:
                            raise ImageJobError("package_conflict", "existing package directory is incomplete")
                        raise ImageJobError("delivery_incomplete", "delivery directory is not present")
                    try:
                        os.mkdir(part, dir_fd=directory_fd)
                        child_fd = os.open(part, cls._no_follow_flags(directory=True), dir_fd=directory_fd)
                    except OSError as error:
                        raise cls._path_open_error(error, package=package) from error
                except OSError as error:
                    raise cls._path_open_error(error, package=package) from error
                os.close(directory_fd)
                directory_fd = child_fd
            return directory_fd
        except BaseException:
            os.close(directory_fd)
            raise

    @classmethod
    def _open_child_directory(
        cls, parent_fd: int, name: str, *, create: bool = False, package: bool = False
    ) -> int:
        """Open one child from an already pinned parent descriptor."""

        try:
            return os.open(name, cls._no_follow_flags(directory=True), dir_fd=parent_fd)
        except FileNotFoundError:
            if not create:
                if package:
                    raise ImageJobError("package_conflict", "existing package directory is incomplete")
                raise ImageJobError("delivery_incomplete", "delivery directory is not present")
            try:
                os.mkdir(name, dir_fd=parent_fd)
                return os.open(name, cls._no_follow_flags(directory=True), dir_fd=parent_fd)
            except OSError as error:
                raise cls._path_open_error(error, package=package) from error
        except OSError as error:
            raise cls._path_open_error(error, package=package) from error

    @classmethod
    def _read_regular_at(
        cls, directory_fd: int, filename: str, *, max_bytes: int, package: bool = False
    ) -> bytes:
        try:
            file_fd = os.open(filename, cls._no_follow_flags(), dir_fd=directory_fd)
        except OSError as error:
            raise cls._path_open_error(error, package=package) from error
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                code = "package_conflict" if package else "delivery_path_invalid"
                raise ImageJobError(code, "image-job entries must be regular files")
            chunks: list[bytes] = []
            remaining = max_bytes + 1
            while remaining:
                chunk = os.read(file_fd, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            if len(content) > max_bytes:
                code = "package_conflict" if package else "delivery_file_too_large"
                raise ImageJobError(code, "delivery file exceeds the configured size limit")
            return content
        finally:
            os.close(file_fd)

    @classmethod
    def _directory_names(cls, directory_fd: int, *, package: bool = False) -> set[str]:
        try:
            names = set(os.listdir(directory_fd))
            for name in names:
                mode = os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    raise ImageJobError("delivery_symlink", "image-job paths must not traverse symlinks")
        except ImageJobError:
            raise
        except OSError as error:
            raise cls._path_open_error(error, package=package) from error
        return names

    @staticmethod
    def _atomic_write_at(directory_fd: int, filename: str, content: bytes) -> None:
        # Copy may be retried concurrently. A per-write nonce avoids colliding
        # temporary entries while the final replace remains atomic.
        temporary = f".{filename}.{os.getpid()}.{os.urandom(8).hex()}.partial"
        file_fd: int | None = None
        try:
            file_fd = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=directory_fd,
            )
            view = memoryview(content)
            while view:
                written = os.write(file_fd, view)
                view = view[written:]
            os.fsync(file_fd)
            os.close(file_fd)
            file_fd = None
            os.replace(temporary, filename, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            os.fsync(directory_fd)
        finally:
            if file_fd is not None:
                os.close(file_fd)
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass

    @staticmethod
    def _package_version(request: dict[str, Any]) -> int:
        """Keep copied v1 packages readable while making v2 self-contained."""

        schema_version = request.get("schemaVersion")
        if schema_version == 1:
            return 1
        if schema_version == 2:
            return 2
        if schema_version == 3:
            return PINNED_PACKAGE_VERSION if request.get("specialistPreflight", {}).get("version") == "p1.5-pin.v1" else PACKAGE_VERSION
        raise ImageJobError("request_integrity", "frozen image request schema is unsupported")

    @classmethod
    def _package_projection(
        cls,
        *,
        root: Path,
        job_id: str,
        request: dict[str, Any],
        request_hash: str,
        reference_entries: list[dict[str, str]],
    ) -> tuple[dict[str, Any], bytes, bytes | None, set[str]]:
        """Derive the complete, recheckable package from frozen database data."""

        package_version = cls._package_version(request)
        job_root = root / "jobs" / job_id
        package = job_root / "package"
        if package_version == 1:
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
            ).encode("utf-8")
            template: bytes | None = None
        elif package_version == 2:
            delivery_instruction = (
                "Read completion-manifest.example.json before preparing delivery. Write complete JPEG or PNG files to "
                "delivery/outputs, then use that exact field shape to publish delivery/completion.json once. Do not write "
                "SQLite, modify this package, or include sensitive values."
            )
            instructions = (
                f"Plotloom image job {job_id}\n"
                f"Read: {package / 'request.json'}\n"
                f"Read completion template: {package / COMPLETION_TEMPLATE_FILENAME}\n"
                f"Deliver only under: {job_root / 'delivery'}\n"
                "Use Codex built-in image generation. The request contains the frozen creator direction, selected reviewed "
                "VisualIntent when this is a refinement, and the resolved authored shot context. Preserve those facts, disclose "
                "the exact actual prompt, and publish completion.json only after every declared output is complete.\n"
            ).encode("utf-8")
            template = _canonical_json({
                "schemaVersion": 1,
                "jobId": job_id,
                "requestHash": request_hash,
                "deliveryId": "replace-with-specialist-delivery-id",
                "actualPrompt": "replace-with-the-exact-prompt-submitted-to-Codex-imagegen",
                "outputs": [{
                    "filename": "candidate.png",
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
            proposal = request.get("target") == "character_reference_proposal"
            delivery_instruction = (
                "Read completion-manifest.example.json before preparing delivery. "
                + (
                    "View every role-mapped character_identity reference before generation and report its hashes in referenceUse. "
                    if not proposal else
                    "This is an exploratory character-reference proposal; it cannot approve or select a reference. "
                )
                + "Write complete JPEG or PNG files to delivery/outputs, then publish delivery/completion.json once. Do not write "
                "SQLite, modify this package, or include sensitive values."
            )
            instructions = (
                f"Plotloom {'character-reference proposal' if proposal else 'identity-aware image job'} {job_id}\n"
                f"Read: {package / 'request.json'}\n"
                f"Read completion template: {package / COMPLETION_TEMPLATE_FILENAME}\n"
                + (f"Before ImageGen, run: uv run python scripts/pin_image_specialist.py --package {package}\n" if package_version == PINNED_PACKAGE_VERSION else "")
                + f"Deliver only under: {job_root / 'delivery'}\n"
                + (
                    "Use Codex built-in image generation. View every supplied character_identity reference and preserve "
                    "that person while the frozen canonical shot state controls costume, pose, expression, lighting, and "
                    "camera. parent_output is a separate edit guide and never replaces character identity. "
                    if not proposal else
                    "Use Codex built-in image generation for the frozen Story Bible character context. This result is an "
                    "exploratory candidate only: do not claim an approved Shot, storyboard Approval, or selected reference. "
                )
                + "Disclose the "
                "exact actual prompt and publish completion.json only after every declared output is complete.\n"
            ).encode("utf-8")
            template_payload: dict[str, Any] = {
                "schemaVersion": 2,
                "jobId": job_id,
                "requestHash": request_hash,
                "deliveryId": "replace-with-specialist-delivery-id",
                "actualPrompt": "replace-with-the-exact-prompt-submitted-to-Codex-imagegen",
                "outputs": [{
                    "filename": "candidate.png",
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
            if not proposal:
                template_payload["referenceUse"] = {
                    "viewedReferenceHashes": ["replace-with-every-character-identity-hash"],
                    "identityNotes": "describe how identity was preserved; this attestation is not creator approval",
                }
            template = _canonical_json(template_payload)
        package_request = dict(request)
        package_request.update({
            "packageVersion": package_version,
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

    def write_package(
        self,
        *,
        job_id: str,
        request: dict[str, Any],
        request_hash: str,
        references: Iterable[PackageReference],
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
        package_request, instructions, template, expected_entries = self._package_projection(
            root=root,
            job_id=job_id,
            request=request,
            request_hash=request_hash,
            reference_entries=reference_entries,
        )
        package_fd = self._open_directory(root, ("jobs", job_id, "package"), create=True, package=True)
        try:
            names = self._directory_names(package_fd, package=True)
            if "request.json" in names:
                if names != expected_entries:
                    raise ImageJobError("package_conflict", "existing package has unexpected entries")
                try:
                    existing_request = json.loads(self._read_regular_at(
                        package_fd, "request.json", max_bytes=1_000_000, package=True
                    ))
                except json.JSONDecodeError as error:
                    raise ImageJobError("package_conflict", "existing package request is malformed") from error
                if existing_request != package_request:
                    raise ImageJobError("package_conflict", "existing package does not match the frozen image request")
                if self._read_regular_at(package_fd, "COPY_ASSIGNMENT.txt", max_bytes=20_000, package=True) != instructions:
                    raise ImageJobError("package_conflict", "existing package instructions do not match the frozen image request")
                if template is not None and self._read_regular_at(
                    package_fd, COMPLETION_TEMPLATE_FILENAME, max_bytes=20_000, package=True
                ) != template:
                    raise ImageJobError("package_conflict", "existing package completion template does not match the frozen request")
                if reference_values:
                    references_fd = self._open_child_directory(package_fd, "references", package=True)
                    try:
                        if self._directory_names(references_fd, package=True) != {item.filename for item in reference_values}:
                            raise ImageJobError("package_conflict", "existing package reference set does not match the frozen request")
                        for reference in reference_values:
                            content = self._read_regular_at(references_fd, reference.filename, max_bytes=self.limits.max_import_bytes, package=True)
                            if sha256(content).hexdigest() != reference.content_hash:
                                raise ImageJobError("package_conflict", "existing package reference bytes do not match the frozen request")
                    finally:
                        os.close(references_fd)
                return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}
            if names:
                raise ImageJobError("package_conflict", "incomplete package cannot be safely resumed")
            if reference_values:
                references_fd = self._open_child_directory(package_fd, "references", create=True, package=True)
                try:
                    for reference in reference_values:
                        self._atomic_write_at(references_fd, reference.filename, reference.content)
                finally:
                    os.close(references_fd)
            if template is not None:
                self._atomic_write_at(package_fd, COMPLETION_TEMPLATE_FILENAME, template)
            self._atomic_write_at(package_fd, "COPY_ASSIGNMENT.txt", instructions)
            self._atomic_write_at(package_fd, "request.json", _canonical_json(package_request))
        finally:
            os.close(package_fd)
        return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}

    def verify_package(
        self,
        *,
        job_id: str,
        request: dict[str, Any],
        request_hash: str,
        references: Iterable[tuple[str, str, str]],
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
        package_request, instructions, template, expected_entries = self._package_projection(
            root=root,
            job_id=job_id,
            request=request,
            request_hash=request_hash,
            reference_entries=reference_entries,
        )
        package_fd = self._open_directory(root, ("jobs", job_id, "package"), package=True)
        try:
            if self._directory_names(package_fd, package=True) != expected_entries:
                raise ImageJobError("package_conflict", "existing package has unexpected entries")
            try:
                existing_request = json.loads(self._read_regular_at(
                    package_fd, "request.json", max_bytes=1_000_000, package=True
                ))
            except json.JSONDecodeError as error:
                raise ImageJobError("package_conflict", "existing package request is malformed") from error
            if existing_request != package_request:
                raise ImageJobError("package_conflict", "existing package does not match the frozen image request")
            if self._read_regular_at(package_fd, "COPY_ASSIGNMENT.txt", max_bytes=20_000, package=True) != instructions:
                raise ImageJobError("package_conflict", "existing package instructions do not match the frozen image request")
            if template is not None and self._read_regular_at(
                package_fd, COMPLETION_TEMPLATE_FILENAME, max_bytes=20_000, package=True
            ) != template:
                raise ImageJobError("package_conflict", "existing package completion template does not match the frozen request")
            if reference_values:
                references_fd = self._open_child_directory(package_fd, "references", package=True)
                try:
                    if self._directory_names(references_fd, package=True) != {filename for _, filename, _ in reference_values}:
                        raise ImageJobError("package_conflict", "existing package reference set does not match the frozen request")
                    for _, filename, content_hash in reference_values:
                        content = self._read_regular_at(
                            references_fd, filename, max_bytes=self.limits.max_import_bytes, package=True
                        )
                        if sha256(content).hexdigest() != content_hash:
                            raise ImageJobError("package_conflict", "existing package reference bytes do not match the frozen request")
                finally:
                    os.close(references_fd)
        finally:
            os.close(package_fd)

    def read_delivery(
        self,
        *,
        job_id: str,
        request_hash: str,
        required_reference_hashes: Iterable[str] = (),
        require_executor_provenance: bool = False,
        require_executor_pin: bool = False,
    ) -> ValidatedDelivery | None:
        """Read a completed untrusted package, or report that no delivery exists yet.

        An absent delivery directory (or an empty inbox) is the normal state
        after Copy.  It is deliberately distinct from an incomplete package:
        once a writer has placed any entry in the inbox, Refresh continues to
        fail closed instead of treating a partial handoff as harmless waiting.
        """

        root = self._root()
        if not is_image_job_id(job_id):
            raise ImageJobError("invalid_job_id", "image job identifier is invalid")
        # Descriptor-relative, no-follow reads bind every ancestor and the
        # final file before inspecting it. A delivery writer can change files
        # while preparing, but cannot swap this read outside the exchange root.
        try:
            delivery_fd = self._open_directory(root, ("jobs", job_id, "delivery"))
        except ImageJobError as error:
            if error.code == "delivery_incomplete":
                return None
            raise
        try:
            names = self._directory_names(delivery_fd)
            if not names:
                return None
            if COMPLETION_FILENAME not in names:
                raise ImageJobError(
                    "delivery_partial",
                    "delivery has files but no completion manifest",
                )
            raw = self._read_regular_at(delivery_fd, COMPLETION_FILENAME, max_bytes=1_000_000)
            try:
                payload = json.loads(raw)
                manifest = ImageDeliveryManifest.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as error:
                raise ImageJobError("delivery_manifest_invalid", "completion manifest does not match the image-job contract") from error
            if manifest.job_id != job_id or manifest.request_hash != request_hash:
                raise ImageJobError("delivery_identity_mismatch", "completion manifest does not belong to this frozen image job")
            required_hashes = tuple(required_reference_hashes)
            if required_hashes:
                if manifest.schema_version != 2 or manifest.reference_use is None:
                    raise ImageJobError(
                        "delivery_reference_use_missing",
                        "identity-aware delivery must attest to every viewed character reference",
                    )
                if set(manifest.reference_use.viewed_reference_hashes) != set(required_hashes):
                    raise ImageJobError(
                        "delivery_reference_use_mismatch",
                        "identity-aware delivery reference attestation does not match the frozen identity set",
                    )
            if require_executor_provenance and manifest.executor_provenance is None:
                raise ImageJobError(
                    "delivery_executor_provenance_missing",
                    "identity-aware delivery must record the observed code and specialist skill provenance",
                )
            if require_executor_pin:
                if not require_executor_provenance:
                    raise ImageJobError("delivery_executor_pin_invalid", "executor pin requires executor provenance")
                if EXECUTOR_PIN_FILENAME not in names:
                    raise ImageJobError(
                        "delivery_executor_pin_missing",
                        "identity-aware delivery must include the pre-generation executor pin",
                    )
                try:
                    pin = json.loads(self._read_regular_at(
                        delivery_fd, EXECUTOR_PIN_FILENAME, max_bytes=20_000
                    ))
                except (json.JSONDecodeError, TypeError) as error:
                    raise ImageJobError("delivery_executor_pin_invalid", "executor pin is not valid JSON") from error
                provenance = manifest.executor_provenance
                expected_pin = {
                    "jobId": job_id,
                    "requestHash": request_hash,
                    "executionContract": "codex_specialist.v2",
                    "skillVersion": provenance.skill_version,
                    "codeRevision": provenance.code_revision,
                    "skillHash": provenance.skill_hash,
                }
                if pin != expected_pin:
                    raise ImageJobError(
                        "delivery_executor_pin_mismatch",
                        "completion provenance must match the pre-generation executor pin",
                    )
            expected_delivery_names = {COMPLETION_FILENAME, "outputs"}
            if require_executor_pin:
                expected_delivery_names.add(EXECUTOR_PIN_FILENAME)
            if names != expected_delivery_names:
                raise ImageJobError("delivery_partial", "delivery contains undeclared files")

            outputs_fd = self._open_directory(root, ("jobs", job_id, "delivery", "outputs"))
            try:
                declared = {item.filename for item in manifest.outputs}
                actual = self._directory_names(outputs_fd)
                if actual != declared:
                    raise ImageJobError("delivery_partial", "delivery output set does not exactly match the completion manifest")
                outputs: list[ValidatedOutput] = []
                for declaration in manifest.outputs:
                    content = self._read_regular_at(outputs_fd, declaration.filename, max_bytes=self.limits.max_import_bytes)
                    if sha256(content).hexdigest() != declaration.sha256:
                        raise ImageJobError("delivery_hash_mismatch", "delivery bytes do not match their declared hash")
                    try:
                        observed = inspect_import_image(content, self.limits)
                    except Exception as error:  # ManagedMediaError is intentionally normalized for this boundary.
                        code = getattr(error, "code", "delivery_image_invalid")
                        raise ImageJobError(code, "delivery output is not a bounded supported raster") from error
                    outputs.append(ValidatedOutput(
                        filename=declaration.filename,
                        role=declaration.role,
                        observed=observed,
                        content=content,
                    ))
            finally:
                os.close(outputs_fd)
        finally:
            os.close(delivery_fd)
        return ValidatedDelivery(
            manifest=manifest,
            manifest_hash=sha256(_canonical_json(manifest.model_dump(mode="json", by_alias=True))).hexdigest(),
            outputs=tuple(outputs),
        )
