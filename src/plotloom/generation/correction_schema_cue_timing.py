"""CueTimingCorrectionSchema authority and projection."""

from __future__ import annotations

from typing import Any

from .correction_schema_contracts import CorrectionResponseSchemaError
from .correction_schema_shapes import (
    _collection_item_schema,
    _collection_schema,
    _replace_collection_cardinality,
    _schema_properties,
    _selected_item_branch,
    _set_property_const,
    _set_string_enum,
)
from .dialogue_repair_contracts import (
    CueOrderRepairFact,
)
from .repair_facts import (
    SemanticRepairFact,
)
from .storyboard_timing_repair import (
    StoryboardTimingRepairPlanFact,
)


class CueTimingCorrectionSchema:
    """Collect exact family authority, then project it deterministically."""

    def __init__(self) -> None:
        self.cue_order_fact: CueOrderRepairFact | None = None
        self.timing_plan_fact: StoryboardTimingRepairPlanFact | None = None
        self.applied_codes: set[str] = set()

    def collect(self, fact: SemanticRepairFact) -> bool:
        if isinstance(fact, CueOrderRepairFact):
            if self.cue_order_fact is not None and self.cue_order_fact != fact:
                raise CorrectionResponseSchemaError(
                    "conflicting cue-order repair facts target dialogueCues"
                )
            self.cue_order_fact = fact
            self.applied_codes.add(fact.code)
            return True

        if isinstance(fact, StoryboardTimingRepairPlanFact):
            if (
                self.timing_plan_fact is not None
                and self.timing_plan_fact.plan != fact.plan
            ):
                raise CorrectionResponseSchemaError(
                    "conflicting Storyboard timing repair facts carry different plans"
                )
            self.timing_plan_fact = fact
            self.applied_codes.add(fact.code)

            return True
        return False

    def apply(self, schema: dict[str, Any]) -> None:
        if self.cue_order_fact is not None:
            collection_schema = _collection_schema(schema, "dialogueCues")
            assignment_count = len(self.cue_order_fact.assignments)
            existing_min = collection_schema.get("minItems")
            existing_max = collection_schema.get("maxItems")
            if isinstance(existing_min, int) and existing_min > assignment_count:
                raise CorrectionResponseSchemaError(
                    "cue-order repair count conflicts with base minItems"
                )
            if isinstance(existing_max, int) and existing_max < assignment_count:
                raise CorrectionResponseSchemaError(
                    "cue-order repair count conflicts with base maxItems"
                )
            collection_schema["minItems"] = assignment_count
            collection_schema["maxItems"] = assignment_count

        if self.timing_plan_fact is not None:
            plan = self.timing_plan_fact.plan
            collection_schema = _collection_schema(schema, "shots")
            target_count = len(plan.target_shots)
            _replace_collection_cardinality(
                collection_schema,
                target_count,
                label="Storyboard timing target shot",
            )
            item_schema = _collection_item_schema(schema, "shots")
            item_properties = _schema_properties(
                item_schema,
                label="shots item schema",
            )
            identity_schema = item_properties.get("localShotId")
            if not isinstance(identity_schema, dict):
                raise CorrectionResponseSchemaError(
                    "base response schema has no localShotId field contract"
                )
            target_ids = sorted(shot.local_shot_id for shot in plan.target_shots)
            _set_string_enum(
                identity_schema,
                target_ids,
                label="Storyboard timing target shot IDs",
            )
            branches = item_schema.setdefault("allOf", [])
            if not isinstance(branches, list):
                raise CorrectionResponseSchemaError(
                    "shots item schema has a non-list allOf"
                )
            for shot in sorted(plan.target_shots, key=lambda item: item.local_shot_id):
                branches.append(
                    _selected_item_branch(
                        "localShotId",
                        shot.local_shot_id,
                        {
                            "order": {"const": shot.target_order},
                            "durationUnits": {"const": shot.target_duration_units},
                            "cueIds": {"const": list(shot.target_cue_ids)},
                        },
                    )
                )

            root_properties = _schema_properties(schema, label="response schema")
            _set_property_const(
                root_properties,
                "primaryShotLocalIdByBeat",
                {
                    link.beat_id: link.shot_local_id
                    for link in plan.target_primary_links
                },
            )
            _set_property_const(
                root_properties,
                "supportingBeatLinks",
                [
                    {
                        "shotLocalId": link.shot_local_id,
                        "beatId": link.beat_id,
                        "coverageWeight": link.coverage_weight,
                    }
                    for link in plan.target_supporting_links
                ],
            )
