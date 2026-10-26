"""Small provider-free production journey for leaf generation contracts."""

from __future__ import annotations

from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.artifact_contracts import ArtifactKind
from plotloom.run_contracts import RunStatus
from plotloom.stage_contracts import STAGE_ORDER, StageName
from plotloom.generation.work_unit_contracts import (
    WorkUnitPromptContract,
)
from plotloom.persistence import stable_hash
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def test_small_split_pipeline_installs_and_reopens_leaf_contract_provenance(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    brief = FIXED_CHINESE_BRIEF.model_copy(
        update={
            "decision_points_per_path": 1,
            "ending_count": 2,
            "desired_join_count": 0,
            "node_budget": 4,
            "shots_per_scene_min": 1,
            "shots_per_scene_max": 1,
        }
    )
    store = storage.projects.create(brief)
    run = ProjectPipelineExecutor(FixtureResolver()).execute(
        store, profile=fixture_profile()
    )
    assert run.status == RunStatus.SUCCEEDED
    canonical = store.canonical_stages()
    assert [item.head.stage for item in canonical] == list(STAGE_ORDER)
    graph, scenes, storyboard = [item.payload for item in canonical[1:]]
    assert (
        len(
            {edge.source_node_id for edge in graph.edges if edge.kind.value == "choice"}
        )
        == 1
    )
    assert sum(node.kind.value == "ending" for node in graph.nodes) == 2
    footage = sum(node.footage_mode == "footage" for node in graph.nodes)
    assert len(scenes.scenes) == len(scenes.beats) == len(storyboard.shots) == footage
    assert scenes.dialogue_cues == []
    assert all(shot.audio_plan.events == [] for shot in storyboard.shots)
    before = stable_hash([item.model_dump(mode="json") for item in canonical])
    trace = store.run_trace(run.id)
    contracts = [
        artifact.content["contract"]
        for artifact in trace.artifacts
        if artifact.kind == ArtifactKind.PROMPT
    ]
    for value in contracts:
        assert WorkUnitPromptContract.model_validate(value).snapshot_dump() == value
    assert {
        WorkUnitPromptContract.model_validate(value).stage for value in contracts
    } == set(STAGE_ORDER)
    project_id = store.project().id
    store.close()
    reopened = storage.projects.open(project_id)
    assert (
        stable_hash(
            [item.model_dump(mode="json") for item in reopened.canonical_stages()]
        )
        == before
    )
    assert reopened.run_trace(run.id).model_dump(mode="json") == trace.model_dump(
        mode="json"
    )
