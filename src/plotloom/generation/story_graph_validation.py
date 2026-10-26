"""Validate model content against frozen graph topology at the correction boundary."""

from __future__ import annotations

from typing import Any

from pydantic import (
    ValidationError,
)

from ..domain import (
    ProjectBrief,
    StageName,
    StoryBibleV2,
    StoryGraphV2,
)
from ..json_value_contract import (
    finite_canonical_json,
)
from ..validation import DomainValidationError, validate_story_graph
from .contracts import ValidationIssue, ValidationReport
from .json_schema import (
    _presence_issues,
)
from plotloom.generation.story_graph_content_contracts import STORY_GRAPH_CONTENT_FILL_SCHEMA_ID, StoryGraphContentFill, story_graph_content_fill_schema
from plotloom.generation.story_graph_content_fill import StoryGraphContentBindingError, bind_story_graph_content_fill, story_graph_content_fill_join_diagnostic_issues
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology
from .validation import (
    SemanticValidationContext,
    ValidationAdapter,
)


class StoryGraphContentFillValidationAdapter(ValidationAdapter[StoryGraphV2]):
    """Validate model prose against a frozen topology before canonicalizing it."""

    schema_id = STORY_GRAPH_CONTENT_FILL_SCHEMA_ID

    def __init__(
        self,
        *,
        topology: StoryGraphTopology,
        brief: ProjectBrief,
        bible: StoryBibleV2 | None = None,
    ) -> None:
        self.topology = topology
        self.brief = brief
        self.bible = bible

    def json_schema(self) -> dict[str, Any]:
        return story_graph_content_fill_schema(self.topology)

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        if context.stage != StageName.STORY_GRAPH.value:
            raise ValueError(
                "Story Graph content fill received a different stage context"
            )
        presence_issues = _presence_issues(value, self.json_schema())
        if presence_issues:
            return ValidationReport(accepted=False, issues=presence_issues)
        try:
            fill = StoryGraphContentFill.model_validate(
                value, by_alias=True, by_name=False
            )
        except ValidationError as exc:
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code=f"schema.{error['type']}",
                        message=error["msg"],
                        path=tuple(error.get("loc") or ()),
                    )
                    for error in exc.errors(include_url=False, include_context=False)
                ),
            )
        try:
            if self.bible is None and any(
                item.entity_state_effects for item in fill.edges
            ):
                return ValidationReport(
                    accepted=False,
                    issues=(
                        ValidationIssue(
                            code="context.story_bible_required",
                            message="typed graph entity-state effects require a sealed story bible",
                            path=("edges",),
                        ),
                    ),
                )
            graph = bind_story_graph_content_fill(
                self.topology, fill, brief=self.brief, bible=self.bible
            )
        except StoryGraphContentBindingError as exc:
            binding_issues = tuple(
                ValidationIssue(
                    code=issue["code"],
                    message=issue["message"],
                    path=tuple(part for part in issue["path"].split(".") if part),
                )
                for issue in exc.issues
            )
            diagnostic_issues: tuple[ValidationIssue, ...] = ()
            if any(
                issue.code == "semantic.join_allowed_differences_must_be_required"
                for issue in binding_issues
            ):
                # Normal binding cannot construct a canonical join when an
                # allowed key is absent from requiredStateKeys.  Its
                # normalized diagnostic view reuses the join-state compiler
                # to reveal independent pre-existing join defects without
                # accepting or changing the rejected response.
                diagnostic_issues = tuple(
                    ValidationIssue(
                        code=issue["code"],
                        message=issue["message"],
                        path=tuple(part for part in issue["path"].split(".") if part),
                    )
                    for issue in story_graph_content_fill_join_diagnostic_issues(
                        self.topology,
                        fill,
                    )
                )
            return ValidationReport(
                accepted=False,
                issues=(*binding_issues, *diagnostic_issues),
            )
        finite_json_issues: list[ValidationIssue] = []
        for edge in graph.edges:
            for state_key, state_value in edge.state_effects.items():
                try:
                    finite_canonical_json(state_value)
                except (TypeError, ValueError):
                    # ``model_dump(mode=\"json\")`` would coerce NaN to null,
                    # which erases the rejection before a correction fact can
                    # bind it. Validate the trusted binder's still-native
                    # value first and preserve the edge-local evidence.
                    finite_json_issues.append(
                        ValidationIssue(
                            code="semantic.state_effect_not_json",
                            message="story edge state effects must be finite canonical JSON values",
                            path=("edges", edge.id, "stateEffects", state_key),
                        )
                    )
        if finite_json_issues:
            return ValidationReport(accepted=False, issues=tuple(finite_json_issues))
        # The topology binder remains the deterministic graph authority.  Its
        # result is projected into the explicit V2 authoring schema only after
        # that topology contract has been checked.
        try:
            canonical_graph = StoryGraphV2.model_validate(
                graph.model_dump(mode="json", by_alias=True)
            )
        except ValidationError as exc:
            # The binder already verifies the complete V2 projection.  Keep a
            # defensive conversion here so future V2 additions cannot turn a
            # model-content mistake into ``validation.internal_error``.
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code="semantic.v2_projection_invalid",
                        message=error["msg"],
                        path=tuple(error.get("loc") or ()),
                    )
                    for error in exc.errors(include_url=False, include_context=False)
                ),
            )
        try:
            # The primary adapter is the first boundary at which a response
            # can enter a correction loop.  Run the same strict graph
            # semantics used by canonical installation here; otherwise an
            # ordinary non-finite edge value can bypass fact projection until
            # a later stage, where no exact graph correction exists.
            validate_story_graph(canonical_graph, self.brief, bible=self.bible)
        except DomainValidationError as exc:
            return ValidationReport(accepted=False, issues=exc.issues)
        return ValidationReport(accepted=True, value=canonical_graph)
