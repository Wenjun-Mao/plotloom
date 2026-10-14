"""Stage validator routing from the frozen creative request's style authority."""
from __future__ import annotations

from dataclasses import dataclass


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
    """Keep the selected authority explicit while reserving execution for the host."""
    return (
        f"The frozen inputs/{route.contract_filename} selects saved-Brief authority and its neutral Plotloom adapter. "
        "Preserve every other requirement in this stage's pinned upstream skill and frozen request. The trusted "
        "host applies this route from the frozen validation plan after the candidate is written; do not invoke the "
        "adapter or write the report yourself. "
    )


def codex_exec_stage_validator_instructions(stage: str, package_request: dict, job_root=None) -> str:
    """Describe the frozen visual-style authority without asking the model to execute it."""
    route = codex_exec_saved_brief_route(stage, package_request)
    if route:
        return saved_brief_codex_exec_instructions(route)
    if stage == "characters":
        return "Follow the frozen preset style contract. The trusted host validates and renders through the plan after the candidate is written. "
    if stage == "art":
        return "Follow the frozen art style and cast inputs. The trusted host validates and renders through the plan after the candidate is written. "
    if stage == "storyboard":
        return "The trusted host validates and renders through the frozen plan after the candidate is written. "
    raise ValueError(f"stage {stage!r} has no Codex Exec visual-style validator instructions")
