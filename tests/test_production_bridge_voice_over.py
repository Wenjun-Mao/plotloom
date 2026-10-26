"""The exact F4 VO token keeps its canonical cue semantics."""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy

import pytest

from plotloom.canonical_schema import default_dialogue_timing_profile
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.stage_contracts import StageName
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.project_storage import ProjectFolderStorage
from tests import creative_delivery_fixtures, production_bridge_fixtures
from tests.production_bridge_fixtures import _prepare_installable_bridge

LINE = "灯还亮着。"
NOTES = "低声、客观；保留原叙述。"


@pytest.fixture
def voiced_store(tmp_path, monkeypatch):
    source = creative_delivery_fixtures._pilot_script()
    source["episodes"][0]["scenes"][0]["flow"][3] = {
        "speaker": "VO", "line": LINE, "delivery": NOTES,
    }
    monkeypatch.setattr(creative_delivery_fixtures, "_pilot_script", lambda: deepcopy(source))
    original_board = production_bridge_fixtures._source_shaped_review_board

    def voiced_board(*args, **kwargs):
        board = original_board(*args, **kwargs)
        segment = board["episodes"][0]["segments"][0]
        segment["h3Prompt"] = "\n".join(
            line + f" An off-screen narrator VO says <d>[Chinese] {LINE}</d>."
            if line.startswith("[Shot 4] ") else line
            for line in segment["h3Prompt"].split("\n")
        )
        return board

    monkeypatch.setattr(production_bridge_fixtures, "_source_shaped_review_board", voiced_board)
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(
        update={"shots_per_scene_min": 9, "shots_per_scene_max": 9},
    ))
    with closing(project) as store:
        proposal = _prepare_installable_bridge(store)
        yield storage, store, proposal


def test_exact_vo_survives_reviewed_proposal_installation_and_ordinary_reopen(voiced_store):
    storage, store, proposal = voiced_store
    project_id = store.manifest.project_id
    assert proposal.installable
    source_before = deepcopy(store.script_state().accepted_script.script)
    result = store.accept_production_bridge(ProductionBridgeAcceptRequest(
        expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
    ))
    assert result.installation.status == "current"
    plan = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    assert len(plan.dialogue_cues) == 1
    cue = plan.dialogue_cues[0]
    assert cue.speaker_id is None and cue.voice_over == "VO"
    assert (cue.text, cue.performance_notes, cue.language, cue.delivery.value) == (LINE, NOTES, "zh-CN", "natural")
    assert cue.estimated_duration_units == default_dialogue_timing_profile().estimate_duration_units(cue)
    assert cue.id == cue.beat_id + "-d1"
    assert cue.beat_id.endswith("-b4")
    containing = [shot for shot in board.shots if cue.id in shot.cue_ids]
    assert len(containing) == 1 and containing[0].order == 4
    assert store.script_state().accepted_script.script == source_before
    store.close()
    with closing(storage.projects.open(project_id)) as reopened:
        assert reopened.production_bridge_state().installation.status == "current"
        assert reopened.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS) == plan
        assert reopened.authoring.get_stage_payload(project_id, StageName.STORYBOARD) == board


@pytest.mark.parametrize("speaker", [None, "", "vo", "VO ", "V.O.", "旁白", "narrator", "foreign-speaker"])
def test_projection_does_not_promote_unknown_or_near_match_speakers_to_vo(voiced_store, speaker):
    _storage, store, _proposal = voiced_store
    owner = store.repository.production_bridge
    with store.repository._read() as session:
        inputs, storyboard, script, cast_art = owner._context(session, store.manifest.project_id)
        source = deepcopy(script)
        source["episodes"][0]["scenes"][0]["flow"][3]["speaker"] = speaker
        payload, _intents, conflicts, _advisories, _scenes, _cuts = owner._build(
            session, store.manifest.project_id, inputs=inputs, storyboard=storyboard,
            script=source, cast_and_art=cast_art,
        )
    assert [item.code for item in conflicts] == ["dialogue_speaker_unknown"]
    assert payload["sceneBeats"]["dialogueCues"] == []


def test_mapped_character_dialogue_keeps_character_authority(voiced_store):
    _storage, store, _proposal = voiced_store
    owner = store.repository.production_bridge
    with store.repository._read() as session:
        inputs, storyboard, script, cast_art = owner._context(session, store.manifest.project_id)
        source = deepcopy(script)
        character_id = cast_art["characters"][0]["id"]
        scene = source["episodes"][0]["scenes"][0]
        scene["characters"] = [character_id]
        scene["flow"][3]["speaker"] = character_id
        payload, _intents, conflicts, _advisories, _scenes, _cuts = owner._build(
            session, store.manifest.project_id, inputs=inputs, storyboard=storyboard,
            script=source, cast_and_art=cast_art,
        )
    assert conflicts == []
    cue, = payload["sceneBeats"]["dialogueCues"]
    assert cue["speakerId"] == store.cast_consumer_identity(character_id)
    assert cue["voiceOver"] is None
    assert cue["text"] == LINE and cue["performanceNotes"] == NOTES
