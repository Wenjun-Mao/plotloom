"""Author-owned Brief settings consumed by a frozen outline candidate."""

from typing import Any

from .creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from .domain import ProjectBrief


OUTLINE_SETTINGS_FILENAME = "outline-settings.json"


def outline_settings(brief: ProjectBrief) -> dict[str, Any]:
    """Source owns story text/title; Brief supplies the remaining saved settings."""

    return {key: value for key, value in brief.generation_input().items() if key not in {"title", "synopsis"}}


def assert_outline_settings_current(request: CreativeHandoffRequest, brief: ProjectBrief) -> None:
    frozen = request.input_artifacts.get(OUTLINE_SETTINGS_FILENAME)
    if frozen is None:
        raise CreativeHandoffError(
            "outline_settings_missing", "outline task must include the saved project settings",
        )
    if frozen != outline_settings(brief):
        raise CreativeHandoffError(
            "outline_settings_stale",
            "project settings changed; cancel the old task and prepare a current outline candidate",
        )
    from .source_structures import planned_structure
    topology = planned_structure(request.project_id, brief).model_dump(mode="json", by_alias=True)
    if request.input_artifacts.get("story-topology.json") != topology:
        raise CreativeHandoffError(
            "outline_topology_stale", "大纲任务缺少当前简报的完整结构，请取消旧任务后重新准备。",
        )
