"""Frozen, source-owned validator plans and successful validation evidence."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Literal

from pydantic import Field, model_validator

from .codex_exec_constants import HASH
from .domain import CamelModel

_PLACEHOLDER = re.compile(r"\{(?:source|submodule|package|delivery|candidate|report|input:[A-Za-z0-9_.-]+|tool:(?:uv|node))\}")


def _hash(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class CodexExecValidationInput(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    filename: str = Field(min_length=1, max_length=180)
    sha256: str = Field(pattern=HASH)
    size_bytes: int = Field(ge=2, le=1_000_000)


class CodexExecValidationStep(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    step_id: Literal["validate", "render"]
    program: Literal["uv", "node"]
    argv: tuple[str, ...] = Field(min_length=2, max_length=48)
    stdout_is_report: bool = False

    @model_validator(mode="after")
    def fixed_confined_arguments(self):
        if not self.argv or any("\x00" in token or len(token) > 1024 for token in self.argv):
            raise ValueError("validation argv must contain bounded, NUL-free tokens")
        for token in self.argv:
            for found in re.findall(r"\{[^{}]*\}", token):
                if _PLACEHOLDER.fullmatch(found) is None:
                    raise ValueError("validation argv contains an unsupported path placeholder")
        if self.stdout_is_report != (self.step_id == "render"):
            raise ValueError("only the trusted renderer may write the report through stdout")
        return self


class CodexExecTextValidationPlan(CamelModel):
    """Canonical command intent frozen with one fresh text package."""

    model_config = CamelModel.model_config | {"frozen": True}

    schema_version: Literal[1] = 1
    stage: Literal[
        "outline", "branches", "characters", "art", "script", "storyboard",
        "bridge-intent", "bridge-presentation",
    ]
    route: Literal["upstream", "preset_style", "saved_brief", "plotloom_native"]
    request_hash: str = Field(pattern=HASH)
    source_revision: str = Field(pattern=r"^[a-f0-9]{7,64}$")
    execution_pin_hash: str = Field(pattern=HASH)
    candidate_filename: str = Field(min_length=1, max_length=180)
    report_filename: Literal["report.html"] = "report.html"
    inputs: tuple[CodexExecValidationInput, ...] = Field(max_length=64)
    steps: tuple[CodexExecValidationStep, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def ordered_complete_steps(self):
        if tuple(step.step_id for step in self.steps) != ("validate", "render"):
            raise ValueError("text completion requires exactly one ordered validate and render step")
        if self.steps[0].stdout_is_report or not self.steps[1].stdout_is_report:
            raise ValueError("only the second, trusted render step may produce report bytes")
        names = [item.filename for item in self.inputs]
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError("validation inputs must be sorted and unique")
        if self.candidate_filename == self.report_filename:
            raise ValueError("candidate and trusted report names must differ")
        return self

    @property
    def plan_hash(self) -> str:
        return _hash(self.model_dump(mode="json", by_alias=True))


class CodexExecValidationStepEvidence(CamelModel):
    """Private, byte-bound result of one exact trusted validator subprocess."""

    model_config = CamelModel.model_config | {"frozen": True}

    step_id: Literal["validate", "render"]
    argv_hash: str = Field(pattern=HASH)
    exit_code: Literal[0]
    stdout_hash: str = Field(pattern=HASH)
    stdout_size_bytes: int = Field(ge=0, le=50_000_000)
    stderr_hash: str = Field(pattern=HASH)
    stderr_size_bytes: int = Field(ge=0, le=50_000_000)
    duration_ms: int = Field(ge=0, le=7_200_000)


class CodexExecTextValidationEvidence(CamelModel):
    """Proof that trusted validation and rendering accepted the exact bytes."""

    model_config = CamelModel.model_config | {"frozen": True}

    plan_hash: str = Field(pattern=HASH)
    profile_hash: str = Field(pattern=HASH)
    validator_hash: str = Field(pattern=HASH)
    request_hash: str = Field(pattern=HASH)
    package_hash: str = Field(pattern=HASH)
    source_revision: str = Field(pattern=r"^[a-f0-9]{7,64}$")
    candidate_filename: str = Field(min_length=1, max_length=180)
    candidate_hash: str = Field(pattern=HASH)
    candidate_size_bytes: int = Field(ge=1, le=2_000_000)
    report_filename: Literal["report.html"] = "report.html"
    report_hash: str = Field(pattern=HASH)
    report_size_bytes: int = Field(ge=1, le=2_000_000)
    steps: tuple[CodexExecValidationStepEvidence, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def successful_exact_order(self):
        if tuple(step.step_id for step in self.steps) != ("validate", "render"):
            raise ValueError("validation evidence must prove both required steps in order")
        rendered = self.steps[1]
        if (rendered.stdout_hash, rendered.stdout_size_bytes) != (self.report_hash, self.report_size_bytes):
            raise ValueError("trusted renderer stdout must be the exact published report bytes")
        return self

    @property
    def evidence_hash(self) -> str:
        return _hash(self.model_dump(mode="json", by_alias=True))


def build_text_validation_plan(request, *, execution_pin: dict, source_revision: str) -> CodexExecTextValidationPlan:
    """Construct fixed command vectors from the immutable stage request."""
    from .codex_exec_stage_routing import codex_exec_saved_brief_route
    from .creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES
    from .creative_handoff_exchange import request_hash

    if (not isinstance(execution_pin, dict)
            or set(execution_pin) != {"upstreamRevision", "upstreamSkillHash", "specialistSkillHash"}
            or not isinstance(execution_pin["upstreamRevision"], str)
            or re.fullmatch(r"[a-f0-9]{7,64}", execution_pin["upstreamRevision"]) is None
            or any(not isinstance(execution_pin[key], str) or re.fullmatch(HASH, execution_pin[key]) is None
                   for key in ("upstreamSkillHash", "specialistSkillHash"))):
        raise ValueError("text validation requires the exact frozen execution pin")
    if not isinstance(source_revision, str) or re.fullmatch(r"[a-f0-9]{7,64}", source_revision) is None:
        raise ValueError("text validation requires the frozen source revision")
    stage = request.stage
    if stage == "outline":
        from .outline_report_metadata import assert_outline_report_schema_current

        assert_outline_report_schema_current(request.input_artifacts)
    if stage == "storyboard":
        from .production_dialogue_timing import TIMING_FILENAME, FrozenF5DialogueTiming

        frozen_timing = request.input_artifacts.get(TIMING_FILENAME)
        if frozen_timing is None:
            raise ValueError("text validation plan requires frozen canonical dialogue timing")
        FrozenF5DialogueTiming.model_validate(frozen_timing)
    candidate = CREATIVE_CANDIDATE_FILENAMES[stage]
    artifacts = request.input_artifacts
    inputs = tuple(CodexExecValidationInput(
        filename=name,
        sha256=_hash(artifact),
        sizeBytes=len(json.dumps(artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()),
    ) for name, artifact in sorted(artifacts.items()))
    saved_route = codex_exec_saved_brief_route(stage, request.model_dump(mode="json", by_alias=True) | {
        "inputArtifacts": request.model_dump(mode="json", by_alias=True)["inputArtifacts"],
    })

    def input_path(filename: str) -> str:
        if filename not in artifacts:
            raise ValueError(f"text validation plan requires frozen input {filename}")
        return f"{{input:{filename}}}"

    source = "{source}"
    package = "{package}"
    cand = "{candidate}"
    request_path = f"{package}/request.json"
    if stage == "branches":
        runner = ("run", "--project", source, "--locked", "--no-sync", "python", f"{source}/scripts/branch_suggestion.py")
        validate = ("uv", runner + ("validate", cand, "--request", request_path))
        render = ("uv", runner + ("render", cand, "--request", request_path))
        route = "plotloom_native"
    elif stage in {"bridge-intent", "bridge-presentation"}:
        script = "native_bridge_intent.py" if stage == "bridge-intent" else "native_bridge_presentation.py"
        runner = ("run", "--project", source, "--locked", "--no-sync", "python", f"{source}/scripts/{script}")
        validate = ("uv", runner + ("validate", cand, "--request", request_path))
        render = ("uv", runner + ("render", cand, "--request", request_path))
        route = "plotloom_native"
    elif stage in {"characters", "art", "storyboard"} and saved_route is not None:
        runner = f"{source}/{saved_route.adapter_path}"
        if stage == "art":
            extra = ("--cast", input_path("cast.json"))
        else:
            extra = ("--request", request_path)
        validate = ("node", (runner, "validate", cand, *extra))
        render = ("node", (runner, "render", cand, *extra))
        route = "saved_brief"
    elif stage == "characters":
        script = "cast-style.mjs"
        contract = input_path("cast-style-contract.json")
        extra = ("--request", request_path, "--contract", contract)
        validate = ("node", (f"{source}/scripts/{script}", "validate", cand, *extra))
        render = ("node", (f"{source}/scripts/{script}", "render", cand, "--html", *extra))
        route = "preset_style"
    elif stage == "art":
        script = "art-style.mjs"
        cast, contract = input_path("cast.json"), input_path("art-style-contract.json")
        extra = ("--cast", cast, "--contract", contract)
        validate = ("node", (f"{source}/scripts/{script}", "validate", cand, *extra))
        render = ("node", (f"{source}/scripts/{script}", "render", cand, "--html", *extra))
        route = "preset_style"
    elif stage == "script":
        from .script_dialogue_compatibility import (
            assert_current_planned_dialogue,
            planned_dialogue_from_admission,
        )
        planned = planned_dialogue_from_admission(artifacts.get("script-admission.json"))
        if planned is not None:
            assert_current_planned_dialogue(planned)
            runner = ("run", "--project", source, "--locked", "--no-sync", "python", f"{source}/scripts/script_receiving.py")
            validate = ("uv", runner + ("validate", cand, "--request", request_path))
            render = ("uv", runner + ("render", cand, "--request", request_path))
            route = "plotloom_native"
        else:
            base = f"{source}/third_party/shuohao-skills/skills/novel-script/scripts/novel-script.mjs"
            validate = ("node", (base, "validate", cand, "--outline", input_path("outline.json"), "--art", input_path("art.json")))
            render = ("node", (base, "render", cand, "--html", "--outline", input_path("outline.json"), "--art", input_path("art.json"), "--cast", input_path("cast.json")))
            route = "upstream"
    elif stage == "storyboard":
        base = f"{source}/scripts/storyboard-receiving.mjs"
        validate = ("node", (base, "validate", cand, "--request", request_path))
        render = ("node", (base, "render", cand, "--request", request_path))
        route = "upstream"
    else:
        base = f"{source}/third_party/shuohao-skills/skills/novel-{stage}/scripts/novel-{stage}.mjs"
        validate = ("node", (base, "validate", cand))
        render = ("node", (base, "render", cand, "--html"))
        route = "upstream"

    steps = tuple(CodexExecValidationStep(
        stepId=step_id, program=program,
        argv=argv,
        stdoutIsReport=(step_id == "render"),
    ) for step_id, (program, argv) in (("validate", validate), ("render", render)))
    pin_hash = _hash(execution_pin)
    return CodexExecTextValidationPlan(
        stage=stage,
        route=route,
        requestHash=request_hash(request),
        sourceRevision=source_revision,
        executionPinHash=pin_hash,
        candidateFilename=candidate,
        inputs=inputs,
        steps=steps,
    )


def validation_plan_from_package(package_request: dict) -> CodexExecTextValidationPlan:
    """Recompute and compare the exact v4 plan; never execute package-supplied argv."""
    from .creative_handoff_contracts import creative_handoff_request_from_package

    if (package_request.get("executorBackend") != "codex_exec"
            or package_request.get("packageVersion") != 4
            or package_request.get("plotloomCodeRevision") is None):
        raise ValueError("fresh Codex text package must contain the v4 trusted validation plan")
    expected = build_text_validation_plan(
        creative_handoff_request_from_package(package_request),
        execution_pin=package_request.get("executionPin"),
        source_revision=package_request["plotloomCodeRevision"],
    )
    actual = package_request.get("validationPlan")
    actual_hash = package_request.get("validationPlanHash")
    if actual != expected.model_dump(mode="json", by_alias=True) or actual_hash != expected.plan_hash:
        raise ValueError("frozen text validation plan does not match source-owned stage policy")
    return expected


def expand_validation_argv(
    step: CodexExecValidationStep, *, source_root, submodule_root, job_root,
    candidate_filename: str, tool_paths,
):
    """Substitute only fixed source, package, delivery and input paths."""
    values = {
        "{source}": str(source_root),
        "{submodule}": str(submodule_root),
        "{package}": str(job_root / "package"),
        "{delivery}": str(job_root / "delivery"),
        "{candidate}": str(job_root / "delivery" / candidate_filename),
        "{report}": str(job_root / "delivery" / "report.html"),
    }
    for name in ("uv", "node"):
        if name in tool_paths:
            values[f"{{tool:{name}}}"] = str(tool_paths[name])
    if step.program not in tool_paths:
        raise ValueError(f"frozen validator runtime is unavailable: {step.program}")
    for item in step.argv:
        if item.startswith("{input:") and item.endswith("}"):
            name = item[7:-1]
            if "/" in name or "\\" in name or name.startswith("."):
                raise ValueError("validation input placeholder is not a plain filename")
            values[item] = str(job_root / "package" / "inputs" / name)
    argv = []
    for token in step.argv:
        for placeholder in re.findall(r"\{[^{}]+\}", token):
            if placeholder not in values:
                raise ValueError("validation argv contains an unknown or unbound path placeholder")
            token = token.replace(placeholder, values[placeholder])
        argv.append(token)
    return (str(tool_paths[step.program]), *argv)
