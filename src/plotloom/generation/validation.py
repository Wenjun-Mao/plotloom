"""Schema and semantic validation through a replaceable adapter boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, Mapping, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ValidationError

from ..domain import (
    ProjectBrief,
    StageName,
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryGraphV2,
    stage_payload_model,
)
from .contracts import ValidationIssue, ValidationReport, ValidationSeverity
from .exceptions import ResponseValidationError
from .json_schema import explicit_presence_json_schema, inline_local_json_references


T = TypeVar("T")
ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class SemanticValidationContext:
    stage: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class SemanticValidator(Protocol[T]):
    def __call__(
        self,
        value: T,
        context: SemanticValidationContext,
    ) -> Iterable[ValidationIssue]:
        ...


@runtime_checkable
class ValidationAdapter(Protocol[T]):
    """Boundary for Pydantic today and other schema engines later."""

    schema_id: str

    def json_schema(self) -> dict[str, Any]:
        ...

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        ...


class PydanticValidationAdapter(Generic[ModelT]):
    def __init__(
        self,
        model_type: type[ModelT],
        *,
        schema_id: str,
        semantic_validators: Iterable[SemanticValidator[ModelT]] = (),
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> None:
        self.model_type = model_type
        self.schema_id = schema_id
        self.semantic_validators = tuple(semantic_validators)
        self.by_alias = by_alias
        self.by_name = by_name

    def json_schema(self) -> dict[str, Any]:
        return self.model_type.model_json_schema()

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        try:
            parsed = self.model_type.model_validate(
                value,
                by_alias=self.by_alias,
                by_name=self.by_name,
            )
        except ValidationError as exc:
            issues = tuple(
                ValidationIssue(
                    code=f"schema.{error['type']}",
                    message=error["msg"],
                    path=tuple(error.get("loc") or ()),
                )
                for error in exc.errors(include_url=False, include_context=False)
            )
            return ValidationReport(accepted=False, issues=issues)

        semantic_issues: list[ValidationIssue] = []
        for validator in self.semantic_validators:
            semantic_issues.extend(validator(parsed, context))
        accepted = not any(
            issue.severity == ValidationSeverity.ERROR for issue in semantic_issues
        )
        return ValidationReport(
            accepted=accepted,
            value=parsed if accepted else None,
            issues=tuple(semantic_issues),
        )


class CanonicalStageValidationAdapter(PydanticValidationAdapter[BaseModel]):
    """Validate generated stages with the extraction-owned canonical models.

    Pydantic enforces the serial shape first. The canonical domain validators
    then enforce graph, coverage, continuity-reference, and budget contracts.
    No generation-specific copy of a stage model exists in this package.
    """

    def __init__(
        self,
        stage: StageName | str,
        *,
        brief: ProjectBrief,
        bible: StoryBibleV2 | None = None,
        graph: StoryGraphV2 | None = None,
        scene_beats: SceneBeatPlanV2 | None = None,
    ) -> None:
        self.stage = StageName(stage)
        self.brief = brief
        self.bible = bible
        self.graph = graph
        self.scene_beats = scene_beats
        self._assert_dependencies()
        super().__init__(
            stage_payload_model(self.stage, schema_version=2),
            schema_id=("story_graph.v4" if self.stage == StageName.STORY_GRAPH else f"{self.stage.value}.v3"),
            by_alias=True,
            by_name=False,
        )

    def json_schema(self) -> dict[str, Any]:
        """Expose a presence-strict canonical camelCase generation schema.

        Domain defaults remain useful for hand-authored edits. Generated output
        crosses a different trust boundary: every declared field must be
        explicit (nullable fields may be null), so omitted model output cannot
        become canonical through silent default insertion.
        """

        schema = explicit_presence_json_schema(
            self.model_type.model_json_schema(by_alias=True)
        )
        return inline_local_json_references(schema)

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        if context.stage != self.stage.value:
            raise ValueError(
                f"Validation context stage {context.stage!r} does not match "
                f"adapter stage {self.stage.value!r}"
            )
        presence_issues = self._generated_field_presence_issues(value)
        if presence_issues:
            return ValidationReport(accepted=False, issues=presence_issues)

        schema_report = super().validate(value, context=context)
        if not schema_report.accepted:
            return schema_report

        semantic_issues = _v2_canonical_semantic_issues(self.stage, schema_report.value)
        if semantic_issues:
            return ValidationReport(accepted=False, issues=semantic_issues)
        return schema_report

    def _assert_dependencies(self) -> None:
        if self.stage == StageName.SCENE_BEATS and (
            self.bible is None or self.graph is None
        ):
            raise ValueError("scene_beats validation requires bible and graph")
        if self.stage == StageName.STORYBOARD and (
            self.bible is None or self.scene_beats is None
        ):
            raise ValueError("storyboard validation requires bible and scene_beats")

    def _generated_field_presence_issues(
        self,
        value: Any,
    ) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        schema = self.json_schema()
        _collect_presence_issues(value, schema, schema, (), issues)
        return tuple(issues)


def _domain_path(path: str) -> tuple[str | int, ...]:
    if not path:
        return ()
    return tuple(int(part) if part.isdigit() else part for part in path.split("."))


def _v2_canonical_semantic_issues(
    stage: StageName,
    value: BaseModel,
) -> tuple[ValidationIssue, ...]:
    """Keep V2 whole-stage validation independent of V1 compatibility rules."""

    if stage != StageName.STORY_GRAPH:
        return ()
    assert isinstance(value, StoryGraphV2)
    node_ids = [node.id for node in value.nodes]
    issues: list[ValidationIssue] = []
    if value.start_node_id not in set(node_ids):
        issues.append(ValidationIssue(code="semantic.missing_start_node", message="startNodeId must identify a graph node", path=("startNodeId",)))
    if len(node_ids) != len(set(node_ids)):
        issues.append(ValidationIssue(code="semantic.duplicate_node_id", message="Story Graph node IDs must be unique", path=("nodes",)))
    return tuple(issues)


def _resolve_schema(schema_node: Any, root: Mapping[str, Any]) -> Any:
    if not isinstance(schema_node, Mapping):
        return schema_node
    reference = schema_node.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return schema_node
    resolved: Any = root
    for segment in reference[2:].split("/"):
        if not isinstance(resolved, Mapping):
            return schema_node
        resolved = resolved.get(segment.replace("~1", "/").replace("~0", "~"))
    return resolved


def _schema_matches_value(schema_node: Any, value: Any, root: Mapping[str, Any]) -> bool:
    resolved = _resolve_schema(schema_node, root)
    if not isinstance(resolved, Mapping):
        return True
    kind = resolved.get("type")
    return {
        "null": value is None,
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }.get(str(kind), True)


def _collect_presence_issues(
    value: Any,
    schema_node: Any,
    root: Mapping[str, Any],
    path: tuple[str | int, ...],
    issues: list[ValidationIssue],
) -> None:
    resolved = _resolve_schema(schema_node, root)
    if not isinstance(resolved, Mapping):
        return
    variants = resolved.get("anyOf") or resolved.get("oneOf")
    if isinstance(variants, list):
        selected = next(
            (variant for variant in variants if _schema_matches_value(variant, value, root)),
            None,
        )
        if selected is not None:
            _collect_presence_issues(value, selected, root, path, issues)
        return

    properties = resolved.get("properties")
    if isinstance(properties, Mapping) and isinstance(value, Mapping):
        for field_name, child_schema in properties.items():
            if field_name not in value:
                issues.append(
                    ValidationIssue(
                        code="schema.missing",
                        message="Field required for generated canonical output",
                        path=(*path, str(field_name)),
                    )
                )
            else:
                _collect_presence_issues(
                    value[field_name],
                    child_schema,
                    root,
                    (*path, str(field_name)),
                    issues,
                )
        return

    items = resolved.get("items")
    if items is not None and isinstance(value, list):
        for index, item in enumerate(value):
            _collect_presence_issues(item, items, root, (*path, index), issues)


def validate_or_raise(
    adapter: ValidationAdapter[T],
    value: Any,
    *,
    context: SemanticValidationContext,
) -> T:
    report = adapter.validate(value, context=context)
    if not report.accepted:
        raise ResponseValidationError(
            f"Response failed validation for schema {adapter.schema_id!r}",
            issues=report.issues,
        )
    return report.value
