"""Five closed accepted-F4 variants; every F5 operation remains copy-local."""
from contextlib import closing
from copy import deepcopy

import pytest

from plotloom.art_style import freeze_art_style
from plotloom.cast_style import freeze_cast_style
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import close_blockers
from tests import creative_delivery_fixtures
from tests.specialist_reconciliation_seed import (
    freeze_accepted_script_project,
    open_accepted_script_copy,
)

LINE = "她私封暗渠。交钥，过错公开；留钥，居民可能被困。"
NOTES = "简短客观叙述，普通话，平稳清楚。"
F5_INITIAL_BRIEF = FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 8, "shots_per_scene_max": 9})
F5_BRIEF = F5_INITIAL_BRIEF.model_copy(update={
    "decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0,
})
VARIANTS = {
    "single-realistic": ("realistic", "single"),
    "single-brief": ("brief", "single"),
    "split-realistic": ("realistic", "split"),
    "action-realistic": ("realistic", "action"),
    "action-brief": ("brief", "action"),
}


def variant_for(configuration):
    style = configuration if isinstance(configuration, str) else configuration["style"]
    mode = "single"
    if isinstance(configuration, dict):
        mode = "split" if configuration.get("multi") else "single" if configuration.get("dialogue", True) else "action"
    variant = f"{mode}-{style}"
    assert variant in VARIANTS
    return variant


def variant_script(variant):
    _style, mode = VARIANTS[variant]
    source = creative_delivery_fixtures._pilot_script()
    source["lang"] = "en"
    flow = source["episodes"][0]["scenes"][0]["flow"]
    if mode != "action":
        flow[3] = {"speaker": "VO", "line": LINE, "delivery": NOTES}
    if mode == "split":
        flow[3]["line"] = LINE[:12]
        flow[4] = {"speaker": "VO", "line": LINE[12:], "delivery": NOTES}
    return source


def assert_no_f5_state(store):
    with store.repository.engine.connect() as connection:
        for table in ("v2_storyboard_review_candidates", "v2_storyboard_review_revisions"):
            assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
        assert connection.exec_driver_sql(
            "SELECT count(*) FROM v2_creative_handoff_execution_pins WHERE stage='storyboard'"
        ).scalar() == 0
    state = store.storyboard_review_state()
    assert state.candidate is None and state.accepted_review is None


def assert_f5_script_variant(store, variant):
    style, _mode = VARIANTS[variant]
    assert store.project().brief == F5_BRIEF
    source = store.source_outline_state()
    assert source.source and source.accepted_outline and source.accepted_section_map
    assert source.graph_admission.status == "current" and not source.graph_admission.stale_reasons
    assert not source.section_map_stale_reasons
    cast, art, script = store.cast_state(), store.art_state(), store.script_state()
    for state in (cast, art, script):
        assert state.accepted_review_state.status == "current" and not state.stale_reasons
    assert script.accepted_script.script == variant_script(variant)
    assert cast.accepted_cast.binding.render_contract == freeze_cast_style(style, F5_BRIEF.visual_direction)
    assert art.accepted_art.binding.render_contract == freeze_art_style(style, F5_BRIEF.visual_direction)
    assert_no_f5_state(store)
    assert not close_blockers(store)


def build_f5_script_seed(root, variant):
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    source = variant_script(variant)
    with closing(storage.projects.create(F5_INITIAL_BRIEF)) as store:
        # Only accepted upstream construction sees the modified pilot source.
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(creative_delivery_fixtures, "_pilot_script", lambda: deepcopy(source))
            creative_delivery_fixtures._accepted_f4_script(store, render_style=VARIANTS[variant][0])
        assert_f5_script_variant(store, variant)
        with store.repository.engine.connect() as connection:
            for model in set(CANDIDATE_ROWS.values()):
                table = model.__table__.name
                assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}" WHERE status != \'accepted\'').scalar() == 0
            for table in (
                "v2_autopilot_runs", "v2_autopilot_exec_attempts", "v2_generation_runs",
                "v2_media_tasks", "v2_video_jobs", "v2_image_jobs",
                "v2_character_reference_proposals", "v2_art_reference_proposals",
                "v2_production_bridge_intent_jobs",
            ):
                assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
        home, project_id = store.home, store.manifest.project_id
    assert not (storage.application.root / "specialists").exists()
    return freeze_accepted_script_project(home, project_id)


@pytest.fixture(scope="session")
def f5_script_seeds(tmp_path_factory):
    return {variant: build_f5_script_seed(tmp_path_factory.mktemp(f"f5-script-{variant}"), variant)
            for variant in VARIANTS}


def open_f5_script_copy(root, seed):
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    return storage, open_accepted_script_copy(storage, seed)
