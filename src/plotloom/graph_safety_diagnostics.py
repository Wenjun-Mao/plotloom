"""Checked structural facts, shared by admission and public refusal diagnostics."""
from dataclasses import asdict, dataclass, field
from typing import Any

from .exceptions import InvalidTransitionError, SamePersonReviewRequiredError
from .review_context_diagnostics import ReviewContextError


@dataclass(frozen=True)
class GraphSafetyDiagnostic:
    code: str
    identity: str
    severity: int
    facts: dict[str, Any] = field(default_factory=dict)

    def public(self, previous_severity: int) -> dict[str, Any]:
        return asdict(self) | {"previousSeverity": previous_severity}


class GraphEditSafetyError(InvalidTransitionError):
    code = "graph_edit_unsafe"

    def __init__(self, diagnostics: list[dict[str, Any]]) -> None:
        self.diagnostics = diagnostics
        super().__init__("结构修改不能新增或加重错误：" + "；".join(item["identity"] for item in diagnostics))


def transition_error_content(error: InvalidTransitionError) -> dict[str, Any]:
    if isinstance(error, SamePersonReviewRequiredError):
        return {
            "code": error.code,
            "message": str(error),
            "shotId": error.shot_id,
            "bindingId": error.binding_id,
            "technicalMessage": error.technical_message,
        }
    if isinstance(error, ReviewContextError):
        return {"code": error.code, "message": str(error), "diagnostic": error.diagnostic.model_dump(mode="json", by_alias=True)}
    if isinstance(error, GraphEditSafetyError):
        return {"code": error.code, "message": str(error), "diagnostics": error.diagnostics}
    return {"code": "invalid_transition", "message": str(error)}
