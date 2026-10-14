"""Complete automatic material pack through existing image owners, fake only."""
from contextlib import closing
import pytest
from tests.autopilot_image_fixtures import image_environment, run_pack, deliver_image
from plotloom.autopilot_materials import initial_inventory
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService


def test_complete_pack_selects_all_subjects_and_unique_route_frames_without_human_facts(tmp_path, monkeypatch):
    storage, registry, service, view, calls, text_calls = image_environment(tmp_path, monkeypatch)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            inventory = initial_inventory(store, view.policy)
        complete = run_pack(storage, service, view)
        assert complete.state == "awaiting_review" and complete.bundle_hash and complete.handoff is None
        assert len(calls) == len(set(calls)) == len(inventory.subjects)
        assert len(text_calls) == 8
        assert inventory.route_count == 2
        assert len(complete.frames) == 27 and len(calls) == 29
        assert {frame.shot_id for frame in complete.frames} == {item.id for item in inventory.subjects if item.owner == "image"}
        assert len(complete.bundle["references"]) == sum(item.owner != "image" for item in inventory.subjects)
        assert not registry.view()["busy"]
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository.engine.connect() as connection:
                for table in ("v2_approval_decisions", "v2_visual_intents", "v2_reviewed_shot_bindings", "v2_same_person_reviews", "v2_video_jobs"):
                    assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
    finally:
        service.close()


def current(storage, view):
    with closing(storage.projects.open(view.project_id)) as store:
        return store.repository.autopilot.current(view.project_id)


def sent_reference(storage, service, view):
    for _ in range(3):
        service.step(view.project_id)
    retained = current(storage, view)
    checkpoint = next(item for item in retained.checkpoints if item["evidence"]["owner"] == "character-reference")
    assert checkpoint["state"] == "sent"
    return retained, checkpoint


@pytest.mark.parametrize("limits", [{"max_images": 1}, {"max_jobs": 9}])
def test_complete_inventory_ceiling_blocks_before_any_image_job(tmp_path, monkeypatch, limits):
    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch, limits=limits)
    try:
        service.step(view.project_id)
        result = current(storage, view)
        assert result.state == "blocked"
        assert not any(item["evidence"]["owner"] in {"image", "character-reference", "art-reference"} for item in result.checkpoints)
        assert not calls and not registry.view()["busy"]
    finally:
        service.close()


def test_gallery_includes_unfilmed_cast_and_every_art_prop(tmp_path, monkeypatch):
    from copy import deepcopy
    import json
    from pathlib import Path
    from tests import autopilot_controller_fixtures
    source = autopilot_controller_fixtures.candidate
    prop = json.loads((Path(__file__).resolve().parents[1] / "third_party/shuohao-skills/skills/novel-art/examples/渡口-art.json").read_text())["props"][0]
    def candidate(store, request):
        value = source(store, request)
        if request.stage == "characters":
            observer = deepcopy(value["characters"][0])
            observer.update(id="observer", name="Observer")
            value["characters"].append(observer)
        if request.stage == "art":
            value["props"] = [deepcopy(prop)]
            preset = request.input_artifacts["art-style-contract.json"]["preset"]["render"]
            value["props"][0]["image"]["prompt"] = preset + " " + value["props"][0]["image"]["prompt"]
        return value
    monkeypatch.setattr(autopilot_controller_fixtures, "candidate", candidate)
    storage, _registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            inventory = initial_inventory(store, view.policy)
        assert any(item.owner == "character-reference" and item.id == "observer" for item in inventory.subjects)
        assert all("observer" not in item.character_ids for item in inventory.subjects if item.owner == "image")
        assert any(item.owner == "art-reference" and item.subject_type == "prop" and item.id == "P01" for item in inventory.subjects)
        for _ in range(20):
            service.step(view.project_id)
            result = current(storage, view)
            gallery = [item for item in result.checkpoints if item["evidence"]["owner"] in {"character-reference", "art-reference"}]
            if len(gallery) == 4 and all(item["state"] == "adopted" for item in gallery):
                break
            assert result.state in {"running", "waiting"}, result.blocker
        assert len(gallery) == 4 and all(item["state"] == "adopted" for item in gallery)
        assert len(calls) == 4 and not result.frames
    finally:
        service.close()


@pytest.mark.parametrize("action", ["pause", "cancel", "takeover"])
def test_late_reference_retains_original_receipt_without_selection(tmp_path, monkeypatch, action):
    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        retained, checkpoint = sent_reference(storage, service, view)
        service.control(view.project_id, RunControlRequest(expected_revision=retained.revision, action=action))
        with closing(storage.projects.open(view.project_id)) as store:
            deliver_image(store, retained, checkpoint, host=registry._codex_exec_test_host)
        service.step(view.project_id)
        result = current(storage, view)
        assert result.state == {"pause": "paused", "cancel": "cancelled", "takeover": "taken_over"}[action]
        with closing(storage.projects.open(view.project_id)) as store:
            assert not store.media.list_character_reference_decisions(view.project_id)["decisions"]
        assert not registry.view()["busy"]
        if action == "pause":
            assert next(item for item in result.checkpoints if item["id"] == checkpoint["id"])["state"] == "delivered"
            service.control(view.project_id, RunControlRequest(expected_revision=result.revision, action="resume"))
            service.step(view.project_id)
            assert next(item for item in current(storage, view).checkpoints if item["id"] == checkpoint["id"])["state"] == "adopted"
        assert calls == [checkpoint["evidence"]["jobId"]]
    finally:
        service.close()


def test_extra_output_is_disclosed_blocker_and_never_competing_selection(tmp_path, monkeypatch):
    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        retained, checkpoint = sent_reference(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            deliver_image(store, retained, checkpoint, output_count=2, host=registry._codex_exec_test_host)
        service.step(view.project_id)
        service.step(view.project_id)
        result = current(storage, view)
        assert result.state == "blocked" and not result.frames
        assert not registry.view()["busy"]
        with closing(storage.projects.open(view.project_id)) as store:
            assert not store.media.list_character_reference_decisions(view.project_id)["decisions"]
        assert len(calls) == 1
    finally:
        service.close()


def test_pause_at_image_send_boundary_prevents_native_dispatch(tmp_path, monkeypatch):
    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        service.step(view.project_id)
        service.step(view.project_id)
        retained = current(storage, view)
        checkpoint = next(item for item in retained.checkpoints if item["evidence"]["owner"] == "character-reference")
        service.control(view.project_id, RunControlRequest(expected_revision=retained.revision, action="pause"))
        service.step(view.project_id)
        result = current(storage, view)
        assert result.state == "paused" and calls == [] and not registry.view()["busy"]
        assert next(item for item in result.checkpoints if item["id"] == checkpoint["id"])["state"] == "prepared"
    finally:
        service.close()


def test_native_unknown_image_restart_reconciles_original_identity_without_resend(tmp_path, monkeypatch):
    import sqlite3
    from pathlib import PurePosixPath

    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch, auto_deliver=False)
    resumed = None
    try:
        for _ in range(3):
            service.step(view.project_id)
        retained = current(storage, view)
        checkpoint = next(item for item in retained.checkpoints if item["evidence"]["owner"] == "character-reference")
        with closing(storage.projects.open(view.project_id)) as store:
            attempt = store.repository.autopilot.exec_attempt_for_operation(view.id, checkpoint["operationKey"])
        assert attempt is not None and attempt.state == "running"
        registry._codex_exec_test_host.lose_attempt(attempt.attempt_id)
        service.close()
        resumed = AutopilotService(storage, registry)
        assert resumed.acquire_controller()
        resumed.step(view.project_id)
        retained = current(storage, view)
        checkpoint = next(item for item in retained.checkpoints if item["evidence"]["owner"] == "character-reference")
        assert checkpoint["state"] == "outcome_unknown"
        with closing(storage.projects.open(view.project_id)) as store:
            unknown_attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                retained.id, checkpoint["operationKey"]
            )
            assert unknown_attempt.state == "outcome_unknown" and receipt is None
            assert unknown_attempt.image_budget_state == "reserved"
            with sqlite3.connect(store.database_path) as connection:
                original_row = connection.execute(
                    "SELECT snapshot,image_budget_state,reserved_image_outputs "
                    "FROM v2_autopilot_exec_attempts WHERE id=?",
                    (str(unknown_attempt.attempt_id),),
                ).fetchone()
            run_directory = next(
                path for path in (store.home / "runs").iterdir()
                if path.name.endswith("__" + unknown_attempt.job_id)
            )
            package_request = run_directory / "jobs" / unknown_attempt.job_id / "package" / "request.json"
            original_package_request = package_request.read_bytes()

        resumed.control(
            view.project_id,
            RunControlRequest(expected_revision=retained.revision, action="pause"),
        )
        resumed.step(view.project_id)
        paused = current(storage, view)
        assert paused.state == "paused"
        from plotloom.project_storage.operational_state import ProjectBusyError
        from plotloom.project_storage.recovery_validation import payload_inventory, payload_paths

        # A retained unknown image attempt still owns an active publication
        # lease, so snapshot creation must refuse it. Exercise the exact
        # read-only payload inventory that snapshot creation uses after that
        # gate, without bypassing the lease.
        with pytest.raises(ProjectBusyError, match="character_reference_publication_active"):
            storage.recovery.create_snapshot(view.project_id)
        inventory_paths = payload_paths(store.home, store.database_path)
        assert PurePosixPath("project.sqlite3") in inventory_paths
        inventory = payload_inventory(store.home, inventory_paths)
        assert inventory[PurePosixPath("project.sqlite3")].content_hash
        with sqlite3.connect(store.database_path) as connection:
            after_row = connection.execute(
                "SELECT snapshot,image_budget_state,reserved_image_outputs "
                "FROM v2_autopilot_exec_attempts WHERE id=?",
                (str(unknown_attempt.attempt_id),),
            ).fetchone()
        assert after_row == original_row
        assert original_row[1:] == ("reserved", 1)
        assert package_request.read_bytes() == original_package_request

        resumed.control(
            view.project_id,
            RunControlRequest(expected_revision=paused.revision, action="resume"),
        )
        resumed.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            deliver_image(store, retained, checkpoint, host=registry._codex_exec_test_host)
        resumed.step(view.project_id)
        resumed.step(view.project_id)
        assert next(item for item in current(storage, view).checkpoints if item["id"] == checkpoint["id"])["state"] == "adopted"
        assert calls == [checkpoint["evidence"]["jobId"]]
        assert not registry.view()["busy"]
    finally:
        service.close()
        if resumed:
            resumed.close()
