"""Default source-shaped story map for generic creative-stage fixtures."""
from plotloom.source_outline_contracts import (
    BranchOutcome,
    SectionChoice,
    SectionMap,
    StorySection,
)
from plotloom.source_structures import planned_structure


def default_story_mapping(store):
    return SectionMap(
        seed_topology=planned_structure(
            store.manifest.project_id, store.project().brief
        ),
        topology_origin="author",
        topology={
            "startNodeId": "opening",
            "nodes": [
                {"id": "opening", "kind": "start"},
                {"id": "choose", "kind": "decision"},
                {"id": "ending-a", "kind": "ending"},
                {"id": "ending-b", "kind": "ending"},
            ],
            "edges": [
                {
                    "id": key,
                    "sourceNodeId": source_id,
                    "targetNodeId": target,
                    "kind": kind,
                    "stateEffects": {},
                    "entityStateEffects": [],
                }
                for key, source_id, target, kind in [
                    ("to-choice", "opening", "choose", "continuation"),
                    ("beacon", "choose", "ending-a", "choice"),
                    ("dock", "choose", "ending-b", "choice"),
                ]
            ],
            "joins": [],
        },
        sections=[
            StorySection(
                section_id="opening",
                title="Opening",
                summary="Lin chooses.",
                footage_mode="footage",
            ),
            StorySection(
                section_id="choose",
                title="Choose",
                summary="Lin chooses a route.",
                footage_mode="route_only",
            ),
            StorySection(
                section_id="ending-a",
                title="Beacon",
                summary="Beacon.",
                ending=True,
                footage_mode="footage",
            ),
            StorySection(
                section_id="ending-b",
                title="Dock",
                summary="Dock.",
                ending=True,
                footage_mode="footage",
            ),
        ],
        choices=[
            SectionChoice(
                choice_id="choose",
                section_id="choose",
                prompt="Where?",
                outcomes=[
                    BranchOutcome(
                        outcome_id="beacon",
                        label="Beacon",
                        consequence="Beacon.",
                        ending_section_id="ending-a",
                    ),
                    BranchOutcome(
                        outcome_id="dock",
                        label="Dock",
                        consequence="Dock.",
                        ending_section_id="ending-b",
                    ),
                ],
            )
        ],
        join_reconciliations={},
    )
