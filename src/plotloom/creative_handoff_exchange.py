"""Filesystem exchange for a one-stage, candidate-only creative handoff."""
from __future__ import annotations
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from pydantic import ValidationError
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecReceipt, assert_receipt_matches_attempt
from .creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES, CreativeDeliveryManifest, CreativeHandoffError, CreativeHandoffRequest, is_creative_job_id
from .creative_handoff_package_exchange import CreativeHandoffPackageExchangeMixin
from .creative_handoff_identity import COMPLETION_FILENAME, canonical_json, request_hash
from .creative_exchange_files import _read_regular
from .creative_execution_pin import current_execution_pin
from .creative_package_projection import project_creative_package


@dataclass(frozen=True)
class ValidatedCreativeDelivery:
    request: CreativeHandoffRequest
    manifest: CreativeDeliveryManifest
    manifest_hash: str
    candidate: dict[str, Any]
    report: bytes


class CreativeHandoffExchange(CreativeHandoffPackageExchangeMixin):
    """Packages immutable requests and reads untrusted specialist candidates."""

    def __init__(self, root: Path) -> None:
        configured = root.expanduser()
        if configured.is_symlink():
            raise CreativeHandoffError("package_conflict", "creative exchange root must not be a symlink")
        self.root = configured.resolve()

    def _job_root(self, job_id: str) -> Path:
        if not is_creative_job_id(job_id):
            raise CreativeHandoffError("invalid_job_id", "creative handoff job identifier is invalid")
        job_root = self.root / "jobs" / job_id
        if (self.root / "jobs").is_symlink() or job_root.is_symlink():
            raise CreativeHandoffError("package_conflict", "creative job paths must not traverse symlinks")
        return job_root

    @staticmethod
    def _names(directory: Path, *, package: bool = False) -> set[str]:
        if not directory.exists():
            return set()
        if directory.is_symlink() or not directory.is_dir():
            raise CreativeHandoffError("package_conflict" if package else "delivery_path_invalid", "handoff directory is unsafe")
        names = {entry.name for entry in directory.iterdir()}
        if any((directory / name).is_symlink() for name in names):
            raise CreativeHandoffError("delivery_symlink", "handoff paths must not traverse symlinks")
        return names

    @staticmethod
    def _candidate_filename(stage: str) -> str:
        return CREATIVE_CANDIDATE_FILENAMES[stage]

    def current_execution_pin(self, stage: str) -> dict[str, str]:
        """Read source authority for preparation; never reinterpret a frozen delivery."""
        return current_execution_pin(stage)

    def _projection(self, request, execution_pin, *, executor_backend="specialist_chat",
                    plotloom_code_revision=None):
        return project_creative_package(self._job_root(request.job_id), request, execution_pin,
            executor_backend=executor_backend, plotloom_code_revision=plotloom_code_revision)

    def read_delivery(
        self, request: CreativeHandoffRequest, execution_pin: dict[str, str], *,
        executor_backend: str = "specialist_chat", executor_attempt: CodexExecAttempt | None = None,
        executor_profile: CodexExecProfile | None = None, executor_receipt: CodexExecReceipt | None = None,
        plotloom_code_revision: str | None = None,
    ) -> ValidatedCreativeDelivery | None:
        request.assert_secret_free()
        job_root, projected = self._verify_frozen_package(
            request, execution_pin, executor_backend=executor_backend,
            plotloom_code_revision=plotloom_code_revision,
        )
        delivery = job_root / "delivery"
        names = self._names(delivery)
        if not names:
            return None
        if names != {COMPLETION_FILENAME, projected["candidateFilename"], projected["reportFilename"]}:
            raise CreativeHandoffError("delivery_partial", "delivery must contain exactly the declared candidate, report, and manifest")
        try:
            manifest = CreativeDeliveryManifest.model_validate(json.loads(_read_regular(delivery / COMPLETION_FILENAME, max_bytes=1_000_000)))
        except (json.JSONDecodeError, ValidationError) as error:
            raise CreativeHandoffError("delivery_manifest_invalid", "completion manifest does not match the creative handoff contract") from error
        manifest.assert_secret_free()
        if executor_backend == "specialist_chat":
            if manifest.schema_version != 1:
                raise CreativeHandoffError("delivery_execution_mismatch", "specialist delivery cannot claim Codex Exec identity")
        elif executor_backend == "codex_exec":
            if executor_attempt is None or executor_profile is None or executor_receipt is None:
                raise CreativeHandoffError("delivery_executor_evidence_missing", "Codex Exec delivery requires its exact project attempt and host receipt")
            try:
                assert_receipt_matches_attempt(executor_attempt, executor_receipt)
            except (TypeError, ValueError) as error:
                raise CreativeHandoffError("delivery_executor_evidence_invalid", "Codex Exec delivery receipt is invalid") from error
            from .codex_exec_validation import validation_plan_from_package
            try:
                validation_plan = validation_plan_from_package(projected)
            except (KeyError, TypeError, ValueError) as error:
                raise CreativeHandoffError(
                    "delivery_executor_evidence_invalid", "Codex Exec package has no trusted validation plan",
                ) from error
            text_validation = executor_receipt.text_validation
            if (executor_profile.contract_version != "plotloom.codex-exec.v8"
                    or executor_attempt.validation_plan_hash != validation_plan.plan_hash
                    or executor_receipt.validation_plan_hash != validation_plan.plan_hash
                    or text_validation is None
                    or manifest.schema_version != 3 or manifest.executor_backend != "codex_exec"
                    or manifest.executor_attempt_id != executor_attempt.attempt_id
                    or manifest.codex_session_id != executor_receipt.session_id
                    or manifest.executor_profile_hash != executor_profile.profile_hash
                    or manifest.validation_plan_hash != validation_plan.plan_hash
                    or manifest.validation_evidence_hash != text_validation.evidence_hash
                    or executor_attempt.profile_hash != executor_profile.profile_hash
                    or manifest.executor_provenance.model != executor_profile.model
                    or manifest.executor_provenance.reasoning_effort != executor_profile.reasoning_effort):
                raise CreativeHandoffError("delivery_execution_mismatch", "creative delivery differs from its exact Codex Exec host receipt")
            if (executor_attempt.plotloom_code_revision != plotloom_code_revision
                    or executor_receipt.plotloom_code_revision != plotloom_code_revision
                    or manifest.executor_provenance.code_revision != plotloom_code_revision):
                raise CreativeHandoffError("delivery_execution_mismatch", "creative delivery differs from the frozen Plotloom source revision")
            receipt_outputs = {item.output_relative_path: item for item in executor_receipt.outputs}
            if any(
                (output := receipt_outputs.get(f"delivery/{declared.filename}")) is None
                or output.output_hash != declared.sha256
                for declared in (manifest.candidate, manifest.report)
            ) or set(receipt_outputs) != {f"delivery/{manifest.candidate.filename}", f"delivery/{manifest.report.filename}"}:
                raise CreativeHandoffError("delivery_executor_evidence_invalid", "creative manifest outputs differ from the exact host receipt inventory")
        else:
            raise CreativeHandoffError("execution_backend_invalid", "creative delivery execution backend is unsupported")
        frozen_hash = request_hash(request)
        if manifest.job_id != request.job_id or manifest.request_hash != frozen_hash or manifest.stage != request.stage:
            raise CreativeHandoffError("delivery_identity_mismatch", "completion manifest does not belong to this frozen creative request")
        if manifest.candidate.filename != projected["candidateFilename"] or manifest.report.filename != projected["reportFilename"]:
            raise CreativeHandoffError("delivery_identity_mismatch", "completion manifest names unsupported outputs")
        expected_pin = projected["executionPin"]
        provenance = manifest.executor_provenance
        if (
            provenance.skill_hash != expected_pin["specialistSkillHash"]
            or provenance.upstream_revision != expected_pin["upstreamRevision"]
            or provenance.upstream_skill_hash != expected_pin["upstreamSkillHash"]
        ):
            raise CreativeHandoffError("delivery_execution_mismatch", "delivery was not produced with the pinned specialist and upstream skill")
        if request.stage in {"bridge-intent", "bridge-presentation", "video-directions"} and (
            provenance.code_revision != expected_pin["upstreamRevision"]
            or provenance.skill_version != f"plotloom-{request.stage.removeprefix('bridge-')}-specialist.v1"
        ):
            raise CreativeHandoffError("delivery_execution_mismatch", "native intent delivery does not match its pinned local execution revision")
        candidate_bytes = _read_regular(delivery / manifest.candidate.filename, max_bytes=2_000_000)
        report = _read_regular(delivery / manifest.report.filename, max_bytes=2_000_000)
        if sha256(candidate_bytes).hexdigest() != manifest.candidate.sha256 or sha256(report).hexdigest() != manifest.report.sha256:
            raise CreativeHandoffError("delivery_hash_mismatch", "delivery bytes do not match declared hashes")
        try:
            candidate = json.loads(candidate_bytes)
        except json.JSONDecodeError as error:
            raise CreativeHandoffError("delivery_candidate_invalid", "candidate is not valid JSON") from error
        if not isinstance(candidate, dict):
            raise CreativeHandoffError("delivery_candidate_invalid", "candidate must be a JSON object")
        if not report.lstrip().lower().startswith((b"<!doctype html", b"<html")):
            raise CreativeHandoffError("delivery_report_invalid", "report must be an HTML-derived view")
        if request.stage == "outline":
            from .outline_report_metadata import (
                assert_outline_report_metadata,
                assert_outline_report_schema_current,
            )

            assert_outline_report_schema_current(request.input_artifacts)
            assert_outline_report_metadata(candidate)
        return ValidatedCreativeDelivery(
            request=request, manifest=manifest,
            manifest_hash=sha256(canonical_json(manifest.model_dump(mode="json", by_alias=True))).hexdigest(),
            candidate=candidate, report=report,
        )

    @staticmethod
    def assert_current(delivery: ValidatedCreativeDelivery, *, current_stage_revision: int) -> None:
        """Let the existing review/canonical owner reject stale candidates before install."""

        if delivery.request.expected_stage_revision != current_stage_revision:
            raise CreativeHandoffError("delivery_stale", "candidate was prepared against a stale accepted stage revision")
