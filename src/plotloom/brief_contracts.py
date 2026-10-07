"""Author-owned project Brief and composed generation directions."""
from __future__ import annotations
from typing import Annotated, Any, Literal
from pydantic import Field, field_validator, model_validator
from .domain_base import CamelModel


class DirectionSelection(CamelModel):
    group: Literal["subject", "narrative", "representation", "treatment", "lighting"]
    value: str = Field(min_length=1, max_length=120)

    @field_validator("value")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("direction selection must not be blank")
        return value.strip()


class ProjectBrief(CamelModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    synopsis: Annotated[str, Field(min_length=1)]
    genre: str | None = None
    visual_style: str | None = None
    genre_selections: list[DirectionSelection] = Field(default_factory=list, max_length=40)
    visual_style_selections: list[DirectionSelection] = Field(default_factory=list, max_length=40)
    language: str = "zh-CN"
    aspect_ratio: str = "16:9"
    target_playthrough_seconds: Annotated[int, Field(ge=1)] = 180
    decision_points_per_path: Annotated[int, Field(ge=0)] = 2
    ending_count: Annotated[int, Field(ge=1)] = 3
    node_budget: Annotated[int, Field(ge=1)] = 10
    max_out_degree: Annotated[int, Field(ge=1)] = 3
    desired_join_count: Annotated[int, Field(ge=0)] = 1
    shots_per_scene_min: Annotated[int, Field(ge=1)] = 2
    shots_per_scene_max: Annotated[int, Field(ge=1)] = 4
    shot_count_policy: Literal["strict", "advisory"] = "advisory"

    @model_validator(mode="after")
    def validate_internal_limits(self) -> ProjectBrief:
        for selections, allowed in ((self.genre_selections, {"subject", "narrative"}),
                                    (self.visual_style_selections, {"representation", "treatment", "lighting"})):
            if any(item.group not in allowed for item in selections):
                raise ValueError("direction selection belongs to another field")
            if len({(item.group, item.value) for item in selections}) != len(selections):
                raise ValueError("direction selections must be unique within each group")
        if self.shots_per_scene_min > self.shots_per_scene_max:
            raise ValueError("shots_per_scene_min must not exceed shots_per_scene_max")
        if self.ending_count > self.node_budget:
            raise ValueError("ending_count must not exceed node_budget")
        return self

    @property
    def shot_count_is_strict(self) -> bool:
        return self.shot_count_policy == "strict"

    @property
    def genre_direction(self) -> str | None:
        return self._direction(self.genre_selections, self.genre)

    @property
    def visual_direction(self) -> str | None:
        return self._direction(self.visual_style_selections, self.visual_style)

    @staticmethod
    def _direction(selections: list[DirectionSelection], detail: str | None) -> str | None:
        return "；".join([item.value for item in selections] + ([detail] if detail else [])) or None

    def generation_input(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True) | {
            "genre": self.genre_direction, "visualStyle": self.visual_direction,
        }
