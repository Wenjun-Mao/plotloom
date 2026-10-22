"""Non-collected helpers for production rebuild contract tests."""

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from plotloom.project_storage import ProjectFolderStorage
from tests.production_bridge_fixtures import (
    _prepare_installable_bridge,
    _review_fixture_presentation,
)


def _accept(store, proposal):
    return store.accept_production_bridge(
        ProductionBridgeAcceptRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
        )
    )


def _review(store, proposal):
    target = proposal.replacement_target
    proposal = _review_fixture_presentation(store, proposal)
    assert proposal.replacement_target == target
    saved = store.update_production_bridge_intent_package(
        ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
            entries=[
                {"id": entry.id, "text": "New author purpose " + entry.id}
                for entry in proposal.intent_package.entries
            ],
        )
    ).proposal
    assert saved.replacement_target == target
    return saved


def _store(tmp_path):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    return storage, storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"})
    )


def _heads(store):
    return {
        stage.value: store.authoring.get_stage_head(
            store.manifest.project_id, stage
        ).model_dump(mode="json")
        for stage in StageName
    }


def _effects_mapping(store):
    from plotloom.source_outline_contracts import SectionMap
    from tests.source_graph_fixtures import letter_section_map

    data = letter_section_map(
        store.manifest.project_id, store.project().brief
    ).model_dump(mode="json", by_alias=True)
    edge = next(
        item for item in data["topology"]["edges"] if item["targetNodeId"] == "ending-a"
    )
    edge["entityStateEffects"] = [
        {"entityType": "location", "entityId": "S01", "state": "dawn"}
    ]
    return SectionMap.model_validate(data)


def _effects_store(tmp_path):
    from plotloom.canonical_schema import StoryBibleV2
    from tests.backend_core.conftest import make_story_bible

    _, store = _store(tmp_path)
    project = store.project()
    store.update_brief(
        project.brief.model_copy(
            update={
                "decision_points_per_path": 1,
                "ending_count": 2,
                "desired_join_count": 0,
            }
        ),
        expected_revision=project.revision,
    )
    data = make_story_bible().model_dump(mode="json", by_alias=True)
    data["locations"] = [
        {
            "id": "S01",
            "name": "Beacon",
            "description": "Room",
            "visualAnchors": [],
            "soundAnchors": [],
            "allowedStates": ["dawn"],
            "continuityRules": [],
        }
    ]
    store.authoring.update_stage(
        store.manifest.project_id,
        StageName.STORY_BIBLE,
        0,
        StoryBibleV2.model_validate(data),
    )
    proposal = _prepare_installable_bridge(store, structure_factory=_effects_mapping)
    return store, proposal
