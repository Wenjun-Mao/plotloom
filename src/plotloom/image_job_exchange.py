"""Concrete same-host package and delivery exchange for P1 image jobs.

The canonical job is persisted before this module is called.  This adapter owns
only configured, confined filesystem exchange and never accepts a browser path.
"""
from __future__ import annotations

import errno
import json
import os
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from .image_exchange_packages import ImagePackageCommands
from .image_job_contracts import (
    ImageDeliveryManifest,
    ImageExecutorProvenance,
    ImageJobError,
    NativeTaskBinding,
    is_image_job_id,
)
from .image_job_package import canonical_json as _canonical_json
from .managed_media import ManagedMediaLimits, ObservedImage, inspect_import_image

COMPLETION_FILENAME = "completion.json"
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


class ImageJobExchange(ImagePackageCommands):
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
                        try:
                            os.mkdir(part, dir_fd=directory_fd)
                        except FileExistsError:
                            # A cooperating publisher may create this ancestor
                            # before our per-job lock. Reopen with no-follow.
                            pass
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
                try:
                    os.mkdir(name, dir_fd=parent_fd)
                except FileExistsError:
                    pass
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
    def _directory_names(
        cls,
        directory_fd: int,
        *,
        package: bool = False,
        allow_disappearing: frozenset[str] = frozenset(),
    ) -> set[str]:
        try:
            names = set(os.listdir(directory_fd))
            for name in tuple(names):
                try:
                    mode = os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode
                except FileNotFoundError:
                    # Directory listings are not snapshots. The publisher
                    # unlinks this known staging file after linking the final
                    # completion marker, so omit it if it vanishes mid-scan.
                    if name not in allow_disappearing:
                        raise
                    names.discard(name)
                    continue
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

    def read_delivery(
        self,
        *,
        job_id: str,
        request_hash: str,
        required_reference_hashes: Iterable[str] = (),
        require_executor_provenance: bool = False,
        require_executor_pin: bool = False,
        expected_executor_skill_version: str | None = None,
        expected_executor_contract: str = "codex_specialist.v2",
        expected_native_task_binding: NativeTaskBinding | dict | None = None,
        expected_codex_attempt: CodexExecAttempt | None = None,
        expected_codex_profile: CodexExecProfile | None = None,
        expected_codex_receipt: CodexExecReceipt | None = None,
        expected_codex_references: Iterable[tuple[str, str, str]] = (),
        expected_codex_execution_pin: dict[str, str] | None = None,
        expected_codex_output_role: str | None = None,
    ) -> ValidatedDelivery | None:
        """Read a completed untrusted package, or report that no delivery exists yet.

        An absent delivery directory, an empty inbox, and staged output before
        ``completion.json`` are all normal pending states after Copy. The
        completion manifest is the specialist's final publication marker: only
        once it exists can an observer classify malformed bytes as a durable
        rejected delivery. This keeps repeated polling from manufacturing
        rejection history while an otherwise valid specialist is still writing.
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
        completion_marker_observed = False
        try:
            names = self._directory_names(
                delivery_fd, allow_disappearing=frozenset({"completion-draft.json"})
            )
            if not names:
                return None
            if COMPLETION_FILENAME not in names:
                # The delivery protocol requires the specialist to publish the
                # manifest last. Outputs, the v4 executor pin, and even a
                # partially written staging set therefore carry no terminal
                # meaning before that marker exists. They remain confined and
                # non-publishing until the next observation sees completion.
                return None
            completion_marker_observed = True
            raw = self._read_regular_at(delivery_fd, COMPLETION_FILENAME, max_bytes=1_000_000)
            try:
                payload = json.loads(raw)
                manifest = ImageDeliveryManifest.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as error:
                raise ImageJobError("delivery_manifest_invalid", "completion manifest does not match the image-job contract") from error
            manifest.assert_secret_free()
            if manifest.job_id != job_id or manifest.request_hash != request_hash:
                raise ImageJobError("delivery_identity_mismatch", "completion manifest does not belong to this frozen image job")
            if manifest.schema_version == 3 and not require_executor_pin:
                raise ImageJobError("delivery_executor_pin_missing", "schema-v3 delivery requires its pre-generation executor pin")
            if manifest.schema_version == 5 and expected_executor_contract != "codex_exec.v1":
                raise ImageJobError("delivery_execution_mismatch", "schema-v5 delivery requires its exact Codex Exec attempt receipt")
            if expected_executor_contract == "codex_exec.v1":
                self._validate_codex_exec_delivery(
                    manifest,
                    job_id=job_id,
                    request_hash=request_hash,
                    expected_references=tuple(expected_codex_references),
                    required_identity_hashes=tuple(required_reference_hashes),
                    execution_pin=expected_codex_execution_pin,
                    expected_output_role=expected_codex_output_role,
                    attempt=expected_codex_attempt,
                    profile=expected_codex_profile,
                    receipt=expected_codex_receipt,
                )
            elif manifest.schema_version in {4, 5}:
                raise ImageJobError("delivery_execution_mismatch", "Codex Exec delivery requires its exact attempt receipt")
            required_hashes = tuple(required_reference_hashes)
            if required_hashes:
                if manifest.schema_version not in {2, 3, 4, 5} or manifest.reference_use is None:
                    raise ImageJobError(
                        "delivery_reference_use_missing",
                        "identity-aware delivery must attest to every viewed character reference",
                    )
                viewed_hashes = set(manifest.reference_use.viewed_reference_hashes)
                required_match = set(required_hashes) <= viewed_hashes if manifest.schema_version == 5 else viewed_hashes == set(required_hashes)
                if not required_match:
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
                pin = self._validated_executor_pin(
                    delivery_fd, job_id=job_id, request_hash=request_hash,
                    expected_skill_version=expected_executor_skill_version,
                    expected_execution_contract=expected_executor_contract,
                )
                provenance = manifest.executor_provenance
                expected_pin = {
                    "jobId": job_id,
                    "requestHash": request_hash,
                    "executionContract": expected_executor_contract,
                    "skillVersion": provenance.skill_version,
                    "codeRevision": provenance.code_revision,
                    "skillHash": provenance.skill_hash,
                }
                if expected_executor_contract == "codex_specialist.v3":
                    try:
                        binding = NativeTaskBinding.model_validate(expected_native_task_binding)
                    except (TypeError, ValueError) as error:
                        raise ImageJobError(
                            "delivery_native_task_binding_missing",
                            "schema-v3 delivery requires the package's expected native task binding",
                        ) from error
                    if manifest.schema_version != 3 or manifest.tool_evidence.native_task_id is None:
                        raise ImageJobError("delivery_native_task_identity_missing", "schema-v3 delivery must name its native task UUID")
                    if pin["nativeTaskId"] != str(manifest.tool_evidence.native_task_id):
                        raise ImageJobError("delivery_native_task_identity_mismatch", "completion native task UUID differs from the pre-generation pin")
                    if binding.mode == "configured_task" and pin["nativeTaskId"] != str(binding.task_id):
                        raise ImageJobError("delivery_native_task_identity_mismatch", "completion native task UUID differs from the configured specialist binding")
                    expected_pin["nativeTaskId"] = pin["nativeTaskId"]
                elif manifest.schema_version == 3:
                    raise ImageJobError("delivery_executor_pin_invalid", "schema-v3 delivery requires codex_specialist.v3")
                if pin != expected_pin:
                    raise ImageJobError(
                        "delivery_executor_pin_mismatch",
                        "completion provenance must match the pre-generation executor pin",
                    )
            expected_delivery_names = {COMPLETION_FILENAME, "outputs"}
            if require_executor_pin:
                expected_delivery_names.add(EXECUTOR_PIN_FILENAME)
            if manifest.schema_version == 3 and "completion-draft.json" in names:
                try:
                    draft_payload = json.loads(self._read_regular_at(
                        delivery_fd, "completion-draft.json", max_bytes=1_000_000
                    ))
                    draft = ImageDeliveryManifest.model_validate(draft_payload)
                except ImageJobError:
                    # The publisher removes this known staging file after the
                    # atomic marker link. Recheck the directory to distinguish
                    # that cleanup race from a still-present invalid entry.
                    current_names = self._directory_names(
                        delivery_fd, allow_disappearing=frozenset({"completion-draft.json"})
                    )
                    if "completion-draft.json" in current_names:
                        raise
                    names = current_names
                except (json.JSONDecodeError, ValidationError) as error:
                    raise ImageJobError(
                        "delivery_partial", "staged completion draft is invalid", publication_phase="final"
                    ) from error
                else:
                    if draft.canonical_payload() != manifest.canonical_payload():
                        raise ImageJobError(
                            "delivery_partial", "staged completion draft differs from the published manifest",
                            publication_phase="final",
                        )
                    expected_delivery_names.add("completion-draft.json")
            if names != expected_delivery_names:
                raise ImageJobError(
                    "delivery_partial", "delivery contains undeclared files", publication_phase="final"
                )

            outputs_fd = self._open_directory(root, ("jobs", job_id, "delivery", "outputs"))
            try:
                declared = {item.filename for item in manifest.outputs}
                actual = self._directory_names(outputs_fd)
                if actual != declared:
                    raise ImageJobError(
                        "delivery_partial", "delivery output set does not exactly match the completion manifest",
                        publication_phase="final",
                    )
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
        except ImageJobError as error:
            # Once the completion marker has been observed, every normalized
            # delivery error is final-publication evidence. The marker is set
            # before parsing because malformed completion bytes are final too.
            if completion_marker_observed and error.publication_phase is None:
                error.publication_phase = "final"
            raise
        finally:
            os.close(delivery_fd)
        return ValidatedDelivery(
            manifest=manifest,
            manifest_hash=sha256(_canonical_json(manifest.canonical_payload())).hexdigest(),
            outputs=tuple(outputs),
        )

    @staticmethod
    def _validate_codex_exec_delivery(
        manifest: ImageDeliveryManifest,
        *,
        job_id: str,
        request_hash: str,
        expected_references: tuple[tuple[str, str, str], ...],
        required_identity_hashes: tuple[str, ...],
        execution_pin: dict[str, str] | None,
        expected_output_role: str | None,
        attempt: CodexExecAttempt | None,
        profile: CodexExecProfile | None,
        receipt: CodexExecReceipt | None,
    ) -> None:
        expected_package_views = tuple(
            (role, f"references/{filename}", reference_hash)
            for role, filename, reference_hash in expected_references
        )
        if attempt is None or profile is None or receipt is None:
            raise ImageJobError("delivery_executor_evidence_missing", "Codex Exec image delivery requires its exact project attempt and host receipt")
        try:
            assert_receipt_matches_attempt(attempt, receipt)
        except (TypeError, ValueError) as error:
            raise ImageJobError("delivery_executor_evidence_invalid", "Codex Exec image receipt is invalid") from error
        tool = manifest.tool_evidence
        if (
            manifest.schema_version != 5
            or attempt.domain != "image"
            or attempt.job_id != job_id
            or attempt.request_hash != request_hash
            or attempt.profile_hash != profile.profile_hash
            or attempt.plotloom_code_revision != (execution_pin or {}).get("codeRevision")
            or manifest.executor_profile_hash != profile.profile_hash
            or tool.executor_attempt_id != attempt.attempt_id
            or tool.codex_session_id != receipt.session_id
            or receipt.expected_image_outputs != 1
            or len(receipt.image_evidence) != 1
            or tool.image_gen_call_id != receipt.image_evidence[0].call_id
            or tool.image_gen_event_id != receipt.image_evidence[0].event_id
            or manifest.actual_prompt == ""
            or sha256(manifest.actual_prompt.encode("utf-8")).hexdigest()
                != receipt.image_evidence[0].prompt_hash
            or receipt.image_evidence[0].reference_hashes != tuple(item[2] for item in expected_references)
            or tuple((item.role, item.package_relative_path, item.reference_hash) for item in receipt.reference_views)
                != expected_package_views
            or ((manifest.reference_use is not None) != bool(expected_references))
            or (manifest.reference_use is not None and
                manifest.reference_use.viewed_reference_hashes != list(dict.fromkeys(item[2] for item in expected_references)))
            or manifest.executor_provenance is None
            or manifest.executor_provenance.model != profile.model
            or manifest.executor_provenance.reasoning_effort != profile.reasoning_effort
            or execution_pin is None
            or manifest.executor_provenance.code_revision != execution_pin.get("codeRevision")
            or manifest.executor_provenance.skill_version != execution_pin.get("skillVersion")
            or manifest.executor_provenance.skill_hash != execution_pin.get("skillHash")
            or not set(required_identity_hashes) <= {item[2] for item in expected_references}
        ):
            raise ImageJobError("delivery_execution_mismatch", "image delivery differs from its exact Codex Exec attempt, profile or host receipt")
        event = receipt.image_evidence[0]
        if len(manifest.outputs) != 1 or (
            manifest.outputs[0].filename != event.output_relative_path.rsplit("/", 1)[-1]
            or manifest.outputs[0].sha256 != event.output_hash
            or manifest.outputs[0].role != expected_output_role
        ):
            raise ImageJobError("delivery_executor_evidence_invalid", "image output differs from the exact Codex Exec event bytes")

    def _validated_executor_pin(
        self, delivery_fd: int, *, job_id: str, request_hash: str,
        expected_skill_version: str | None,
        expected_execution_contract: str = "codex_specialist.v2",
    ) -> dict[str, str]:
        """Validate the narrow v4 pre-generation marker before accepting waiting."""

        try:
            pin = json.loads(self._read_regular_at(
                delivery_fd, EXECUTOR_PIN_FILENAME, max_bytes=20_000
            ))
        except (json.JSONDecodeError, TypeError) as error:
            raise ImageJobError("delivery_executor_pin_invalid", "executor pin is not valid JSON") from error
        expected_keys = {
            "jobId", "requestHash", "executionContract", "skillVersion",
            "codeRevision", "skillHash",
        }
        if expected_execution_contract == "codex_specialist.v3":
            expected_keys.add("nativeTaskId")
        if not isinstance(pin, dict) or set(pin) != expected_keys:
            raise ImageJobError("delivery_executor_pin_invalid", "executor pin has an unsupported shape")
        if pin.get("jobId") != job_id or pin.get("requestHash") != request_hash:
            raise ImageJobError("delivery_executor_pin_mismatch", "executor pin does not belong to this frozen image job")
        if pin.get("executionContract") != expected_execution_contract:
            raise ImageJobError("delivery_executor_pin_invalid", "executor pin has an unsupported execution contract")
        if expected_skill_version is not None and pin.get("skillVersion") != expected_skill_version:
            raise ImageJobError("delivery_executor_pin_invalid", "executor pin has an unsupported specialist skill version")
        try:
            ImageExecutorProvenance.model_validate({
                "codeRevision": pin["codeRevision"], "skillVersion": pin["skillVersion"],
                "skillHash": pin["skillHash"],
            })
        except (KeyError, ValidationError) as error:
            raise ImageJobError("delivery_executor_pin_invalid", "executor pin provenance is invalid") from error
        if expected_execution_contract == "codex_specialist.v3":
            try:
                pin["nativeTaskId"] = str(UUID(pin["nativeTaskId"]))
            except (KeyError, TypeError, ValueError) as error:
                raise ImageJobError("delivery_executor_pin_invalid", "executor pin native task UUID is invalid") from error
        return pin
