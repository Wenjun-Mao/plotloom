"""Attribution for actions performed by a registered Codex task."""

from typing import Literal

from pydantic import Field

from plotloom.domain_base import CamelModel


class CodexTaskAttribution(CamelModel):
    """Identifies the task that operated a selection without claiming review."""

    kind: Literal["codex_task"] = "codex_task"
    task_id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
