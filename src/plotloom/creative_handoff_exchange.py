"""Filesystem exchange for a one-stage, candidate-only creative handoff."""
from __future__ import annotations

import json
import os
import shlex
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
from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)


PACKAGE_VERSION = 1
COMPLETION_FILENAME = "completion.json"
TEMPLATE_FILENAME = "completion-manifest.example.json"
EXECUTION_PIN_KEYS = frozenset({"upstreamRevision", "upstreamSkillHash", "specialistSkillHash"})


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


def execution_pin_for_request(
    request: CreativeHandoffRequest, execution_pin: dict[str, str] | Any
) -> dict[str, str]:
    """Validate a trusted stored pin before it influences package checks."""

    if not isinstance(execution_pin, dict) or set(execution_pin) != EXECUTION_PIN_KEYS:
        raise CreativeHandoffError("execution_pin_missing", "creative handoff execution pin is malformed")
    pin = {key: execution_pin[key] for key in EXECUTION_PIN_KEYS}
    if (
        not all(isinstance(value, str) for value in pin.values())
        or len(pin["upstreamRevision"]) < 7
        or len(pin["upstreamRevision"]) > 64
        or any(character not in "0123456789abcdef" for character in pin["upstreamRevision"])
        or any(len(pin[key]) != 64 or any(character not in "0123456789abcdef" for character in pin[key]) for key in ("upstreamSkillHash", "specialistSkillHash"))
    ):
        raise CreativeHandoffError("execution_pin_missing", "creative handoff execution pin is malformed")
    return pin


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
        return {"branches": "branches.json", "outline": "outline.json", "characters": "cast.json", "art": "art.json", "script": "script.json", "storyboard": "storyboard.json", "bridge-intent": "intent.json", "bridge-presentation": "presentation.json"}[stage]

    @staticmethod
    def _pinned_execution(stage: str) -> dict[str, str]:
        """Freeze the vendored skill and local specialist used by a package."""

        repository = Path(__file__).resolve().parents[2]
        if stage in {"bridge-intent", "bridge-presentation"}:
            name = "intent" if stage == "bridge-intent" else "presentation"
            dirty = subprocess.run(["git", "-C", str(repository), "status", "--porcelain", "--",
                "src/plotloom", f"scripts/native_bridge_{name}.py", f"docs/creative-workflow/native-bridge-{name}.md",
                f".agents/skills/plotloom-{name}-specialist"], capture_output=True, text=True, check=False)
            if dirty.returncode != 0 or dirty.stdout.strip():
                raise CreativeHandoffError("execution_pin_missing", "native intent execution source must be committed before preparing a package")
            revision = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            return {
                "upstreamRevision": revision,
                "upstreamSkillHash": sha256((repository / f"docs/creative-workflow/native-bridge-{name}.md").read_bytes()).hexdigest(),
                "specialistSkillHash": sha256((repository / f".agents/skills/plotloom-{name}-specialist/SKILL.md").read_bytes()).hexdigest(),
            }
        submodule = repository / "third_party" / "shuohao-skills"
        stage = "outline" if stage == "branches" else stage
        upstream_skill = repository / "third_party" / "shuohao-skills" / "skills" / f"novel-{stage}" / "SKILL.md"
        specialist_skill = repository / ".agents" / "skills" / "plotloom-shuohao-specialist" / "SKILL.md"
        if not upstream_skill.is_file() or not specialist_skill.is_file():
            raise CreativeHandoffError(
                "execution_pin_missing",
                "pinned upstream and specialist skills must exist in the repository checkout",
            )
        gitlink = subprocess.run(
            ["git", "-C", str(repository), "ls-tree", "HEAD", "--", "third_party/shuohao-skills"],
            capture_output=True, text=True, check=False,
        )
        lines = gitlink.stdout.strip().splitlines()
        if gitlink.returncode != 0 or len(lines) != 1:
            raise CreativeHandoffError("execution_pin_missing", "recorded Shuohao submodule gitlink is unavailable")
        fields = lines[0].split(maxsplit=2)
        if len(fields) != 3 or fields[0] != "160000" or fields[1] != "commit":
            raise CreativeHandoffError("execution_pin_missing", "Shuohao dependency is not a recorded submodule gitlink")
        recorded_revision = fields[2].split("\t", 1)[0]
        revision = subprocess.run(
            ["git", "-C", str(submodule), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        checked_out_revision = revision.stdout.strip()
        if revision.returncode != 0 or checked_out_revision != recorded_revision:
            raise CreativeHandoffError(
                "execution_pin_missing",
                "checked-out Shuohao revision does not match the repository-recorded submodule gitlink",
            )
        return {
            "upstreamRevision": recorded_revision,
            "upstreamSkillHash": sha256(upstream_skill.read_bytes()).hexdigest(),
            "specialistSkillHash": sha256(specialist_skill.read_bytes()).hexdigest(),
        }

    def current_execution_pin(self, stage: str) -> dict[str, str]:
        """Read current checkout authority without changing a frozen candidate."""

        return self._pinned_execution(stage)

    def _projection(
        self, request: CreativeHandoffRequest, execution_pin: dict[str, str], *, executor_backend: str = "specialist_chat"
    ) -> tuple[dict[str, Any], bytes, bytes, set[str]]:
        if executor_backend not in {"specialist_chat", "codex_exec"}:
            raise CreativeHandoffError("execution_backend_invalid", "creative package execution backend is unsupported")
        frozen_hash = request_hash(request)
        candidate_filename = self._candidate_filename(request.stage)
        projected = request.model_dump(mode="json", by_alias=True) | {
            "packageVersion": 2 if executor_backend == "codex_exec" else PACKAGE_VERSION,
            "requestHash": frozen_hash,
            "candidateFilename": candidate_filename,
            "reportFilename": "report.html",
            "upstreamSkillPath": f"docs/creative-workflow/native-{request.stage}.md" if request.stage in {"bridge-intent", "bridge-presentation"} else f"third_party/shuohao-skills/skills/novel-{'outline' if request.stage == 'branches' else request.stage}/SKILL.md",
            "executionPin": execution_pin_for_request(request, execution_pin),
        }
        if executor_backend == "codex_exec":
            projected["executorBackend"] = "codex_exec"
        character_id_instruction = (
            "For characters, preserve established characters[].id values; every "
            "characters[].id must be unique and nonblank. "
            if request.stage == "characters"
            else ""
        )
        branch_candidate = shlex.quote(str(self._job_root(request.job_id) / "delivery" / "branches.json"))
        branch_request = shlex.quote(str(self._job_root(request.job_id) / "package" / "request.json"))
        branch_report = shlex.quote(str(self._job_root(request.job_id) / "delivery" / "report.html"))
        branch_instruction = (
            "For branches, upstream outline is narrative guidance only. Output strictly inputs/branch-schema.json; "
            "Preserve every planned node, choice-option and join ID and order from source.topology. Do not emit an upstream outline or invent topology. "
            f"From the repository root, run uv run --locked python scripts/branch_suggestion.py validate {branch_candidate} --request {branch_request}, then "
            f"uv run --locked python scripts/branch_suggestion.py render {branch_candidate} --request {branch_request} > {branch_report}. Disclose ambiguous proposals in clarifications. "
            if request.stage == "branches" else ""
        )
        intent_instruction = (
            "For bridge-intent, the local native intent contract replaces upstream stage authoring. "
            "Output exactly inputs/intent-schema.json: every frozen target exactly once, only id and suggestedText. "
            "From the repository root run uv run --locked python scripts/native_bridge_intent.py validate <absolute-delivery/intent.json> --request <absolute-package/request.json>, "
            "then render with the same arguments to derive report.html. "
            if request.stage == "bridge-intent" else ""
        )
        presentation_instruction = (
            "For bridge-presentation, use the local presentation contract and inputs/presentation-schema.json. "
            "Return every frozen source ID with exhaustive ordered Unicode-codepoint ownership spans, faithful rendering and required reasons. "
            "From the repository root run uv run --locked python scripts/native_bridge_presentation.py validate <absolute-delivery/presentation.json> --request <absolute-package/request.json>, "
            "then render with the same arguments to derive report.html. Suggestions do not approve presentation or production. "
            if request.stage == "bridge-presentation" else ""
        )
        if executor_backend == "codex_exec":
            instructions = (
                "Read request.json, each inputs/*.json file, and the pinned upstream skill path. "
                f"Write only the stage-shaped candidate JSON to ../delivery/{candidate_filename} and derive "
                "../delivery/report.html from that candidate. Do not write completion.json or other files; "
                "the trusted Codex Exec host publishes completion after the exact output inventory is checked. "
                f"{character_id_instruction}{branch_instruction}{intent_instruction}{presentation_instruction}"
                "This is a candidate only: do not edit project canon, approvals, selections, or request files.\n"
            ).encode()
            return projected, instructions, b"", {"request.json", "COPY_ASSIGNMENT.txt", "inputs"}
        instructions = (
            "Read request.json, each inputs/*.json file, and the pinned upstream skill path. "
            f"Write the stage-shaped candidate JSON to the sibling ../delivery/{candidate_filename}, then derive "
            "../delivery/report.html from that candidate. Never create package/delivery. Finally publish "
            "../delivery/completion.json once. "
            f"{character_id_instruction}{branch_instruction}{intent_instruction}{presentation_instruction}"
            "This is a candidate only: do not edit project canon, approvals, selections, or request files.\n"
        ).encode()
        template = canonical_json({
            "schemaVersion": 1, "jobId": request.job_id, "requestHash": frozen_hash,
            "deliveryId": "replace-with-specialist-delivery-id", "stage": request.stage,
            "candidate": {"filename": candidate_filename, "sha256": "0" * 64},
            "report": {"filename": "report.html", "sha256": "0" * 64},
            "executorProvenance": {
                "codeRevision": "checked-out-commit", "skillVersion": f"plotloom-{request.stage.removeprefix('bridge-')}-specialist.v1" if request.stage in {"bridge-intent", "bridge-presentation"} else "plotloom-shuohao-specialist.v1",
                "skillHash": projected["executionPin"]["specialistSkillHash"],
                "upstreamRevision": projected["executionPin"]["upstreamRevision"],
                "upstreamSkillHash": projected["executionPin"]["upstreamSkillHash"],
                "model": None, "reasoningEffort": None,
            }, "limitations": [],
        })
        return projected, instructions, template, {"request.json", "COPY_ASSIGNMENT.txt", TEMPLATE_FILENAME, "inputs"}

    def _verify_frozen_package(
        self, request: CreativeHandoffRequest, execution_pin: dict[str, str], *, executor_backend: str = "specialist_chat"
    ) -> tuple[Path, dict[str, Any]]:
        """Confirm every specialist-consumed package file still matches its projection."""

        job_root = self._job_root(request.job_id)
        package = job_root / "package"
        projected, instructions, template, expected = self._projection(request, execution_pin, executor_backend=executor_backend)
        names = self._names(package, package=True)
        if names != expected:
            raise CreativeHandoffError("package_conflict", "existing package has unexpected entries")
        if _read_regular(package / "request.json", max_bytes=1_000_000, package=True) != canonical_json(projected):
            raise CreativeHandoffError("package_conflict", "existing package differs from frozen request")
        if _read_regular(package / "COPY_ASSIGNMENT.txt", max_bytes=20_000, package=True) != instructions:
            raise CreativeHandoffError("package_conflict", "existing package instructions differ from frozen request")
        if executor_backend == "specialist_chat" and _read_regular(package / TEMPLATE_FILENAME, max_bytes=20_000, package=True) != template:
            raise CreativeHandoffError("package_conflict", "existing package template differs from frozen request")
        inputs = package / "inputs"
        if self._names(inputs, package=True) != set(request.input_artifacts):
            raise CreativeHandoffError("package_conflict", "existing package inputs differ from frozen request")
        for filename, payload in request.input_artifacts.items():
            if _read_regular(inputs / filename, max_bytes=1_000_000, package=True) != canonical_json(payload):
                raise CreativeHandoffError("package_conflict", "existing package input differs from frozen request")
        return job_root, projected

    def verified_package_paths(
        self, request: CreativeHandoffRequest, execution_pin: dict[str, str], *, executor_backend: str = "specialist_chat"
    ) -> dict[str, str]:
        """Recover an existing handoff without creating or repairing frozen files."""
        request.assert_secret_free()
        job_root, _ = self._verify_frozen_package(request, execution_pin, executor_backend=executor_backend)
        return {"packagePath": str(job_root / "package"), "deliveryPath": str(job_root / "delivery")}

    def write_package(
        self, request: CreativeHandoffRequest, execution_pin: dict[str, str], *, executor_backend: str = "specialist_chat"
    ) -> dict[str, str]:
        request.assert_secret_free()
        job_root = self._job_root(request.job_id)
        package = job_root / "package"
        projected, instructions, template, expected = self._projection(request, execution_pin, executor_backend=executor_backend)
        self._names(package, package=True)
        if package.exists():
            self._verify_frozen_package(request, execution_pin, executor_backend=executor_backend)
            return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}
        from .creative_package_publication import publish_package
        files = {**{f"inputs/{filename}": canonical_json(payload) for filename, payload in request.input_artifacts.items()},
            "request.json": canonical_json(projected), "COPY_ASSIGNMENT.txt": instructions}
        if executor_backend == "specialist_chat":
            files[TEMPLATE_FILENAME] = template
        publish_package(package, digest=request_hash(request), files=files, write_once=_write_once)
        self._verify_frozen_package(request, execution_pin, executor_backend=executor_backend)
        return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}

    def read_delivery(
        self, request: CreativeHandoffRequest, execution_pin: dict[str, str], *,
        executor_backend: str = "specialist_chat", executor_attempt: CodexExecAttempt | None = None,
        executor_profile: CodexExecProfile | None = None, executor_receipt: CodexExecReceipt | None = None,
    ) -> ValidatedCreativeDelivery | None:
        request.assert_secret_free()
        job_root, projected = self._verify_frozen_package(request, execution_pin, executor_backend=executor_backend)
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
            if (manifest.schema_version != 2 or manifest.executor_backend != "codex_exec"
                    or manifest.executor_attempt_id != executor_attempt.attempt_id
                    or manifest.codex_session_id != executor_receipt.session_id
                    or manifest.executor_profile_hash != executor_profile.profile_hash
                    or executor_attempt.profile_hash != executor_profile.profile_hash
                    or manifest.executor_provenance.model != executor_profile.model
                    or manifest.executor_provenance.reasoning_effort != executor_profile.reasoning_effort):
                raise CreativeHandoffError("delivery_execution_mismatch", "creative delivery differs from its exact Codex Exec host receipt")
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
        if request.stage in {"bridge-intent", "bridge-presentation"} and (
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
