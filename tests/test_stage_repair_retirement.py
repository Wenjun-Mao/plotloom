"""Retired scope-less repair refuses admission and never reaches providers."""

from __future__ import annotations

from threading import Event
from types import SimpleNamespace

import pytest

from plotloom.artifacts import LocalArtifactStore
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import RunKind, StageName
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.pipeline import PipelineEngine
from plotloom.runtime_secrets import RunSecretBroker
from plotloom.project_storage.text_dispatch import ProjectRunDispatcher
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext
from tests.project_storage_exact_repair_support import storage
from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def test_generic_repair_admission_refuses_before_profile_snapshot_lease_or_plan(
    tmp_path, monkeypatch
) -> None:
    store = storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("retired repair must refuse before allocation")

    with monkeypatch.context() as guard:
        guard.setattr(
            store.generation._snapshots,
            "_access",
            SimpleNamespace(leases=SimpleNamespace(lifecycle_write=forbidden)),
        )
        guard.setattr(store.generation._snapshots, "snapshot_in_session", forbidden)
        # Missing profile/project are secondary to the retired kind.
        with pytest.raises(
            InvalidTransitionError, match="scope-less stage repair is retired"
        ):
            store.generation.create_run(
                "missing-project", RunKind.REPAIR, [StageName.STORY_BIBLE]
            )
    assert store.generation_runs() == []


@pytest.mark.parametrize("project_state", ["missing", "unconfirmed"])
def test_dispatcher_repair_refuses_before_open_route_or_profile_allocation(
    tmp_path, monkeypatch, project_state
) -> None:
    project_storage = storage(tmp_path)
    store = (
        project_storage.projects.create(None)
        if project_state == "unconfirmed"
        else None
    )
    project_id = store.project().id if store else "missing-project"
    provider_snapshot = {"profileId": "incomplete-profile"} if store else {}

    def forbidden(*_args, **_kwargs):
        pytest.fail(
            "retired repair reached project opening or route/profile allocation"
        )

    monkeypatch.setattr(project_storage.projects, "open", forbidden)
    monkeypatch.setattr(project_storage.application, "reserve_run_route", forbidden)
    monkeypatch.setattr(ProjectRunDispatcher, "_route_for_snapshot", forbidden)
    monkeypatch.setattr("plotloom.project_storage.text_dispatch.new_id", forbidden)
    broker = RunSecretBroker()
    dispatcher = ProjectRunDispatcher(
        project_storage,
        provider_resolver=FixtureResolver(),
        secrets=broker,
        max_workers=1,
    )
    try:
        with pytest.raises(
            InvalidTransitionError, match="scope-less stage repair is retired"
        ):
            dispatcher.create_run(
                project_id,
                kind=RunKind.REPAIR,
                requested_stages=[],
                provider_snapshot=provider_snapshot,
            )
        if store:
            assert store.project().brief is None
            assert store.generation_runs() == []
    finally:
        dispatcher.close()
        broker.close()
        if store:
            store.close()


@pytest.mark.parametrize("scope", ["absent", "missing", "wrong_parent", "wrong_child"])
def test_corrupt_or_absent_exact_scope_never_falls_back_to_stage_execution(
    tmp_path, monkeypatch, scope
) -> None:
    store = storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    snapshot = fixture_profile().model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        run = store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=snapshot,
        )
    run = run.model_copy(
        update={
            "kind": RunKind.REPAIR,
            "parent_run_id": "parent",
            "work_unit_repair_scope_id": None if scope == "absent" else run.id,
        }
    )

    def read_scope(_run_id):
        if scope == "missing":
            raise NotFoundError("scope missing")
        return SimpleNamespace(
            parent_run_id="different" if scope == "wrong_parent" else "parent",
            child_run_id="different" if scope == "wrong_child" else run.id,
        )

    monkeypatch.setattr(store.generation, "get_work_unit_repair_scope", read_scope)

    class NoProvider:
        def resolve(self, _snapshot):
            raise AssertionError("invalid lineage must fail before provider resolution")

    broker = RunSecretBroker()
    try:
        with pytest.raises(InvalidTransitionError):
            PipelineEngine(store.generation, NoProvider(), broker).execute(
                run,
                RunContext(
                    providers=ProviderPorts(),
                    artifacts=LocalArtifactStore(tmp_path / "artifacts"),
                ),
                Event(),
            )
    finally:
        broker.close()
    assert store.run_trace(run.id).attempts == []
    assert store.generation.list_generation_work_units(run.id) == []
