"""Typed currentness evidence for Cast/Art; never part of a frozen request."""
from __future__ import annotations

from typing import Any, Literal

from .domain import CamelModel
from .exceptions import InvalidTransitionError


ReviewContextCode = Literal[
    "source_context_not_ready", "installed_graph_not_current",
    "installed_graph_context_mismatch", "accepted_cast_not_current",
    "binding_revision_changed", "binding_content_changed",
    "section_context_changed", "art_render_contract_changed", "cast_render_contract_changed",
]
ReviewContextField = Literal[
    "source_revision", "outline_revision", "section_map_revision", "graph_revision",
    "cast_revision", "source_content_hash", "outline_content_hash",
    "section_map_content_hash", "graph_content_hash", "cast_content_hash",
]


class ReviewContextDiagnostic(CamelModel):
    code: ReviewContextCode
    owner: Literal["source", "characters", "art"]
    technical_message: str
    field: ReviewContextField | None = None


class ReviewContextError(InvalidTransitionError):
    code = "review_context_not_current"

    def __init__(self, diagnostic: ReviewContextDiagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic.technical_message)


def binding_diagnostics(
    current: Any, frozen: Any, fields: tuple[tuple[ReviewContextField, str], ...]
) -> list[ReviewContextDiagnostic]:
    """Preserve the exact comparison order and technical text of each owner."""
    reasons = [
        ReviewContextDiagnostic(
            code="binding_revision_changed" if field.endswith("revision") else "binding_content_changed",
            owner="characters" if field.startswith("cast_") else "source",
            field=field,
            technical_message=f"{label} {'revision' if field.endswith('revision') else 'content'} changed",
        )
        for field, label in fields
        if getattr(current, field) != getattr(frozen, field)
    ]
    return reasons
