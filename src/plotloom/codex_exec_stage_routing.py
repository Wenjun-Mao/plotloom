"""Stage validator routing from the frozen creative request's style authority."""
from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodexExecSavedBriefRoute:
    """Neutral validator entrypoint and exact source dependencies for Brief authority."""

    contract_filename: str
    adapter_path: str
    policy_path: str
    candidate_filename: str
    package_arguments: tuple[str, ...]

    @property
    def source_paths(self) -> tuple[str, ...]:
        return (self.adapter_path, self.policy_path)

    @property
    def commands(self) -> tuple[str, str]:
        runner = f'"$PLOTLOOM_NODE" "$PLOTLOOM_SOURCE_ROOT/{self.adapter_path}"'
        arguments = " ".join(self.package_arguments)
        candidate = self.candidate_filename
        return (
            f"{runner} validate {candidate} {arguments}",
            f"{runner} render {candidate} {arguments} > report.html",
        )


_SAVED_BRIEF_STAGE_CONFIG = {
    "characters": CodexExecSavedBriefRoute(
        contract_filename="cast-style-contract.json",
        adapter_path="scripts/brief-cast-style.mjs",
        policy_path="src/plotloom/autopilot_brief_style.py",
        candidate_filename="cast.json",
        package_arguments=("--request", "../package/request.json"),
    ),
    "art": CodexExecSavedBriefRoute(
        contract_filename="art-style-contract.json",
        adapter_path="scripts/brief-art-style.mjs",
        policy_path="src/plotloom/autopilot_brief_style.py",
        candidate_filename="art.json",
        package_arguments=("--cast", "../package/inputs/cast.json"),
    ),
    "storyboard": CodexExecSavedBriefRoute(
        contract_filename="storyboard-style-contract.json",
        adapter_path="scripts/brief-storyboard-style.mjs",
        policy_path="src/plotloom/storyboard_brief_style.py",
        candidate_filename="storyboard.json",
        package_arguments=("--request", "../package/request.json"),
    ),
}


def codex_exec_saved_brief_route(stage: str, package_request: dict) -> CodexExecSavedBriefRoute | None:
    """Return a verified neutral route only for an exact frozen saved-Brief contract."""
    route = _SAVED_BRIEF_STAGE_CONFIG.get(stage)
    if route is None:
        return None
    artifacts = package_request.get("inputArtifacts")
    if not isinstance(artifacts, dict):
        return None
    contract = artifacts.get(route.contract_filename)
    if contract is None:
        return None
    if not isinstance(contract, dict):
        raise TypeError("frozen visual-style contract must be an object")
    if "authority" not in contract:
        return None  # Preset Cast and Art contracts have no authority field.
    if contract.get("authority") != "saved_brief":
        raise ValueError("frozen visual-style authority is unsupported")

    if stage in {"characters", "art"}:
        from .autopilot_brief_style import freeze_brief_style

        direction = contract.get("direction")
        if direction is not None and not isinstance(direction, str):
            raise ValueError("saved-Brief visual direction must be text or null")
        expected = freeze_brief_style(direction)
    else:
        from .storyboard_brief_style import freeze_storyboard_brief_style

        expected = freeze_storyboard_brief_style(contract.get("inheritedArtRenderContract"))
    if contract != expected:
        raise ValueError("frozen saved-Brief visual authority differs from its source contract")
    return route


def saved_brief_codex_exec_instructions(route: CodexExecSavedBriefRoute) -> str:
    """Map repository-root examples to the actual delivery working directory."""
    commands = "\n".join(route.commands)
    return (
        f"The frozen inputs/{route.contract_filename} selects saved-Brief authority and its neutral Plotloom adapter. "
        "Preserve every other requirement in this stage's pinned upstream skill and frozen request. Some source "
        "instructions show their validator commands from the repository root; this CLI stays in the writable "
        "delivery directory. For this Codex assignment, the commands below replace only that shell path base and "
        "entrypoint syntax. They retain the same stage validator, frozen inputs, candidate and report. From the "
        "delivery directory, run exactly:\n"
        f"{commands}\n"
    )


def codex_exec_stage_validator_instructions(stage: str, package_request: dict, job_root: Path) -> str:
    """Build the delivery-CWD validator contract for visual style stages."""
    route = codex_exec_saved_brief_route(stage, package_request)
    if route:
        return saved_brief_codex_exec_instructions(route)
    package = job_root / "package"
    delivery = job_root / "delivery"
    request = shlex.quote(str(package / "request.json"))
    report = shlex.quote(str(delivery / "report.html"))
    if stage == "characters":
        candidate = shlex.quote(str(delivery / "cast.json"))
        contract = shlex.quote(str(package / "inputs" / "cast-style-contract.json"))
        runner = '"$PLOTLOOM_NODE" "$PLOTLOOM_SOURCE_ROOT/scripts/cast-style.mjs"'
        return (
            f"Validate with {runner} validate {candidate} --request {request} --contract {contract}, then "
            f"render with the same arguments using render --html, redirecting to {report}. "
        )
    if stage == "art":
        candidate = shlex.quote(str(delivery / "art.json"))
        cast = shlex.quote(str(package / "inputs" / "cast.json"))
        contract = shlex.quote(str(package / "inputs" / "art-style-contract.json"))
        runner = '"$PLOTLOOM_NODE" "$PLOTLOOM_SOURCE_ROOT/scripts/art-style.mjs"'
        return (
            f"Validate with {runner} validate {candidate} --cast {cast} --contract {contract}, then "
            f"render with the same arguments using render --html, redirecting to {report}. "
        )
    if stage == "storyboard":
        return (
            "Run the stage skill's deterministic validate and render commands against the absolute "
            "candidate/package paths. Do not change to the source checkout as the working directory. "
        )
    raise ValueError(f"stage {stage!r} has no Codex Exec visual-style validator instructions")
