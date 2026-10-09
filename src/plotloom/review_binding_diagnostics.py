"""Field-owned comparisons for Script and Storyboard review projections."""
from __future__ import annotations

from typing import Any

from .review_context_diagnostics import ReviewContextDiagnostic, ReviewContextField


# Explicit membership makes a new binding field require a diagnostic decision.
# These comparisons describe currentness; they do not repair or translate data.
FIELD_OWNERS = {
    "source_revision": "source", "source_content_hash": "source",
    "outline_revision": "source", "outline_content_hash": "source",
    "section_map_revision": "source", "section_map_content_hash": "source",
    "graph_revision": "source", "graph_content_hash": "source",
    "cast_revision": "characters", "cast_content_hash": "characters",
    "art_revision": "art", "art_content_hash": "art",
    "script_revision": "script", "script_content_hash": "script",
    "target_playthrough_seconds": "brief", "route_budget_hash": "brief",
    "section_bindings": "source", "complete_route_section_ids": "source",
    "route_only_section_ids": "source", "section_ids": "source",
    "render_contract": "art",
    "review_min_cut_seconds": "storyboard-review",
    "review_max_cut_seconds": "storyboard-review",
    "review_max_segment_seconds": "storyboard-review",
}


def review_binding_diagnostics(
    current: Any, frozen: Any, fields: tuple[ReviewContextField, ...],
) -> list[ReviewContextDiagnostic]:
    diagnostics = []
    for field in fields:
        owner = FIELD_OWNERS[field]
        if getattr(current, field) == getattr(frozen, field):
            continue
        code = (
            "binding_revision_changed" if field.endswith("_revision") else
            "binding_content_changed" if field.endswith("_content_hash") else
            "binding_value_changed"
        )
        label = field.replace("_content_hash", " content").replace("_revision", " revision").replace("_", " ")
        diagnostics.append(ReviewContextDiagnostic(
            code=code, owner=owner, field=field, technical_message=f"{label} changed",
        ))
    return diagnostics
