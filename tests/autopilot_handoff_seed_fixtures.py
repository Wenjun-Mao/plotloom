"""A real completed pack, without any human handoff or copied controller."""
from contextlib import closing
from dataclasses import dataclass

import pytest

from plotloom.persistence.project.autopilot_authority import video_eligible
from tests.autopilot_image_fixtures import (
    assert_compact_handoff_pack,
    handoff_image_environment,
    run_pack,
)
from tests.autopilot_seed_fixtures import (
    ClosedAutopilotSeed,
    copy_closed_autopilot_seed,
    freeze_closed_autopilot_seed,
)

HUMAN_FACT_TABLES = (
    "v2_approval_decisions", "v2_visual_intents", "v2_reviewed_shot_bindings",
    "v2_same_person_reviews", "v2_autopilot_handoffs", "v2_video_jobs",
)


@dataclass(frozen=True)
class AwaitingHandoffSeed:
    project: ClosedAutopilotSeed
    image_job_ids: tuple[str, ...]


def assert_no_human_facts(store):
    with store.repository.engine.connect() as connection:
        for table in HUMAN_FACT_TABLES:
            assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
    with store.repository._read() as session:
        assert not video_eligible(session, store.manifest.project_id)


def _assert_awaiting_review(view):
    assert view.state == "awaiting_review" and view.phase == "material-review"
    assert len(view.frames) == 6 and view.bundle is not None and view.bundle_hash is not None
    assert view.handoff is None


def build_awaiting_handoff_seed(root):
    with pytest.MonkeyPatch.context() as patch:
        storage, registry, service, view, calls, text = handoff_image_environment(root, patch, cuts_per_scene=2)
        try:
            complete = run_pack(storage, service, view)
            assert_compact_handoff_pack(storage, view, complete, calls, expected_frames=6)
            _assert_awaiting_review(complete)
            assert len(text) == 8 and len(calls) == 8
            host = registry._codex_exec_test_host
            assert not host.pending and not registry.view()["busy"]
            assert all(status.state == "completed" for status in host.statuses.values())
            with closing(storage.projects.open(view.project_id)) as store:
                home_name = store.home.name
                assert_no_human_facts(store)
                with store.repository.engine.connect() as connection:
                    attempts = connection.exec_driver_sql(
                        "SELECT job_id,domain,state,image_budget_state,receipt FROM v2_autopilot_exec_attempts"
                    ).all()
                    assert len(attempts) == 16
                    assert all(row.state == "completed" and row.receipt is not None for row in attempts)
                    assert {row.job_id for row in attempts if row.domain == "image"} == set(calls)
                    assert {row.job_id for row in attempts if row.domain == "text"} == set(text)
                    assert all(row.image_budget_state == ("consumed" if row.domain == "image" else "none") for row in attempts)
        finally:
            service.close()
        assert service._thread is None and service._descriptor is None
    project = freeze_closed_autopilot_seed(root, view.project_id, home_name)
    return AwaitingHandoffSeed(project, tuple(calls))


def copy_awaiting_handoff_seed(seed, destination):
    storage, view = copy_closed_autopilot_seed(seed.project, destination)
    _assert_awaiting_review(view)
    with closing(storage.projects.open(view.project_id)) as store:
        assert_no_human_facts(store)
    return storage, view, seed.image_job_ids
