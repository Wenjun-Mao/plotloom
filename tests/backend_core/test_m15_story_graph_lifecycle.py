from __future__ import annotations

import pytest

from plotloom.domain import ProjectBrief, RunKind, StageName
from plotloom.generation.story_graph_topology import StoryGraphTopologyError
from plotloom.persistence import SQLiteRepository

from .conftest import make_story_bible


def test_story_graph_topology_is_persisted_bound_to_plan_and_exposed_in_trace() -> None:
    repository = SQLiteRepository("sqlite://")
    try:
        project = repository.create_project(
            ProjectBrief(
                title="冻结图",
                synopsis="主角必须选择一条路线，随后在危机前汇流。",
                ending_count=3,
                decision_points_per_path=2,
                desired_join_count=1,
                node_budget=9,
                max_out_degree=3,
            )
        )
        repository.update_stage(project.id, StageName.STORY_BIBLE, 0, make_story_bible())
        run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_GRAPH])

        plan = repository.get_generation_plan(run.id)
        topology = repository.get_story_graph_topology(run.id)
        trace = repository.get_run_execution_trace(run.id)
        assert topology is not None
        assert plan.story_graph_topology_hash == topology.topology_hash
        assert trace.story_graph_topology is not None
        assert trace.story_graph_topology.topology_hash == topology.topology_hash
        assert trace.story_graph_topology.generation_plan_hash == plan.plan_hash

        repository.start_run(run.id)
        stage_plan = repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)
        assert stage_plan.generation_plan_hash == plan.plan_hash
    finally:
        repository.close()


def test_infeasible_graph_brief_fails_before_a_run_or_provider_work_is_created() -> None:
    repository = SQLiteRepository("sqlite://")
    try:
        project = repository.create_project(
            ProjectBrief(
                title="不可行",
                synopsis="约束故意无法满足。",
                ending_count=3,
                decision_points_per_path=2,
                desired_join_count=1,
                node_budget=6,
                max_out_degree=3,
            )
        )
        repository.update_stage(project.id, StageName.STORY_BIBLE, 0, make_story_bible())

        with pytest.raises(StoryGraphTopologyError) as captured:
            repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_GRAPH])
        assert captured.value.code == "topology.node_budget_too_small"
        assert repository.list_project_runs(project.id) == []
    finally:
        repository.close()
