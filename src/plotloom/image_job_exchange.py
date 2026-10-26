"""Configured composition of image package and delivery owners."""
from __future__ import annotations
from collections.abc import Iterable
from pathlib import Path
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecReceipt
from .image_job_contracts import ImageJobError, NativeTaskBinding
from .managed_media import ManagedMediaLimits
from .image_exchange_packages import ImagePackageCommands
from .image_delivery_reader import ValidatedDelivery, read_delivery


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
        return read_delivery(self._root(), self.limits,
            job_id=job_id,
            request_hash=request_hash,
            required_reference_hashes=required_reference_hashes,
            require_executor_provenance=require_executor_provenance,
            require_executor_pin=require_executor_pin,
            expected_executor_skill_version=expected_executor_skill_version,
            expected_executor_contract=expected_executor_contract,
            expected_native_task_binding=expected_native_task_binding,
            expected_codex_attempt=expected_codex_attempt,
            expected_codex_profile=expected_codex_profile,
            expected_codex_receipt=expected_codex_receipt,
            expected_codex_references=expected_codex_references,
            expected_codex_execution_pin=expected_codex_execution_pin,
            expected_codex_output_role=expected_codex_output_role,
        )
