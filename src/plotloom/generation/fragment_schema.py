"""Project frozen selector and foreign-key authority into model response schemas."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from plotloom.brief_contracts import ProjectBrief
from plotloom.stage_contracts import StageName
from plotloom.canonical_schema import StoryBibleV2
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
)
from .frozen_join_requirements import (
    _continuity_requirements,
)
from plotloom.generation.planning_contracts import GenerationWorkUnit
from .scene_beats_edge_entry import (
    edge_entry_state_requirements,
    require_first_scene_entity_state_values,
)
from .storyboard_timing_repair import (
    StoryboardTimingGuidance,
)
from .work_unit_contracts import (
    WorkUnitContractError,
)


def _bind_fragment_foreign_keys(
    schema: dict[str, Any],
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
    storyboard_timing_guidance: StoryboardTimingGuidance | None,
) -> None:
    """Expose trusted selector/foreign-key constraints in the model schema.

    These constraints reduce avoidable model transcription errors, but do not
    replace semantic validation. Generated scene, beat, and shot handles are
    local to one response; the trusted binder derives canonical IDs only after
    this validation succeeds.
    """

    definitions = schema["$defs"]
    character_ids = sorted(item.id for item in bible.characters)
    location_ids = sorted(item.id for item in bible.locations)
    prop_ids = sorted(item.id for item in bible.props)

    if work_unit.stage == StageName.SCENE_BEATS:
        if dialogue_capacity_guidance is None:
            raise WorkUnitContractError(
                "Scene Beats schema binding requires frozen dialogue capacity guidance"
            )
        schema["properties"]["scenes"]["maxItems"] = (
            dialogue_capacity_guidance.max_scenes
        )
        schema["properties"]["dialogueCues"]["maxItems"] = (
            0
            if dialogue_capacity_guidance.schema_max_text_codepoints == 0
            else dialogue_capacity_guidance.max_dialogue_cues
        )
        scene_properties = definitions["DramaticSceneContent"]["properties"]
        _set_nullable_string_enum(scene_properties["locationId"], location_ids)
        _set_array_string_enum(scene_properties["characterIds"], character_ids)
        cue_properties = definitions["DialogueCueContent"]["properties"]
        _set_nullable_string_enum(cue_properties["speakerId"], character_ids)
        if dialogue_capacity_guidance.authoring_language is not None:
            _set_string_const(
                cue_properties["language"],
                dialogue_capacity_guidance.authoring_language,
            )
            assert dialogue_capacity_guidance.schema_max_text_codepoints is not None
            cue_properties["text"]["maxLength"] = (
                dialogue_capacity_guidance.schema_max_text_codepoints
            )
        continuity = _continuity_requirements(scoped_context)
        _require_state_fact_values(
            scene_properties["entryState"],
            continuity["requiredEntryFacts"],
        )
        require_first_scene_entity_state_values(
            definitions["DramaticSceneContent"],
            edge_entry_state_requirements(scoped_context)["requiredEntityStates"],
        )
        return

    if work_unit.stage != StageName.STORYBOARD:
        raise WorkUnitContractError("foreign-key binding only supports sharded stages")
    if dialogue_capacity_guidance is not None:
        raise WorkUnitContractError(
            "dialogue capacity guidance only belongs to Scene Beats"
        )
    if storyboard_timing_guidance is None:
        raise WorkUnitContractError(
            "Storyboard schema binding requires frozen timing guidance"
        )
    schema["properties"]["shots"].update(
        {
            "minItems": storyboard_timing_guidance.min_shots,
            "maxItems": storyboard_timing_guidance.max_shots,
        }
    )
    shot_properties = definitions["ShotContent"]["properties"]
    _set_nullable_string_enum(shot_properties["locationId"], location_ids)
    _set_array_string_enum(shot_properties["characterIds"], character_ids)
    _set_array_string_enum(shot_properties["propIds"], prop_ids)
    cue_ids = sorted(
        str(item["id"])
        for item in scoped_context.get("dialogue_cues", [])
        if isinstance(item, Mapping) and item.get("id")
    )
    _set_array_string_enum(shot_properties["cueIds"], cue_ids)
    beat_ids = sorted(
        str(item["id"])
        for item in scoped_context.get("beats", [])
        if isinstance(item, Mapping) and item.get("id")
    )
    _set_string_enum(
        definitions["SupportingBeatLinkContent"]["properties"]["beatId"], beat_ids
    )
    primary_coverage = schema["properties"]["primaryShotLocalIdByBeat"]
    primary_coverage.clear()
    primary_coverage.update(
        {
            "type": "object",
            "properties": {
                beat_id: {"type": "string", "minLength": 1} for beat_id in beat_ids
            },
            "required": beat_ids,
            "additionalProperties": False,
            "minProperties": len(beat_ids),
            "maxProperties": len(beat_ids),
        }
    )


def _set_string_const(schema_node: dict[str, Any], value: str) -> None:
    schema_node.clear()
    schema_node.update({"type": "string", "const": value})


def _set_string_enum(schema_node: dict[str, Any], values: list[str]) -> None:
    schema_node.clear()
    schema_node.update({"type": "string", "enum": values})


def _set_nullable_string_enum(schema_node: dict[str, Any], values: list[str]) -> None:
    description = schema_node.get("description")
    schema_node.clear()
    if values:
        schema_node.update(
            {
                "anyOf": [
                    {"type": "string", "enum": values},
                    {"type": "null"},
                ]
            }
        )
    else:
        schema_node.update({"type": "null"})
    if isinstance(description, str) and description:
        schema_node["description"] = description


def _set_array_string_enum(schema_node: dict[str, Any], values: list[str]) -> None:
    schema_node["items"] = {"type": "string", "enum": values}
    if not values:
        schema_node["maxItems"] = 0


def _require_state_fact_values(
    schema_node: dict[str, Any],
    facts: Mapping[str, Any],
) -> None:
    if not facts:
        return
    keys = sorted(facts)
    referenced_state = deepcopy(schema_node)
    schema_node.clear()
    schema_node.update(
        {
            "allOf": [referenced_state],
            "type": "object",
            "required": ["facts"],
            "properties": {
                "facts": {
                    "type": "object",
                    "required": keys,
                    "properties": {
                        key: {"const": deepcopy(facts[key])} for key in keys
                    },
                }
            },
        }
    )
