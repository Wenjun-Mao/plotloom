from copy import deepcopy
from contextlib import closing
from pathlib import Path

import pytest

from plotloom.production_timing import source_seconds_to_milliseconds
from plotloom.production_presentation import prepare_presentation, review_presentation, project_presentation, ProductionPresentationUpdateRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
from tests.test_production_bridge import _prepare_installable_bridge


@pytest.mark.parametrize("seconds,units", [(2.5, 2500), (1.001, 1001), (5, 5000), (10**35 + 1, (10**35 + 1)*1000)])
def test_exact_ms(seconds, units):
    assert source_seconds_to_milliseconds(seconds) == units


@pytest.mark.parametrize("seconds", [True, False, 0, -1, float("nan"), float("inf"), -float("inf"), 2.5001, "2.5", None])
def test_unrepresentable_ms(seconds):
    with pytest.raises(ValueError):
        source_seconds_to_milliseconds(seconds)


def test_fresh_prepare_cannot_launder_stale_accepted_f5(tmp_path: Path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        before = _prepare_installable_bridge(store)
        script = store.script_state().accepted_script
        store.reopen_script(ScriptReopenRequest(expected_script_revision=script.revision))
        with pytest.raises(InvalidTransitionError):
            store.prepare_production_bridge()
        episode = deepcopy(script.script["episodes"][0]); episode["cliff"] = "Changed accepted authority"
        store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=script.revision, binding=script.binding, section_id="opening", episode=episode))
        assert store.storyboard_review_state().status == "stale"
        with pytest.raises(InvalidTransitionError, match="stale"):
            store.prepare_production_bridge()
        after = store.production_bridge_state().proposal
        assert after.revision == before.revision and after.content_hash == before.content_hash
        assert store.authoring.get_stage_head(store.manifest.project_id, StageName.STORYBOARD).revision == 0


def _package():
    choice = {"choiceId": "turn", "sectionId": "opening", "prompt": "怎么办？", "outcomes": [{"outcomeId": "a", "label": "赴约"}, {"outcomeId": "b", "label": "回家"}]}
    script = {"sectionBindings": [{"episode": 1, "sectionId": "opening"}], "episodes": [{"ep": 1, "scenes": [{"flow": [
        {"action": "停步。抬眼。"}, {"action": "留在门廊。显示怎么办？赴约或回家。"},
        {"action": "输入今晚不去了，明天见。"}, {"action": "发送，保留已发文字，不出现新回信。"},
        {"line": "你好。", "speaker": "C01"},
    ]}]}]}
    board = {"episodes": [{"ep": 1, "segments": [{"sceneIndex": 1, "cuts": [{"frame": "门廊画面。预留选择区域。"}]}]}]}
    return prepare_presentation(inputs={"scriptRevision": 3}, script=script, storyboard=board, mapping={"choice": choice})


def _updates(pkg):
    result = []
    for source in pkg.sources:
        text = source.source_text
        if source.kind == "dialogue":
            spans = [{"start": 0, "end": len(text), "role": "dialogue"}]
        elif "显示" in text:
            cut = text.index("显示")
            spans = [{"start": 0, "end": cut, "role": "physical", "rendering": text[:cut]}, {"start": cut, "end": len(text), "role": "runtime_choice", "reason": "Exact frozen author choice belongs to player"}]
        elif "预留" in text:
            cut = text.index("预留")
            spans = [{"start": 0, "end": cut, "role": "physical", "rendering": text[:cut]}, {"start": cut, "end": len(text), "role": "review_only", "reason": "Runtime choices do not require generated UI"}]
        elif "今晚" in text:
            cut = text.index("今晚")
            spans = [{"start": 0, "end": cut, "role": "physical", "rendering": "在手机上输入完整回复。"}, {"start": cut, "end": len(text), "role": "visible_text"}]
        else:
            spans = [{"start": 0, "end": len(text), "role": "physical", "rendering": text}]
        result.append({"id": source.id, "spans": spans})
    return result


def _request(pkg, entries):
    return ProductionPresentationUpdateRequest(expected_proposal_revision=1, expected_content_hash="a"*64, source_hash=pkg.source_hash, reviewed_complete=True, entries=entries)


def test_complete_review_preserves_order_text_constraints_and_runtime_separation():
    pkg = _package(); reviewed = review_presentation(pkg, _request(pkg, _updates(pkg)))
    raw = {"sceneBeats": {"beats": [{"id": source.target_id} for source in pkg.sources if source.kind != "composition"]}, "storyboard": {
        "shots": [{"id": "opening-s1-c1"}], "shotBeatLinks": [{"shotId": "opening-s1-c1", "beatId": f"opening-s1-b{i}"} for i in range(1, 6)]}}
    projected = project_presentation(raw, reviewed)
    shot = projected["storyboard"]["shots"][0]
    assert shot["action"].startswith("停步。抬眼。\n留在门廊。")
    assert "发送，保留已发文字，不出现新回信。" in shot["action"]
    assert "怎么办" not in str(shot) and "预留" not in str(shot)
    assert shot["visibleTexts"][0]["text"] == "今晚不去了，明天见。"
    assert "你好。" not in shot["action"]
    assert reviewed.runtime_choice == pkg.runtime_choice
    assert reviewed.frozen_evidence == pkg.frozen_evidence
    assert [source.source_hash for source in reviewed.sources] == [source.source_hash for source in pkg.sources]


@pytest.mark.parametrize("mutation", ["omitted", "duplicate", "gap", "overlap", "unassigned", "rewrite_visible", "dialogue_action", "hash"])
def test_review_refuses_incomplete_or_wrong_authority(mutation):
    pkg = _package(); entries = _updates(pkg); request = _request(pkg, entries)
    if mutation == "omitted": request.entries.pop()
    elif mutation == "duplicate": request.entries.append(request.entries[0])
    elif mutation == "gap": request.entries[0].spans[0].start = 1
    elif mutation == "overlap": request.entries[1].spans[1].start -= 1
    elif mutation == "unassigned": request.entries[0].spans[0].role = "unassigned"
    elif mutation == "rewrite_visible": request.entries[2].spans[1].rendering = "different words"
    elif mutation == "dialogue_action": request.entries[4].spans[0].role = "physical"
    elif mutation == "hash": request.source_hash = "b"*64
    with pytest.raises(ValueError): review_presentation(pkg, request)


def test_media_context_does_not_reactivate_narrative_ui_prose(tmp_path: Path):
    from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
    from plotloom.persistence.project.media_image_currentness import ImageJobCurrentness
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        proposal = _prepare_installable_bridge(store)
        store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
        project_id = store.manifest.project_id
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        bible = store.authoring.get_stage_payload(project_id, StageName.STORY_BIBLE)
        beats = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
        beats = beats.model_copy(update={
            "scenes": [scene.model_copy(update={"objective": "RAW_RUNTIME_QUESTION"}) for scene in beats.scenes],
            "beats": [beat.model_copy(update={"description": "RAW_RUNTIME_QUESTION", "purpose": "RAW_RUNTIME_QUESTION", "visible_event": "Stop then gaze toward the junction."}) for beat in beats.beats],
        })
        context = ImageJobCurrentness.image_job_resolved_context(shot=board.shots[0], storyboard=board, story_bible=bible, scene_beats=beats)
        assert "RAW_RUNTIME_QUESTION" not in str(context)
        assert "Stop then gaze toward the junction." in str(context)


def test_fractional_source_installs_exact_sums_and_accepted_cut_lineage(tmp_path: Path):
    from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
    from plotloom.persistence.project.media_video_source import VideoSourceTiming
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        proposal = _prepare_installable_bridge(store, seconds=2.5)
        store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
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
            frozen = timing.binding_in_session(session, project_id, board.shots[0].id, 2500)
            assert frozen["cut"]["seconds"] == 2.5 and frozen["durationUnits"] == 2500
            assert timing.binding_is_current(session, project_id, board.shots[0].id, 2500, frozen)
            with pytest.raises(InvalidTransitionError, match="differs"):
                timing.binding_in_session(session, project_id, board.shots[0].id, 2000)


def test_dialogue_only_cut_keeps_spoken_words_exclusively_cue_owned():
    package = _package()
    reviewed = review_presentation(package, _request(package, _updates(package)))
    payload = {"sceneBeats": {"beats": [{"id": "opening-s1-b5"}], "dialogueCues": [{"id": "cue", "text": "你好。"}]},
        "storyboard": {"shots": [{"id": "opening-s1-c1"}], "shotBeatLinks": [{"shotId": "opening-s1-c1", "beatId": "opening-s1-b5"}]}}
    result = project_presentation(payload, reviewed)
    assert result["storyboard"]["shots"][0]["action"] == ""
    assert result["sceneBeats"]["dialogueCues"] == payload["sceneBeats"]["dialogueCues"]


def test_raw_f5_accepts_submillisecond_time_but_production_conflicts_explicitly(tmp_path: Path):
    from tests.test_production_bridge import _source_shaped_review_board
    from tests.test_project_storage_art import _accepted_f4_script
    from tests.test_project_storage_art import _deliver_stage
    from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "e" * 32)
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", _source_shaped_review_board(2.5001), "submillisecond"))
        accepted = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        assert accepted.status == "accepted"
        proposal = store.prepare_production_bridge().proposal
        assert proposal is not None and not proposal.installable
        assert any(conflict.code == "cut_duration_invalid" for conflict in proposal.conflicts)


def test_fresh_prepare_retains_the_accepted_longer_cut_review_policy(tmp_path: Path):
    from tests.test_production_bridge import _source_shaped_review_board
    from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage
    from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "f" * 32, max_cut_seconds=12)
        board = _source_shaped_review_board()
        board["params"]["maxCutSeconds"] = 12
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "longer-policy"))
        accepted = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        assert accepted.accepted_review.binding.review_max_cut_seconds == 12
        assert store.prepare_production_bridge().proposal is not None
        assert store.storyboard_review_state().accepted_review.binding.review_max_cut_seconds == 12


@pytest.mark.parametrize("words", ["  今晚不去了，明天见。  ", "\t我还在老地方。\n"])
def test_exact_visible_span_survives_projection_canonical_serialization_and_media_prompt(tmp_path: Path, words: str):
    import json
    from plotloom.canonical_schema import ShotV2
    from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
    from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
    from tests.test_h3_i2va_prompt import _review
    package = _package()
    evidence = deepcopy(package.frozen_evidence)
    evidence["script"]["episodes"][0]["scenes"][0]["flow"][2] = {"action": words}
    package = prepare_presentation(inputs=evidence["inputs"], script=evidence["script"], storyboard=evidence["storyboard"], mapping=evidence["sectionMap"])
    entries = _updates(package)
    entries[2]["spans"] = [{"start": 0, "end": len(words), "role": "visible_text"}]
    reviewed = review_presentation(package, _request(package, entries))
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        proposal = _prepare_installable_bridge(store)
        store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
        canonical_shot = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORYBOARD).shots[0].model_dump(mode="json", by_alias=True)
    canonical_shot["id"] = "opening-s1-c1"
    payload = {"sceneBeats": {"beats": [{"id": "opening-s1-b3"}]}, "storyboard": {"shots": [canonical_shot], "shotBeatLinks": [{"shotId": "opening-s1-c1", "beatId": "opening-s1-b3"}]}}
    projected = project_presentation(payload, reviewed)
    shot = ShotV2.model_validate(projected["storyboard"]["shots"][0]).model_dump(mode="json", by_alias=True)
    assert shot["visibleTexts"][0]["text"] == words
    snapshot = {"shot": shot, "resolvedContext": {"characters": [], "dialogueCues": []}}
    prompt = compile_i2va_prompt(snapshot, _review(snapshot))
    assert json.dumps(words, ensure_ascii=False) in prompt
    assert "<d>" not in prompt
    assert shot["visibleTexts"][0]["sourceContentHash"] == package.sources[2].source_hash


@pytest.mark.parametrize("words", ["", "  ", "\t\n", "\u3000"])
def test_authored_visible_text_rejects_whitespace_only_without_normalizing(words):
    from plotloom.canonical_schema import AuthoredVisibleText
    with pytest.raises(ValueError):
        AuthoredVisibleText.model_validate({"text": words, "sourceCoordinates": {}, "sourceContentHash": "a"*64})
