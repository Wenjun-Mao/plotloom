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
from tests.autopilot_seed_fixtures import seed_files
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
    assert view.model_dump() == other.model_dump()
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
            assert current.model_dump() == other.model_dump()
            assert _attempts(store) == retained_attempts
    finally:
        unavailable.rename(seed.project.root)
    assert seed_files(seed.project.root) == seed.project.files
    untouched, current, _calls = copy_awaiting_handoff_seed(seed, tmp_path / "still-machine-only")
    assert current.model_dump() == view.model_dump()
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
