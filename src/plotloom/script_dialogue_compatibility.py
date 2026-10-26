"""Explicit prospective F5 requirements; no future Script or dispatch authority."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Literal

from pydantic import Field, model_validator

from .canonical_schema import DialogueTimingProfile, default_dialogue_timing_profile
from plotloom.domain_base import CamelModel
from .production_dialogue_timing import DIALOGUE_NORMALIZATION_VERSION, projected_dialogue_timing


def _profile_hash(profile: DialogueTimingProfile) -> str:
    payload = profile.model_dump(mode="json", by_alias=True)
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class PlannedStoryboardDialogue(CamelModel):
    version: Literal["plotloom.planned-storyboard-dialogue.v1"] = "plotloom.planned-storyboard-dialogue.v1"
    max_cut_seconds: int = Field(strict=True, ge=2, le=15)
    language: str = Field(min_length=1)
    profile: DialogueTimingProfile
    profile_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalization_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _profile_identity(self):
        if self.profile_hash != _profile_hash(self.profile):
            raise ValueError("planned storyboard profile identity differs from its rules")
        return self


def freeze_planned_storyboard_dialogue(*, max_cut_seconds: int, language: str) -> PlannedStoryboardDialogue:
    profile = default_dialogue_timing_profile()
    return PlannedStoryboardDialogue(max_cut_seconds=max_cut_seconds, language=language,
        profile=profile, profile_hash=_profile_hash(profile),
        normalization_version=DIALOGUE_NORMALIZATION_VERSION)


def planned_dialogue_from_admission(admission: Any) -> PlannedStoryboardDialogue | None:
    value = admission.get("plannedStoryboardDialogue") if isinstance(admission, dict) else None
    return PlannedStoryboardDialogue.model_validate(value) if value is not None else None


def assert_current_planned_dialogue(planned: PlannedStoryboardDialogue) -> None:
    current = freeze_planned_storyboard_dialogue(max_cut_seconds=planned.max_cut_seconds,
        language=planned.language)
    if current != planned:
        raise ValueError("planned storyboard dialogue profile or normalization changed")


def assert_planned_dialogue_necessary_bounds(script: dict[str, Any], *, planned: PlannedStoryboardDialogue,
        section_episodes: dict[str, int], routes: list[list[str]], route_only: list[str],
        maximum_seconds: int) -> None:
    """Necessary per-line/route lower bounds, never proof of a complete schedule."""
    assert_current_planned_dialogue(planned)
    episode_minima = {}
    for episode in script["episodes"]:
        total = 0
        for scene in episode["scenes"]:
            for flow in scene["flow"]:
                if not isinstance(flow, dict) or not isinstance(flow.get("line"), str):
                    continue
                minimum = projected_dialogue_timing(flow, planned.language)["estimatedDurationUnits"]
                if minimum > planned.max_cut_seconds * 1000:
                    raise ValueError("F4 dialogue cannot fit the planned storyboard maximum cut duration")
                total += minimum
        episode_minima[episode["ep"]] = total
    section_minima = {section: episode_minima[episode] for section, episode in section_episodes.items()}
    route_only_ids = set(route_only)
    for route in routes:
        lower_bound = sum(section_minima[section] for section in route if section not in route_only_ids)
        if lower_bound > maximum_seconds * 1000:
            raise ValueError("canonical dialogue lower bound exceeds the complete route maximum")


def planned_dialogue_instructions(planned: PlannedStoryboardDialogue | None) -> str:
    if planned is None:
        return ""
    return (
        " script-admission.json.plannedStoryboardDialogue freezes an explicitly selected prospective F5 "
        f"dialogue requirement: spoken language {planned.language}, maximum indivisible line duration "
        f"{planned.max_cut_seconds * 1000} ms, canonical profile {planned.profile.version}. "
        "Trusted code owns the frozen rules and normalization, not the model. Keep every line, including VO, "
        "within that maximum and the canonical dialogue-only lower bound of every complete route within the "
        "author maximum. Report lang and upstream charsPerSecond do not change these canonical minima. "
        "Free-form performance notes do not select a faster pace; do not rewrite the requirement or add "
        "timing minima to the response. These are necessary constraints, not a guarantee of a complete F5 "
        "schedule; all upstream creative gates and the later independent F5/Bridge gates still apply."
    )
