"""Shared F4 mapping, route and optional prospective dialogue admission."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from .authored_route_timing import route_budget_hash, validate_route_seconds
from plotloom.domain_base import CamelModel
from .script_contracts import ScriptBinding, ScriptSectionBinding
from .script_dialogue_compatibility import PlannedStoryboardDialogue, assert_planned_dialogue_necessary_bounds


class ScriptAdmission(CamelModel):
    target_playthrough_seconds: int = Field(ge=3)
    route_budget_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_bindings: list[ScriptSectionBinding] = Field(min_length=1)
    complete_route_section_ids: list[list[str]] = Field(min_length=1)
    route_only_section_ids: list[str]
    planned_storyboard_dialogue: PlannedStoryboardDialogue | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def _exact_budget(self):
        expected = route_budget_hash(target_seconds=self.target_playthrough_seconds,
            section_bindings=[v.model_dump(mode="json", by_alias=True) for v in self.section_bindings],
            routes=self.complete_route_section_ids, route_only_ids=self.route_only_section_ids)
        if self.route_budget_hash != expected:
            raise ValueError("script admission route budget differs")
        return self


def script_admission_artifact(binding: ScriptBinding) -> dict[str, Any]:
    fields = ScriptAdmission.model_fields
    return ScriptAdmission(**{name: getattr(binding, name) for name in fields}).model_dump(mode="json", by_alias=True)


def section_bindings(script: dict[str, Any], binding: ScriptBinding | ScriptAdmission) -> dict[str, int]:
    entries = script.get("sectionBindings")
    if not isinstance(entries, list):
        raise ValueError("script must contain Plotloom sectionBindings")
    try:
        bindings = [ScriptSectionBinding.model_validate(item) for item in entries]
    except ValueError as error:
        raise ValueError("script sectionBindings are invalid") from error
    if bindings != binding.section_bindings:
        raise ValueError("script sectionBindings must exactly match the frozen section-to-episode mapping")
    episodes = script.get("episodes")
    if not isinstance(episodes, list) or {item.get("ep") for item in episodes if isinstance(item, dict)} != {item.episode for item in bindings} or len(episodes) != len(bindings):
        raise ValueError("script episodes must match sectionBindings exactly")
    return {item.section_id: item.episode for item in bindings}


def upstream_timing_stats(script_path: Path, validator: Path, *, node: str = "node") -> dict[str, Any]:
    program = (
        f"import {{ computeStats }} from {json.dumps(validator.as_uri())};"
        "import { readFileSync } from 'node:fs';"
        "console.log(JSON.stringify(computeStats(JSON.parse(readFileSync(process.argv[1], 'utf8')))));"
    )
    result = subprocess.run([node, "--input-type=module", "--eval", program, str(script_path)],
        capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError("upstream novel-script timing estimator is unavailable")
    try:
        stats = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("upstream novel-script timing estimator returned invalid data") from error
    if not isinstance(stats, dict) or not isinstance(stats.get("episodes"), list):
        raise ValueError("upstream novel-script timing estimator returned incomplete data")
    return stats


def validate_timing_caps(script: dict[str, Any], binding: ScriptBinding | ScriptAdmission, stats: dict[str, Any]) -> None:
    by_episode = {item.get("ep"): item for item in stats["episodes"]
        if isinstance(item, dict) and isinstance(item.get("ep"), int)}
    actual, targets = {}, {}
    for section in binding.section_bindings:
        episode = by_episode.get(section.episode)
        if episode is None:
            raise ValueError("script timing is missing a frozen section")
        actual[section.section_id], targets[section.section_id] = episode.get("est"), episode.get("target")
    for durations, label in ((actual, "script estimated"), (targets, "script target")):
        validate_route_seconds(durations=durations, routes=binding.complete_route_section_ids,
            route_only_ids=binding.route_only_section_ids, maximum=binding.target_playthrough_seconds, label=label)


def validate_script_receiving(script: dict[str, Any], admission: ScriptAdmission, stats: dict[str, Any]) -> None:
    mapping = section_bindings(script, admission)
    validate_timing_caps(script, admission, stats)
    if admission.planned_storyboard_dialogue is not None:
        assert_planned_dialogue_necessary_bounds(script, planned=admission.planned_storyboard_dialogue,
            section_episodes=mapping, routes=admission.complete_route_section_ids,
            route_only=admission.route_only_section_ids, maximum_seconds=admission.target_playthrough_seconds)
