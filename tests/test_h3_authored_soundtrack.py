"""Authored prose sound survives visual-only presentation without inference."""
from copy import deepcopy
from hashlib import sha256

import pytest

from plotloom.video_backends.minimax_h3.authored_audio_sources import COMPILER_VERSION
from plotloom.video_backends.minimax_h3.directions import direction_sources
from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
from plotloom.video_directions_contract import bind_fidelity
from plotloom.video_fidelity_contracts import FidelityFinding
from plotloom.video_fidelity_paths import bind_finding_paths
from tests.test_production_brief_display import draft_request, snapshot_for
from tests.video_fidelity_fixtures import fidelity_for

ZH = "除指定对白外只有房间底噪，无旁白、配乐、字幕、招牌、按钮及其他新增画面文字。"


def source(composition=ZH):
    snapshot = snapshot_for("zh-CN")
    snapshot["compilerVersion"] = COMPILER_VERSION
    snapshot["shot"]["audioPlan"]["events"] = []
    snapshot["sourceTiming"] = {"kind": "f5_bridge", "cut": {
        "sectionId": "opening", "episode": 1, "sceneIndex": 1,
        "cutIndex": 1, "shotId": "SH01", "composition": composition,
        "h3Prompt": "Untrusted technical text: add a loud orchestra."}}
    return snapshot


def package(snapshot, sound="Only continuous quiet room tone besides the authored cue. No other voices or action sounds.", music="No music.", action_sound="N/A", action_music="N/A"):
    request, draft = draft_request(snapshot)
    target = draft["targets"][0]
    for field in target["fields"]:
        if field["path"] == "reviewedSoundscape": field["english"] = sound
        if field["path"] == "reviewedMusic": field["english"] = music
        if field["path"] == "reviewedActionSoundscape": field["english"] = action_sound
        if field["path"] == "reviewedActionMusic": field["english"] = action_music
    return request, target


def test_exact_authored_scalar_provenance_survives_empty_events_and_visual_projection():
    snapshot = source()
    original = deepcopy(snapshot)
    fields = {item["path"]: item for item in direction_sources(snapshot)["sources"]}
    for key in ("reviewedSoundscape", "reviewedMusic"):
        assert fields[key]["text"] == ZH
        assert fields[key]["sourceTextHash"] == sha256(ZH.encode()).hexdigest()
        assert fields[key]["sourcePath"] == "sourceTiming.cut.composition"
        assert fields[key]["sourceCoordinates"]["cutIndex"] == 1
        assert "orchestra" not in fields[key]["text"]
    _, target = package(snapshot)
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    assert "overall_soundscape: Only continuous quiet room tone" in prompt
    assert "non_diegetic_music: No music." in prompt
    assert "orchestra" not in prompt
    assert snapshot == original


def test_explicit_audio_events_do_not_hide_prose_restrictions_or_music():
    snapshot = source("房间底噪；配乐为持续低音弦乐，不加旁白。")
    snapshot["shot"]["audioPlan"]["events"] = [
        {"kind": "ambience", "description": "Rain", "startOffsetUnits": 0, "durationUnits": 1000},
        {"kind": "score", "description": "Strings", "startOffsetUnits": 0, "durationUnits": 1000}]
    _, target = package(snapshot, sound="Room tone. No narration.", music="Continuous low strings.")
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    sound, music = prompt.split("overall_soundscape: ")[1].split("non_diegetic_music: ")
    assert "From 0.000s to 1.000s" in sound and "Room tone. No narration." in sound
    assert "From 0.000s to 1.000s" in music and "Continuous low strings." in music


def test_no_sound_is_a_separate_checked_judgment_and_both_fields_are_required():
    snapshot = source("一人站在门旁。")
    _, target = package(snapshot, sound="N/A", music="N/A")
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    assert "overall_soundscape: N/A\n\nnon_diegetic_music: N/A" in prompt
    target["fields"] = [f for f in target["fields"] if f["path"] != "reviewedMusic"]
    with pytest.raises(ValueError, match="cover every"):
        compile_i2va_prompt(snapshot, target, draft=True)


def test_no_additional_prose_requirement_does_not_cancel_explicit_events():
    snapshot = source("一人站在门旁。")
    snapshot["shot"]["audioPlan"]["events"] = [
        {"kind": "ambience", "description": "Rain", "startOffsetUnits": 0, "durationUnits": 1000},
        {"kind": "score", "description": "Strings", "startOffsetUnits": 0, "durationUnits": 1000}]
    _, target = package(snapshot, sound="N/A", music="N/A")
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    sound, music = prompt.split("overall_soundscape: ")[1].split("non_diegetic_music: ")
    assert "From 0.000s to 1.000s" in sound and "N/A" not in sound
    assert "From 0.000s to 1.000s" in music and "N/A" not in music


@pytest.mark.parametrize("path", ["reviewedSoundscape", "reviewedMusic"])
def test_sound_conflict_findings_resolve_to_original_owner_and_bind_rejection(path):
    snapshot = source("只有房间底噪，无配乐。")
    request, target = package(snapshot, sound="Loud impacts.", music="An orchestra.")
    frozen = request.input_artifacts["video-targets.json"]["targets"][0]
    frozen["directions"] = {k: target[k] for k in ("sourceHash", "fields")}
    frozen["compiledPrompt"] = compile_i2va_prompt(snapshot, target, draft=True)
    request.source["operation"] = "fidelity-check"
    result = fidelity_for(request, reject=True)
    result["targets"][0]["findings"] = [{"path": path, "code": "sound_role", "message": "候选声音与作者限制冲突。"}]
    bound = bind_fidelity(request, result)["SH01"]
    assert bound["verdict"] == "reject"
    assert bound["findings"][0]["sourcePath"] == "sourceTiming.cut.composition"
    index = next(i for i,f in enumerate(target["fields"]) if f["path"] == path)
    findings = bind_finding_paths(snapshot, target, [FidelityFinding(
        path=f"directions.fields.{index}.english", code="omission", message="遗漏来源。")])
    assert findings[0]["sourcePath"] == "sourceTiming.cut.composition"


def test_retained_v7_source_and_fallback_stay_under_original_contract():
    snapshot = source()
    snapshot["compilerVersion"] = "plotloom.h3-production-brief.v7"
    fields = {item["path"]: item for item in direction_sources(snapshot)["sources"]}
    assert "reviewedMusic" not in fields
    assert fields["reviewedSoundscape"]["text"].startswith("No ambient or physical sound event is authored.")
    _, target = package(snapshot, sound="N/A")
    assert "overall_soundscape: N/A\n\nnon_diegetic_music: N/A" in compile_i2va_prompt(snapshot, target, draft=True)


def test_canonical_composition_uses_its_own_exact_source_coordinates():
    snapshot = snapshot_for("en-US")
    snapshot["compilerVersion"] = COMPILER_VERSION
    sources = direction_sources(snapshot)["sources"]
    sound = next(item for item in sources if item["path"] == "reviewedSoundscape")
    assert sound["text"] == snapshot["shot"]["composition"]
    assert sound["sourcePath"] == "shot.composition"


def test_english_action_owns_room_tone_and_no_music_when_composition_only_describes_speech():
    snapshot = source("Nora rests her hand beside the cup, says the source sentence once, then keeps her hand there through the end.")
    action = "Maintain one continuous static-camera live-action shot with quiet room ambience, no music, subtitles, signs or visible words beyond the cup marking."
    snapshot["shot"]["action"] = action
    sources = {item["path"]: item for item in direction_sources(snapshot)["sources"]}
    for path in ("reviewedActionSoundscape", "reviewedActionMusic"):
        assert sources[path]["text"] == action
        assert sources[path]["sourcePath"] == "shot.action"
        assert sources[path]["sourceTextHash"] == sha256(action.encode()).hexdigest()
    _, target = package(snapshot, sound="N/A", music="N/A",
        action_sound="Quiet room ambience.", action_music="No music.")
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    assert "overall_soundscape: Quiet room ambience.\n\nnon_diegetic_music: No music." in prompt
    finding = bind_finding_paths(snapshot, target, [FidelityFinding(
        path="reviewedActionSoundscape", code="sound_role", message="Preserve room ambience.")])[0]
    assert finding["sourcePath"] == "shot.action"


def test_conflicting_prose_owners_are_preserved_for_rejection_instead_of_prioritized():
    snapshot = source("只有房间底噪，无配乐。")
    snapshot["shot"]["action"] = "敲击声持续，弦乐不停。"
    _, target = package(snapshot, action_sound="Continuous knocking.", action_music="Continuous strings.")
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    assert "Only continuous quiet room tone" in prompt and "Continuous knocking." in prompt
    assert "non_diegetic_music: No music. Continuous strings." in prompt


def test_retained_v8_composition_sources_do_not_acquire_new_action_authority():
    snapshot = source()
    snapshot["compilerVersion"] = "plotloom.h3-production-brief.v8"
    paths = {item["path"] for item in direction_sources(snapshot)["sources"]}
    assert {"reviewedSoundscape", "reviewedMusic"} <= paths
    assert not paths & {"reviewedActionSoundscape", "reviewedActionMusic"}
    _, target = package(snapshot)
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    assert "overall_soundscape: Only continuous quiet room tone" in prompt
    assert "non_diegetic_music: No music." in prompt


@pytest.mark.parametrize("version", ["plotloom.h3-production-brief.v9", "plotloom.h3-production-brief.v10"])
def test_retained_action_sources_and_compiled_sound_bytes(version):
    snapshot = source()
    current_sources = direction_sources(snapshot)["sources"]
    _, current = package(snapshot)
    current_prompt = compile_i2va_prompt(snapshot, current, draft=True)
    snapshot["compilerVersion"] = version
    assert direction_sources(snapshot)["sources"] == current_sources
    _, retained = package(snapshot)
    assert compile_i2va_prompt(snapshot, retained, draft=True) == current_prompt
