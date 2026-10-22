"""A valid copied pack can grant human authority only inside that exact copy."""
from contextlib import closing

import pytest

from plotloom.autopilot_handoff_contracts import HumanHandoffRequest
from plotloom.persistence.project.autopilot_authority import video_eligible
from plotloom.persistence.project.autopilot_handoff import record_handoff, review_material
from tests.autopilot_geometry_fixtures import copy_geometry_frame_seed
from tests.autopilot_handoff_seed_fixtures import (
    AwaitingHandoffSeed,
    assert_no_human_facts,
    copy_awaiting_handoff_seed,
)
from tests.autopilot_seed_fixtures import run_facts, seed_files
from tests.test_autopilot_handoff import observation


def _attempts(store):
    with store.repository.engine.connect() as connection:
        return connection.exec_driver_sql(
            "SELECT id,snapshot,receipt FROM v2_autopilot_exec_attempts ORDER BY id"
        ).all()


def test_valid_copy_handoff_grants_video_only_in_that_copy_without_seed_access(
    tmp_path, awaiting_handoff_seed,
):
    seed = awaiting_handoff_seed
    left, view, calls = copy_awaiting_handoff_seed(seed, tmp_path / "left")
    sibling, other, _calls = copy_awaiting_handoff_seed(seed, tmp_path / "sibling")
    assert run_facts(view) == run_facts(other)
    with closing(sibling.projects.open(view.project_id)) as store:
        retained_attempts = _attempts(store)
        assert len(retained_attempts) == 16 and all(row.receipt for row in retained_attempts)
    assert len(calls) == len(set(calls)) == 8
    for relative, _digest in seed.project.files:
        paths = [root / relative for root in (seed.project.root, tmp_path / "left", tmp_path / "sibling")]
        assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 3
    unavailable = seed.project.root.with_name(seed.project.root.name + "-unavailable")
    seed.project.root.rename(unavailable)
    try:
        with closing(left.projects.open(view.project_id)) as store:
            assert _attempts(store) == retained_attempts
            assert_no_human_facts(store)
            review = review_material(store)
            assert len(review["bundle"]["references"]) == 2
            assert len(review["bundle"]["frames"]) == 6
            assert len(review["bundle"]["story"]["routes"]) == 2
            result = record_handoff(store, HumanHandoffRequest.model_validate(observation(review)))
            assert result.state == "handed_off"
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
            with store.repository.engine.connect() as connection:
                for table, expected in (
                    ("v2_approval_decisions", 1), ("v2_autopilot_handoffs", 1),
                    ("v2_reviewed_shot_bindings", 6), ("v2_same_person_reviews", 6),
                    ("v2_visual_intents", len({frame.asset_id for frame in view.frames})),
                    ("v2_video_jobs", 0),
                ):
                    assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == expected
            assert _attempts(store) == retained_attempts
        with closing(left.projects.open(view.project_id)) as store:
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
        with closing(sibling.projects.open(view.project_id)) as store:
            assert_no_human_facts(store)
            current = store.repository.autopilot.current(view.project_id)
            assert run_facts(current) == run_facts(other)
            assert _attempts(store) == retained_attempts
    finally:
        unavailable.rename(seed.project.root)
    assert seed_files(seed.project.root) == seed.project.files
    untouched, current, _calls = copy_awaiting_handoff_seed(seed, tmp_path / "still-machine-only")
    assert run_facts(current) == run_facts(view)
    with closing(untouched.projects.open(view.project_id)) as store:
        assert_no_human_facts(store)
    assert seed_files(seed.project.root) == seed.project.files


def test_shared_copy_safeguards_do_not_substitute_geometry_and_handoff_states(
    tmp_path, geometry_frame_seed, awaiting_handoff_seed,
):
    with pytest.raises(AssertionError):
        copy_awaiting_handoff_seed(AwaitingHandoffSeed(geometry_frame_seed, ()), tmp_path / "not-complete")
    with pytest.raises(AssertionError):
        copy_geometry_frame_seed(awaiting_handoff_seed.project, tmp_path / "not-first-geometry")
    assert seed_files(geometry_frame_seed.root) == geometry_frame_seed.files
    assert seed_files(awaiting_handoff_seed.project.root) == awaiting_handoff_seed.project.files


@pytest.mark.parametrize("operation", ["manual", "rollback", "takeover"])
def test_human_operations_keep_retained_work_and_sibling_isolated_without_source(
    tmp_path, monkeypatch, awaiting_handoff_seed, operation,
):
    from tests import test_autopilot_handoff as consumers

    seed = awaiting_handoff_seed
    sibling_root = tmp_path / "sibling"
    sibling, other, retained_image_ids = copy_awaiting_handoff_seed(seed, sibling_root)
    with closing(sibling.projects.open(other.project_id)) as store:
        retained_attempts = _attempts(store)
        assert_no_human_facts(store)
    assert len(retained_attempts) == 16 and len(retained_image_ids) == 8
    sibling_files = seed_files(sibling_root)
    unavailable = seed.project.root.with_name(seed.project.root.name + "-unavailable")
    captured, runtimes = [], []

    def copy_then_remove_source(original_seed, destination):
        assert original_seed is seed and not captured
        result = copy_awaiting_handoff_seed(original_seed, destination)
        storage, view, image_ids = result
        assert image_ids == retained_image_ids
        with closing(storage.projects.open(view.project_id)) as store:
            assert_no_human_facts(store)
            assert _attempts(store) == retained_attempts
            with store.repository.engine.connect() as connection:
                claim = connection.exec_driver_sql("SELECT claim FROM v2_autopilot_runs").scalar_one()
        for relative, _digest in seed.project.files:
            paths = [root / relative for root in (seed.project.root, destination, sibling_root)]
            assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 3
        captured.append((storage, view, claim))
        seed.project.root.rename(unavailable)
        return result

    def no_machine_work(*_args, **_kwargs):
        raise AssertionError("human takeover must not claim, continue or contact retained machine work")

    original_runtime = consumers.runtime

    def fresh_runtime(storage, patch):
        from plotloom.persistence.project.autopilot import AutopilotPersistence

        registry, service, host = original_runtime(storage, patch)
        assert not host.calls and not host.image_calls and not host.statuses and not host.pending
        assert host.admissions == 0 and service._thread is None and service._descriptor is None
        assert service.claim != captured[0][2]
        for name in ("codex_exec_admit", "codex_exec_status", "codex_exec_cancel", "codex_exec_suspend"):
            patch.setattr(registry, name, no_machine_work)
        patch.setattr(service, "acquire_controller", no_machine_work)
        patch.setattr(service, "step", no_machine_work)
        patch.setattr(service.controller, "advance", no_machine_work)
        patch.setattr(service.image_controller, "advance", no_machine_work)
        patch.setattr(AutopilotPersistence, "claim", no_machine_work)
        runtimes.append((registry, service, host))
        return registry, service, host

    functions = {
        "manual": consumers.test_manual_import_replaces_one_frame_and_can_receive_fresh_human_handoff,
        "rollback": consumers.test_mid_handoff_failure_rolls_back_all_native_human_rows,
        "takeover": consumers.test_takeover_accepts_current_bundle_and_explicit_unassessable_authorization,
    }
    try:
        with monkeypatch.context() as patch:
            # Instrument the real factory only to hide the source AFTER copying.
            # Reuse the complete operation/assertion body, including recovery and
            # the second-selection failure; no alternate human-operation path.
            patch.setattr(consumers, "copy_awaiting_handoff_seed", copy_then_remove_source)
            patch.setattr(consumers, "runtime", fresh_runtime if operation == "takeover" else no_machine_work)
            options = {"awaiting_handoff_seed": seed}
            if operation != "manual":
                options["monkeypatch"] = patch
            functions[operation](tmp_path / "left", **options)
            assert not seed.project.root.exists() and unavailable.is_dir()
            storage, view, original_claim = captured[0]
            with closing(storage.projects.open(view.project_id)) as store:
                assert _attempts(store) == retained_attempts
                current = store.repository.autopilot.current(view.project_id)
                assert current.state == ("awaiting_review" if operation == "rollback" else "handed_off")
                if operation == "rollback":
                    assert_no_human_facts(store)
                with store.repository.engine.connect() as connection:
                    assert connection.exec_driver_sql("SELECT claim FROM v2_autopilot_runs").scalar_one() == original_claim
            assert len(runtimes) == (1 if operation == "takeover" else 0)
            for registry, service, host in runtimes:
                assert not host.calls and not host.image_calls and not host.statuses and not host.pending
                assert host.admissions == 0 and not registry.view()["busy"]
                assert service._thread is None and service._descriptor is None
            with closing(sibling.projects.open(other.project_id)) as store:
                assert_no_human_facts(store)
                assert run_facts(store.repository.autopilot.current(other.project_id)) == run_facts(other)
                assert _attempts(store) == retained_attempts
            assert seed_files(sibling_root) == sibling_files
    finally:
        if unavailable.exists():
            unavailable.rename(seed.project.root)
    assert seed_files(seed.project.root) == seed.project.files
