"""Bounded incomplete Brief input; never a confirmed production Brief."""
from typing import Annotated, Literal
from pydantic import Field, StrictInt, StrictStr
from .brief_contracts import DirectionSelection, ProjectBrief
from .domain_base import CamelModel

RawNumber = StrictInt | Annotated[StrictStr, Field(max_length=100)]


class BriefWorkingInput(CamelModel):
    title: str = Field(max_length=200)
    synopsis: str = Field(max_length=200_000)
    genre: str | None = Field(default=None, max_length=10_000)
    visual_style: str | None = Field(default=None, max_length=10_000)
    genre_selections: list[DirectionSelection] = Field(default_factory=list, max_length=40)
    visual_style_selections: list[DirectionSelection] = Field(default_factory=list, max_length=40)
    language: str = Field(default="zh-CN", max_length=80)
    aspect_ratio: str = Field(default="16:9", max_length=80)
    target_playthrough_seconds: RawNumber = 180
    decision_points_per_path: RawNumber = 2
    ending_count: RawNumber = 2
    node_budget: RawNumber = 8
    max_out_degree: RawNumber = 3
    desired_join_count: RawNumber = 1
    shots_per_scene_min: RawNumber = 1
    shots_per_scene_max: RawNumber = 4
    shot_count_policy: Literal["strict", "advisory"] = "advisory"

    def confirmed(self) -> ProjectBrief:
        """Explicit Apply alone supplies the documented optional-title fallback."""
        payload = self.model_dump(mode="json", by_alias=True)
        payload["title"] = self.title.strip() or "未命名故事"
        return ProjectBrief.model_validate(payload)


def working_project_title(confirmed_title: str | None, working_title: str | None = None) -> str:
    """None means no working row; an empty working title overrides canon."""
    title = confirmed_title if working_title is None else working_title
    return (title or "").strip() or "未命名项目"
