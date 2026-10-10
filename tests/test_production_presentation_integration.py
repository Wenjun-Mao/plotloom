"""Storage-backed production presentation and F5 integration contracts."""

from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.production_presentation import (
    prepare_presentation,
    project_presentation,
    review_presentation,
)
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.production_presentation_fixtures import _package, _request, _updates


def test_media_context_does_not_reactivate_narrative_ui_prose(tmp_path: Path):
    from plotloom.persistence.project.media_image_currentness import ImageJobCurrentness
    from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        proposal = _prepare_installable_bridge(store)
        store.accept_production_bridge(
            ProductionBridgeAcceptRequest(
                expected_proposal_revision=proposal.revision,
                expected_content_hash=proposal.content_hash,
            )
        )
        project_id = store.manifest.project_id
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        bible = store.authoring.get_stage_payload(project_id, StageName.STORY_BIBLE)
        beats = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
        beats = beats.model_copy(
            update={
                "scenes": [
                    scene.model_copy(update={"objective": "RAW_RUNTIME_QUESTION"})
                    for scene in beats.scenes
                ],
                "beats": [
                    beat.model_copy(
                        update={
                            "description": "RAW_RUNTIME_QUESTION",
                            "purpose": "RAW_RUNTIME_QUESTION",
                            "visible_event": "Stop then gaze toward the junction.",
                        }
                    )
                    for beat in beats.beats
                ],
            }
        )
        context = ImageJobCurrentness.image_job_resolved_context(
            shot=board.shots[0], storyboard=board, story_bible=bible, scene_beats=beats
        )
        assert "RAW_RUNTIME_QUESTION" not in str(context)
        assert "Stop then gaze toward the junction." in str(context)


def test_fractional_source_installs_exact_sums_and_accepted_cut_lineage(tmp_path: Path):
    from plotloom.persistence.project.media_video_source import VideoSourceTiming
    from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        proposal = _prepare_installable_bridge(store, seconds=2.5)
        store.accept_production_bridge(
            ProductionBridgeAcceptRequest(
                expected_proposal_revision=proposal.revision,
                expected_content_hash=proposal.content_hash,
            )
        )
        project_id = store.manifest.project_id
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        beats = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
        assert all(shot.duration_units == 2500 for shot in board.shots)
        assert all(scene.duration_budget_units == 22500 for scene in beats.scenes)
        last = board.shots[8]
        assert "action 8." in last.action and "action 9." in last.action
        assert last.action.index("action 8.") < last.action.index("action 9.")
        access = store.repository.production_bridge._access
        timing = VideoSourceTiming(access, store.repository.production_bridge)
        with access.leases.read() as session:
            frozen = timing.binding_in_session(
                session, project_id, board.shots[0].id, 2500
            )
            assert frozen["cut"]["seconds"] == 2.5 and frozen["durationUnits"] == 2500
            assert timing.binding_is_current(
                session, project_id, board.shots[0].id, 2500, frozen
            )
            with pytest.raises(InvalidTransitionError, match="differs"):
                timing.binding_in_session(session, project_id, board.shots[0].id, 2000)


def test_raw_f5_accepts_submillisecond_time_but_production_conflicts_explicitly(
    tmp_path: Path,
):
    from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
    from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage
    from tests.production_bridge_fixtures import _source_shaped_review_board

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "e" * 32)
        ready = store.admit_storyboard_review_delivery(
            _deliver_stage(
                store,
                request,
                "storyboard.json",
                _source_shaped_review_board(2.5001),
                "submillisecond",
            )
        )
        accepted = store.accept_storyboard_review_candidate(
            StoryboardReviewAcceptRequest(
                job_id=candidate.job_id,
                expected_review_revision=0,
                binding=ready.binding,
            )
        )
        assert accepted.status == "accepted"
        proposal = store.prepare_production_bridge(
            store.production_bridge_state().preparation.request
        ).proposal
        assert proposal is not None and not proposal.installable
        assert any(
            conflict.code == "cut_duration_invalid" for conflict in proposal.conflicts
        )


def test_fresh_prepare_retains_the_accepted_longer_cut_review_policy(tmp_path: Path):
    from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
    from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage
    from tests.production_bridge_fixtures import _source_shaped_review_board

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate(
            "ch_" + "f" * 32, max_cut_seconds=12
        )
        board = _source_shaped_review_board()
        board["params"]["maxCutSeconds"] = 12
        ready = store.admit_storyboard_review_delivery(
            _deliver_stage(store, request, "storyboard.json", board, "longer-policy")
        )
        accepted = store.accept_storyboard_review_candidate(
            StoryboardReviewAcceptRequest(
                job_id=candidate.job_id,
                expected_review_revision=0,
                binding=ready.binding,
            )
        )
        assert accepted.accepted_review.binding.review_max_cut_seconds == 12
        assert (
            store.prepare_production_bridge(
                store.production_bridge_state().preparation.request
            ).proposal
            is not None
        )
        assert (
            store.storyboard_review_state().accepted_review.binding.review_max_cut_seconds
            == 12
        )


@pytest.mark.parametrize("words", ["  今晚不去了，明天见。  ", "\t我还在老地方。\n"])
def test_exact_visible_span_survives_projection_canonical_serialization_and_media_prompt(
    tmp_path: Path, words: str
):
    import json

    from plotloom.canonical_schema import ShotV2
    from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
    from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
    from tests.test_h3_i2va_prompt import _review

    package = _package()
    evidence = deepcopy(package.frozen_evidence)
    evidence["script"]["episodes"][0]["scenes"][0]["flow"][2] = {"action": words}
    package = prepare_presentation(
        inputs=evidence["inputs"],
        script=evidence["script"],
        storyboard=evidence["storyboard"],
        mapping=evidence["sectionMap"],
    )
    entries = _updates(package)
    entries[2]["spans"] = [{"start": 0, "end": len(words), "role": "visible_text"}]
    reviewed = review_presentation(package, _request(package, entries))
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        proposal = _prepare_installable_bridge(store)
        store.accept_production_bridge(
            ProductionBridgeAcceptRequest(
                expected_proposal_revision=proposal.revision,
                expected_content_hash=proposal.content_hash,
            )
        )
        canonical_shot = (
            store.authoring.get_stage_payload(
                store.manifest.project_id, StageName.STORYBOARD
            )
            .shots[0]
            .model_dump(mode="json", by_alias=True)
        )
    canonical_shot["id"] = "opening-s1-c1"
    payload = {
        "sceneBeats": {"beats": [{"id": "opening-s1-b3"}]},
        "storyboard": {
            "shots": [canonical_shot],
            "shotBeatLinks": [{"shotId": "opening-s1-c1", "beatId": "opening-s1-b3"}],
        },
    }
    projected = project_presentation(payload, reviewed)
    shot = ShotV2.model_validate(projected["storyboard"]["shots"][0]).model_dump(
        mode="json", by_alias=True
    )
    assert shot["visibleTexts"][0]["text"] == words
    snapshot = {"shot": shot, "resolvedContext": {"characters": [], "dialogueCues": []}}
    prompt = compile_i2va_prompt(snapshot, _review(snapshot))
    assert json.dumps(words, ensure_ascii=False) in prompt
    assert "<d>" not in prompt
    assert (
        shot["visibleTexts"][0]["sourceContentHash"] == package.sources[2].source_hash
    )
