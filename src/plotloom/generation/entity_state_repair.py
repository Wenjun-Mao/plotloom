"""Derive and revalidate entity-state repairs against the frozen Bible vocabulary."""

from __future__ import annotations

from typing import Any

from pydantic import (
    ValidationError,
)

from plotloom.canonical_schema import EntityType, StoryBibleV2
from plotloom.stage_contracts import StageName
from .continuity_repair_contracts import (
    ContinuityEntityStateRepairFact,
    ContinuityStateEndpoint,
)
from .contracts import ValidationIssue
from .repair_facts import SemanticRepairFact
from .scene_response_contracts import (
    SceneBeatsFragmentOutput,
)
from .storyboard_repair_contracts import (
    RequiredEntityStateRepairFact,
)
from .storyboard_response_contracts import (
    StoryboardFragmentOutput,
)


def storyboard_required_entity_state_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    bible: StoryBibleV2,
) -> tuple[RequiredEntityStateRepairFact, ...]:
    """Project exact frozen Story Bible state choices into correction facts.

    Facts are emitted only when the whole model response is schema-valid and
    the persisted semantic issue points to the same parsed requirement.  This
    keeps malformed indexes, unknown entities, and empty author vocabularies
    fail-closed instead of turning them into guessed repair authority.
    """

    relevant_issues = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.invalid_required_entity_state"
    )
    if not relevant_issues:
        return ()
    try:
        output = StoryboardFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()
    entities_by_type = {
        EntityType.CHARACTER: {item.id: item for item in bible.characters},
        EntityType.LOCATION: {item.id: item for item in bible.locations},
        EntityType.PROP: {item.id: item for item in bible.props},
    }
    facts: list[RequiredEntityStateRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 5
            or path[0] != "shots"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "requiredEntityStates"
            or not isinstance(path[3], int)
            or isinstance(path[3], bool)
            or path[3] < 0
            or path[4] != "state"
        ):
            continue
        shot_index = path[1]
        state_index = path[3]
        if shot_index >= len(output.shots):
            continue
        requirements = output.shots[shot_index].required_entity_states
        if state_index >= len(requirements):
            continue
        requirement = requirements[state_index]
        entity = entities_by_type[requirement.entity_type].get(requirement.entity_id)
        if entity is None:
            continue
        allowed_states = tuple(entity.allowed_states)
        if not allowed_states or requirement.state in allowed_states:
            continue
        facts.append(
            RequiredEntityStateRepairFact(
                code=issue.code,
                path=path,
                entity_type=requirement.entity_type,
                entity_id=requirement.entity_id,
                allowed_states=allowed_states,
            )
        )
    return tuple(facts)


def continuity_entity_state_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2,
) -> tuple[ContinuityEntityStateRepairFact, ...]:
    """Rebind known invalid continuity states to frozen Bible vocabulary."""

    relevant = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.invalid_continuity_entity_state"
    )
    if not relevant or stage not in {StageName.SCENE_BEATS, StageName.STORYBOARD}:
        return ()
    try:
        output: SceneBeatsFragmentOutput | StoryboardFragmentOutput
        output = (
            SceneBeatsFragmentOutput.model_validate(value, by_alias=True, by_name=False)
            if stage == StageName.SCENE_BEATS
            else StoryboardFragmentOutput.model_validate(
                value, by_alias=True, by_name=False
            )
        )
    except ValidationError:
        return ()
    entities_by_type = {
        EntityType.CHARACTER: {item.id: item for item in bible.characters},
        EntityType.LOCATION: {item.id: item for item in bible.locations},
        EntityType.PROP: {item.id: item for item in bible.props},
    }
    collections: dict[str, tuple[str, str, list[Any]]]
    if isinstance(output, SceneBeatsFragmentOutput):
        collections = {
            "scenes": ("scene", "local_scene_id", list(output.scenes)),
            "beats": ("beat", "local_beat_id", list(output.beats)),
        }
    else:
        collections = {"shots": ("shot", "local_shot_id", list(output.shots))}
    facts: list[ContinuityEntityStateRepairFact] = []
    for issue in relevant:
        path = issue.path
        if (
            len(path) != 6
            or path[0] not in collections
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] not in {"entryState", "exitState"}
            or path[3] != "entityStates"
            or not isinstance(path[4], int)
            or isinstance(path[4], bool)
            or path[4] < 0
            or path[5] != "state"
        ):
            continue
        kind, local_id_field, items = collections[path[0]]
        item_index, state_index = path[1], path[4]
        if item_index >= len(items):
            continue
        item = items[item_index]
        continuity = item.entry_state if path[2] == "entryState" else item.exit_state
        if state_index >= len(continuity.entity_states):
            continue
        assignment = continuity.entity_states[state_index]
        entity = entities_by_type[assignment.entity_type].get(assignment.entity_id)
        if (
            entity is None
            or not entity.allowed_states
            or assignment.state in entity.allowed_states
        ):
            continue
        facts.append(
            ContinuityEntityStateRepairFact(
                code=issue.code,
                path=path,
                target=ContinuityStateEndpoint(
                    kind=kind,
                    id=getattr(item, local_id_field),
                    id_scope="response_local",
                    state="entry" if path[2] == "entryState" else "exit",
                ),
                entity_state_index=state_index,
                entity_type=assignment.entity_type,
                entity_id=assignment.entity_id,
                allowed_states=tuple(entity.allowed_states),
            )
        )
    return tuple(facts)


def assert_continuity_entity_state_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
    *,
    stage: StageName,
    bible: StoryBibleV2 | None,
) -> None:
    """Prove a vocabulary fact still belongs to this rejected response."""

    if not isinstance(fact, ContinuityEntityStateRepairFact):
        return
    if bible is None:
        raise ValueError("continuity entity-state repair requires a frozen story bible")
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = continuity_entity_state_repair_facts(
        source_value, (source_issue,), stage=stage, bible=bible
    )
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError(
            "continuity entity-state repair fact does not match the rejected response and frozen story bible"
        )
