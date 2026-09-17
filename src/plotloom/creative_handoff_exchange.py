"""Filesystem exchange for a one-stage, candidate-only creative handoff."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .creative_handoff_contracts import (
    CreativeDeliveryManifest, CreativeHandoffError, CreativeHandoffRequest,
    is_creative_job_id,
)


PACKAGE_VERSION = 1
COMPLETION_FILENAME = "completion.json"
TEMPLATE_FILENAME = "completion-manifest.example.json"


@dataclass(frozen=True)
class ValidatedCreativeDelivery:
    request: CreativeHandoffRequest
    manifest: CreativeDeliveryManifest
    manifest_hash: str
    candidate: dict[str, Any]
    report: bytes


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def request_hash(request: CreativeHandoffRequest) -> str:
    return sha256(canonical_json(request.model_dump(mode="json", by_alias=True))).hexdigest()


def _read_regular(path: Path, *, max_bytes: int, package: bool = False) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise CreativeHandoffError("delivery_incomplete", "required handoff file is not present") from error
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise CreativeHandoffError("package_conflict" if package else "delivery_path_invalid", "handoff entries must be regular files")
    with path.open("rb") as handle:
        content = handle.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise CreativeHandoffError("package_conflict" if package else "delivery_file_too_large", "handoff file exceeds its size limit")
    return content


def _write_once(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


class CreativeHandoffExchange:
    """Packages immutable requests and reads untrusted specialist candidates."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def _job_root(self, job_id: str) -> Path:
        if not is_creative_job_id(job_id):
            raise CreativeHandoffError("invalid_job_id", "creative handoff job identifier is invalid")
        return self.root / "jobs" / job_id

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
        return {"outline": "outline.json", "characters": "cast.json", "art": "art.json", "script": "script.json", "storyboard": "storyboard.json"}[stage]

    @staticmethod
    def _pinned_execution(request: CreativeHandoffRequest) -> dict[str, str]:
        """Freeze the vendored skill and local specialist used by a package."""

        repository = Path(__file__).resolve().parents[2]
        upstream_skill = repository / "third_party" / "shuohao-skills" / "skills" / f"novel-{request.stage}" / "SKILL.md"
        specialist_skill = repository / ".agents" / "skills" / "plotloom-shuohao-specialist" / "SKILL.md"
        if not upstream_skill.is_file() or not specialist_skill.is_file():
            raise CreativeHandoffError("execution_pin_missing", "pinned upstream and specialist skills must exist in this checkout")
        revision = subprocess.run(
            ["git", "-C", str(repository / "third_party" / "shuohao-skills"), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        if revision.returncode != 0:
            raise CreativeHandoffError("execution_pin_missing", "pinned upstream revision is unavailable")
        return {
            "upstreamRevision": revision.stdout.strip(),
            "upstreamSkillHash": sha256(upstream_skill.read_bytes()).hexdigest(),
            "specialistSkillHash": sha256(specialist_skill.read_bytes()).hexdigest(),
        }

    def _projection(self, request: CreativeHandoffRequest) -> tuple[dict[str, Any], bytes, bytes, set[str]]:
        frozen_hash = request_hash(request)
        candidate_filename = self._candidate_filename(request.stage)
        projected = request.model_dump(mode="json", by_alias=True) | {
            "packageVersion": PACKAGE_VERSION,
            "requestHash": frozen_hash,
            "candidateFilename": candidate_filename,
            "reportFilename": "report.html",
            "upstreamSkillPath": f"third_party/shuohao-skills/skills/novel-{request.stage}/SKILL.md",
            "executionPin": self._pinned_execution(request),
        }
        instructions = (
            "Read request.json, each inputs/*.json file, and the pinned upstream skill path. "
            f"Write the stage-shaped candidate JSON to the sibling ../delivery/{candidate_filename}, then derive "
            "../delivery/report.html from that candidate. Never create package/delivery. Finally publish "
            "../delivery/completion.json once. "
            "This is a candidate only: do not edit project canon, approvals, selections, or request files.\n"
        ).encode()
        template = canonical_json({
            "schemaVersion": 1, "jobId": request.job_id, "requestHash": frozen_hash,
            "deliveryId": "replace-with-specialist-delivery-id", "stage": request.stage,
            "candidate": {"filename": candidate_filename, "sha256": "0" * 64},
            "report": {"filename": "report.html", "sha256": "0" * 64},
            "executorProvenance": {
                "codeRevision": "checked-out-commit", "skillVersion": "plotloom-shuohao-specialist.v1",
                "skillHash": projected["executionPin"]["specialistSkillHash"],
                "upstreamRevision": projected["executionPin"]["upstreamRevision"],
                "upstreamSkillHash": projected["executionPin"]["upstreamSkillHash"],
                "model": None, "reasoningEffort": None,
            }, "limitations": [],
        })
        return projected, instructions, template, {"request.json", "COPY_ASSIGNMENT.txt", TEMPLATE_FILENAME, "inputs"}

    def write_package(self, request: CreativeHandoffRequest) -> dict[str, str]:
        request.assert_secret_free()
        job_root = self._job_root(request.job_id)
        package = job_root / "package"
        package.mkdir(parents=True, exist_ok=True)
        projected, instructions, template, expected = self._projection(request)
        names = self._names(package, package=True)
        if names:
            if names != expected:
                raise CreativeHandoffError("package_conflict", "existing package has unexpected entries")
            if _read_regular(package / "request.json", max_bytes=1_000_000, package=True) != canonical_json(projected):
                raise CreativeHandoffError("package_conflict", "existing package differs from frozen request")
            if _read_regular(package / "COPY_ASSIGNMENT.txt", max_bytes=20_000, package=True) != instructions:
                raise CreativeHandoffError("package_conflict", "existing package instructions differ from frozen request")
            if _read_regular(package / TEMPLATE_FILENAME, max_bytes=20_000, package=True) != template:
                raise CreativeHandoffError("package_conflict", "existing package template differs from frozen request")
            inputs = package / "inputs"
            if self._names(inputs, package=True) != set(request.input_artifacts):
                raise CreativeHandoffError("package_conflict", "existing package inputs differ from frozen request")
            for filename, payload in request.input_artifacts.items():
                if _read_regular(inputs / filename, max_bytes=1_000_000, package=True) != canonical_json(payload):
                    raise CreativeHandoffError("package_conflict", "existing package input differs from frozen request")
            return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}
        inputs = package / "inputs"
        inputs.mkdir(mode=0o700)
        for filename, payload in request.input_artifacts.items():
            _write_once(inputs / filename, canonical_json(payload))
        _write_once(package / "request.json", canonical_json(projected))
        _write_once(package / "COPY_ASSIGNMENT.txt", instructions)
        _write_once(package / TEMPLATE_FILENAME, template)
        return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}

    def read_delivery(self, request: CreativeHandoffRequest) -> ValidatedCreativeDelivery | None:
        request.assert_secret_free()
        job_root = self._job_root(request.job_id)
        package = job_root / "package"
        projected, _, _, _ = self._projection(request)
        if _read_regular(package / "request.json", max_bytes=1_000_000, package=True) != canonical_json(projected):
            raise CreativeHandoffError("package_conflict", "package no longer matches frozen request")
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
