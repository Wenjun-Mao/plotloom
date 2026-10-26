"""F5 seed variants retain fresh per-copy candidate and pin authority."""
from contextlib import closing

import pytest

from plotloom.creative_handoff_identity import request_hash
from plotloom.persistence.schema import (
    CreativeHandoffExecutionPinRow,
    StoryboardReviewCandidateRow,
)
from tests import creative_delivery_fixtures
from tests.autopilot_seed_fixtures import seed_files
from tests.f5_dialogue_timing_fixtures import (
    F5_BRIEF,
    LINE,
    NOTES,
    assert_f5_script_variant,
    assert_no_f5_state,
    open_f5_script_copy,
)
from tests.f5_dialogue_timing_fixtures import f5_script_seeds as f5_script_seeds


@pytest.mark.parametrize("variant,style,lines", [
    ("single-realistic", "realistic", [LINE]),
    ("single-brief", "brief", [LINE]),
    ("split-realistic", "realistic", [LINE[:12], LINE[12:]]),
    ("action-realistic", "realistic", []),
    ("action-brief", "brief", []),
])
def test_exact_variant_and_fresh_f5_authority_are_isolated_from_seed_and_sibling(
    tmp_path, f5_script_seeds, variant, style, lines,
):
    seed = f5_script_seeds[variant]
    assert "lang" not in creative_delivery_fixtures._pilot_script()  # Scoped patch restored.
    left_storage, left = open_f5_script_copy(tmp_path / "left", seed)
    with closing(left):
        right_storage, right = open_f5_script_copy(tmp_path / "right", seed)
        with closing(right):
            for store in (left, right):
                assert_f5_script_variant(store, variant)
                assert store.project().brief == F5_BRIEF
                script = store.script_state().accepted_script.script
                assert script["lang"] == "en"
                dialogue = [item for episode in script["episodes"] for scene in episode["scenes"]
                            for item in scene["flow"] if "line" in item]
                assert dialogue == [{"speaker": "VO", "line": text, "delivery": NOTES} for text in lines]
                contract = store.art_state().accepted_art.binding.render_contract
                assert (contract.get("authority") == "saved_brief") is (style == "brief")
            for relative, _digest in seed.files:
                files = [home / relative for home in (seed.home, left.home, right.home)]
                assert len({(path.stat().st_dev, path.stat().st_ino) for path in files}) == 3
            retained_script = next(name for name, _digest in seed.files if name.endswith("/delivery/script.json"))
            sibling_content = (right.home / retained_script).read_bytes()
        left_home, right_home = left.home, right.home
        # Whole-file inventories belong to closed databases, including copies.
        sibling_before = seed_files(right_home)
        job_id = "ch_" + "t" * 32
        candidate, frozen = left.prepare_storyboard_review_candidate(job_id)
        with left.repository._read() as session:
            row = session.get(StoryboardReviewCandidateRow, job_id)
            pin = session.get(CreativeHandoffExecutionPinRow, job_id)
            assert row.status == "prepared" and row.request == frozen.model_dump(mode="json", by_alias=True)
            assert pin.stage == "storyboard" and pin.request_hash == request_hash(frozen)
        assert candidate.job_id == job_id
        left.cancel_storyboard_review_candidate(job_id)
        with left.repository._read() as session:
            assert session.get(StoryboardReviewCandidateRow, job_id).status == "cancelled"
        assert seed_files(right_home) == sibling_before
        assert seed_files(seed.home) == seed.files
    (left_home / retained_script).write_text("deliberately changed case-local accepted Script package")
    with closing(right_storage.projects.open(seed.project_id)) as reopened:
        assert_f5_script_variant(reopened, variant)
        assert (right_home / retained_script).read_bytes() == sibling_content
        assert_no_f5_state(reopened)
    assert seed_files(right_home) == sibling_before
    assert seed_files(seed.home) == seed.files
    assert left_storage.application.root != right_storage.application.root
