"""One trusted F4 dialogue normalization for F5 receiving and canonical Bridge."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Literal

from pydantic import Field, model_validator

from .canonical_schema import DialogueDeliveryPace, default_dialogue_timing_profile
from .domain import CamelModel

TIMING_FILENAME = "dialogue-timing-contract.json"
TIMING_VERSION = "plotloom.f5-dialogue-timing.v1"


def projected_dialogue_timing(value: dict[str, Any], language: str) -> dict[str, Any]:
    """Free-form performance notes are not a machine-selected delivery pace."""
    source_delivery = value.get("delivery")
    pace = source_delivery if source_delivery in ("measured", "natural", "brisk") else "natural"
    estimate = default_dialogue_timing_profile().estimate_text_duration_units(
        text=value["line"], language=language, delivery=pace,
    )
    if estimate is None or estimate < 1:
        raise ValueError("F4 dialogue has no positive canonical language/delivery estimate")
    return {
        "language": language, "delivery": pace,
        "performanceNotes": source_delivery if isinstance(source_delivery, str) else "",
        "estimatedDurationUnits": estimate,
    }


class FrozenDialogueMinimum(CamelModel):
    episode: int = Field(ge=1)
    scene_index: int = Field(ge=1)
    flow_index: int = Field(ge=1)
    text_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    delivery: DialogueDeliveryPace
    minimum_duration_units: int = Field(ge=1)


class FrozenF5DialogueTiming(CamelModel):
    version: Literal["plotloom.f5-dialogue-timing.v1"] = TIMING_VERSION
    script_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    language: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    lines: list[FrozenDialogueMinimum]
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def _unique_source_coordinates(self) -> FrozenF5DialogueTiming:
        coordinates = [(line.episode, line.scene_index, line.flow_index) for line in self.lines]
        if len(coordinates) != len(set(coordinates)):
            raise ValueError("frozen dialogue source coordinates must be unique")
        payload = self.model_dump(mode="json", by_alias=True, exclude={"content_hash"})
        if self.content_hash != _digest(payload):
            raise ValueError("frozen dialogue timing content hash differs")
        return self


def _digest(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def freeze_f5_dialogue_timing(
    script: dict[str, Any], *, script_content_hash: str, language: str,
) -> FrozenF5DialogueTiming:
    lines = []
    for episode in script["episodes"]:
        for scene_index, scene in enumerate(episode["scenes"], 1):
            for flow_index, value in enumerate(scene["flow"], 1):
                if not isinstance(value, dict) or not isinstance(value.get("line"), str):
                    continue
                timing = projected_dialogue_timing(value, language)
                lines.append(FrozenDialogueMinimum(
                    episode=episode["ep"], scene_index=scene_index, flow_index=flow_index,
                    text_hash=sha256(value["line"].encode("utf-8")).hexdigest(),
                    delivery=timing["delivery"], minimum_duration_units=timing["estimatedDurationUnits"],
                ))
    payload = {
        "version": TIMING_VERSION, "scriptContentHash": script_content_hash, "language": language,
        "profileVersion": default_dialogue_timing_profile().version,
        "lines": [line.model_dump(mode="json", by_alias=True) for line in lines],
    }
    return FrozenF5DialogueTiming.model_validate(payload | {"contentHash": _digest(payload)})


def assert_f5_dialogue_capacity(contract: FrozenF5DialogueTiming, *, max_cut_seconds: int) -> None:
    """Refuse impossible source scheduling before creating a provider job."""
    if any(line.minimum_duration_units > max_cut_seconds * 1000 for line in contract.lines):
        raise ValueError("F4 dialogue cannot fit the chosen F5 maximum cut duration")
