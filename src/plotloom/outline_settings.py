"""Author-owned Brief settings consumed by a frozen outline candidate."""

from typing import Any

from .creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from .domain import ProjectBrief


OUTLINE_SETTINGS_FILENAME = "outline-settings.json"


def outline_settings(brief: ProjectBrief) -> dict[str, Any]:
    """Source owns story text/title; Brief supplies the remaining saved settings."""

    return brief.model_dump(mode="json", by_alias=True, exclude={"title", "synopsis"})


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
