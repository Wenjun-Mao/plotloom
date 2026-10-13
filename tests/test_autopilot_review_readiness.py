"""Incomplete material reads refuse without changing the admitted native run."""

from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_materials import initial_inventory
from plotloom.exceptions import InvalidTransitionError
from tests.autopilot_controller_fixtures import environment


@pytest.mark.parametrize("enforce_limits", [True, False])
@pytest.mark.parametrize("missing", ["cast", "art", "installation", "outdated"])
def test_inventory_requires_present_current_installation_before_loading_material(
    missing, enforce_limits
):
    def bridge():
        assert missing not in {"cast", "art"}, (
            "missing text must refuse before bridge inspection"
        )
        return SimpleNamespace(
            installation=None
            if missing == "installation"
            else SimpleNamespace(status="outdated")
        )

    store = SimpleNamespace(
        cast_state=lambda: SimpleNamespace(
            accepted_cast=None if missing == "cast" else object()
        ),
        art_state=lambda: SimpleNamespace(
            accepted_art=None if missing == "art" else object()
        ),
        production_bridge_state=bridge,
    )
    with pytest.raises(
        InvalidTransitionError, match="current accepted text and installation"
    ):
        initial_inventory(store, object(), enforce_limits=enforce_limits)


def _tree(home):
    return {
        path.relative_to(home).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in home.rglob("*")
        if path.is_file()
    }


def test_early_review_and_handoff_refuse_across_real_text_stages_without_mutation(
    tmp_path, monkeypatch
):
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch)
    client = TestClient(create_project_folder_authoring_app(storage))
    stages = {
        "source",
        "characters",
        "art",
        "script",
        "storyboard",
        "bridge-intent",
        "bridge-presentation",
    }
    observed = set()
    try:
        assert service.acquire_controller()
        for _ in range(40):
            service.step(view.project_id)
            with closing(storage.projects.open(view.project_id)) as store:
                current = store.repository.autopilot.current(view.project_id)
                home = store.home
            newly_adopted = {
                item["operationKey"]
                for item in current.checkpoints
                if item["state"] == "adopted"
            } & stages - observed
            if not newly_adopted:
                continue
            before, sent = _tree(home), tuple(calls)
            endpoint = f"/api/v2/projects/{view.project_id}/autopilot"
            response = client.get(endpoint + "/review")
            assert response.status_code == 409, response.text
            assert "current accepted text and installation" in response.text
            body = {
                "expectedRunRevision": current.revision,
                "bundleHash": "a" * 64,
                "reviewer": "Fixture human",
                "notes": "Incomplete material must refuse.",
                "endorsedReferenceIds": [],
                "frames": [],
            }
            rejection = client.post(endpoint + "/handoff", json=body)
            assert rejection.status_code == 409, rejection.text
            assert (
                "stop automatic work before reviewing current material"
                in rejection.text
            )
            with closing(storage.projects.open(view.project_id)) as store:
                assert store.repository.autopilot.current(view.project_id) == current
                with store.repository.engine.connect() as connection:
                    for table in [
                        "v2_approval_decisions",
                        "v2_visual_intents",
                        "v2_reviewed_shot_bindings",
                        "v2_same_person_reviews",
                        "v2_autopilot_handoffs",
                        "v2_video_jobs",
                    ]:
                        assert (
                            connection.exec_driver_sql(
                                f"SELECT count(*) FROM {table}"
                            ).scalar()
                            == 0
                        )
            assert _tree(home) == before and tuple(calls) == sent
            observed.update(newly_adopted)
            if observed == stages:
                break
        assert observed == stages
        service.control(
            view.project_id,
            RunControlRequest(expected_revision=current.revision, action="takeover"),
        )
        with closing(storage.projects.open(view.project_id)) as store:
            stopped = store.repository.autopilot.current(view.project_id)
        body["expectedRunRevision"] = stopped.revision
        before, sent = _tree(home), tuple(calls)
        rejection = client.post(endpoint + "/handoff", json=body)
        assert (
            rejection.status_code == 409
            and "current accepted text and installation" in rejection.text
        )
        assert _tree(home) == before and tuple(calls) == sent
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.repository.autopilot.current(view.project_id) == stopped
    finally:
        client.close()
        service.close()
