"""Quiescent real geometry seeds for isolated ordinary-open corruption checks."""
from contextlib import closing

import pytest

from tests.autopilot_image_fixtures import image_environment
from tests.autopilot_seed_fixtures import copy_closed_autopilot_seed, freeze_closed_autopilot_seed


def first_geometry_frame(storage, service, view):
    for _ in range(30):
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            result = store.repository.autopilot.current(view.project_id)
        if result.frames:
            return result
        assert result.state in {"running", "waiting"}, result.blocker
    raise AssertionError("first geometry frame not selected")


def mismatch(*, context):
    return (941, 1672) if "shot" in context["request"]["frozenSnapshot"] else None


def build_geometry_frame_seed(root):
    with pytest.MonkeyPatch.context() as patch:
        storage, registry, service, view, _calls, _text = image_environment(root, patch, geometry=mismatch)
        try:
            result = first_geometry_frame(storage, service, view)
            assert len(result.frames) == 1 and result.frames[0].geometry_preparation is not None
            host = registry._codex_exec_test_host
            assert not host.pending and not registry.view()["busy"]
            assert all(status.state in {"completed", "failed", "settled"} for status in host.statuses.values())
            with closing(storage.projects.open(view.project_id)) as store:
                home_name = store.home.name
                with store.repository.engine.connect() as connection:
                    assert connection.exec_driver_sql(
                        "SELECT count(*) FROM v2_autopilot_exec_attempts "
                        "WHERE state NOT IN ('completed','failed','settled') OR image_budget_state='reserved'"
                    ).scalar() == 0
        finally:
            service.close()
        assert service._thread is None and service._descriptor is None
    return freeze_closed_autopilot_seed(root, view.project_id, home_name)


def copy_geometry_frame_seed(seed, destination):
    storage, view = copy_closed_autopilot_seed(seed, destination)
    assert len(view.frames) == 1 and view.frames[0].geometry_preparation is not None
    return storage, view
