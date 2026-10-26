"""Trusted preparation-era pin validation and current source discovery."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Any
from .codex_exec_resources import upstream_skill_path_for_stage
from .creative_handoff_contracts import CreativeHandoffRequest, CreativeHandoffError
from .creative_handoff_identity import EXECUTION_PIN_KEYS


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


def current_execution_pin(stage: str) -> dict[str, str]:
    """Freeze the vendored skill and local specialist used by a package."""

    repository = Path(__file__).resolve().parents[2]
    from .native_stage_policy import NATIVE_STAGES, native_execution_pin
    if stage in NATIVE_STAGES:
        return native_execution_pin(stage, repository)
    submodule = repository / "third_party" / "shuohao-skills"
    stage = "outline" if stage == "branches" else stage
    upstream_skill_relative = upstream_skill_path_for_stage(stage)
    upstream_skill = repository / upstream_skill_relative
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
    stage_root = Path(upstream_skill_relative).parent.relative_to("third_party/shuohao-skills")
    dirty_stage = subprocess.run(
        ["git", "-C", str(submodule), "status", "--porcelain", "--untracked-files=all", "--", str(stage_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if dirty_stage.returncode != 0 or dirty_stage.stdout.strip():
        raise CreativeHandoffError(
            "execution_pin_missing",
            "pinned Shuohao stage resources must match their recorded submodule revision",
        )
    return {
        "upstreamRevision": recorded_revision,
        "upstreamSkillHash": sha256(upstream_skill.read_bytes()).hexdigest(),
        "specialistSkillHash": sha256(specialist_skill.read_bytes()).hexdigest(),
    }
