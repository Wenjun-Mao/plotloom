"""Source requirements reach the complete final request without live submission."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.video_provider import VideoProviderError
from tests.h3_final_request_fixtures import authored_request, capture_request

pytestmark = pytest.mark.usefixtures("offline_media")
EXPECTED = Path(__file__).parent / "fixtures" / "h3-final-request.json"


def assert_authored_requirements(request):
    prompt = request["data"]["prompt"]
    picture, audio = prompt.split("Audio/dialogue: ", 1)
    assert "no captions, subtitles" in picture and "typography" in picture, "missing visual exclusion"
    assert "each dialogue cue only as speech in the audio track" in audio, "missing audio-only instruction"
    assert "Do not transcribe or translate dialogue into subtitles" in audio, "missing transcription exclusion"
    assert "Ada，等一下。" not in picture
    assert audio.count("Ada，等一下。") == 1 and "<d>[Chinese] Ada，等一下。</d>" in audio, "authored dialogue missing"
    assert "NO ENTRY / 请勿进入" in prompt, "authored lettering missing"
    assert "Only continuous quiet room tone besides the authored cue. No other voices or action sounds." in prompt
    assert "non_diegetic_music: No music." in prompt, "authored music prohibition missing"
    assert [f["field"] for f in request["files"]] == ["image", "endImage"], "required reference missing"


def test_complete_final_request_preserves_authored_requirements_and_reference_bytes():
    snapshot, prompt, images = authored_request()
    actual = capture_request(snapshot, prompt, images)
    assert_authored_requirements(actual)
    assert actual == json.loads(EXPECTED.read_text())
    assert [f["sha256"] for f in actual["files"]] == [
        snapshot["keyframe"]["originalHash"], snapshot["endFrame"]["originalHash"]]


@pytest.mark.parametrize("read_aloud", [False, True])
def test_picture_text_and_a_spoken_reading_have_independent_owners(read_aloud):
    from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
    from tests.test_h3_authored_soundtrack import package

    snapshot, _, images = authored_request()
    if read_aloud:
        literal = "出口"
        snapshot["resolvedContext"]["dialogueCues"][0]["text"] = literal
    else:
        literal = "明天见。"
        snapshot["resolvedContext"]["dialogueCues"] = []
        snapshot["shotPresentation"] = {"review": {"messagePresentation": "popped_out_draft"}}
    snapshot["shot"]["visibleTexts"][0]["text"] = literal
    _, candidate = package(snapshot)
    prompt = compile_i2va_prompt(snapshot, candidate, draft=True)
    sent = capture_request(snapshot, prompt, images)["data"]["prompt"]
    assert f'on its designated carrier: "{literal}".' in sent
    assert "no captions, subtitles" in sent
    if read_aloud:
        picture, speech = sent.split("Audio/dialogue: ")
        assert picture.count(literal) == speech.count(literal) == 1
        assert f"<d>[Chinese] {literal}</d>" in speech
        assert "Do not transcribe or translate dialogue into subtitles" in speech
    else:
        assert sent.count(literal) == 1 and "popped-out message preview" in sent
        assert "Audio/dialogue:" not in sent and "<d>" not in sent


def test_seed_only_change_has_exactly_one_intended_final_request_difference():
    snapshot, prompt, images = authored_request()
    before = capture_request(snapshot, prompt, images)
    revised = deepcopy(snapshot)
    revised["request"]["seed"] = 23
    after = capture_request(revised, prompt, images)
    assert after == before | {"data": before["data"] | {"seed": "23"}}
    assert_authored_requirements(after)


@pytest.mark.parametrize("omission", ["dialogue", "reference", "audio", "visual rule", "audio-only rule"])
def test_omission_controls_fail_the_same_authored_requirement_assertions(omission):
    actual = json.loads(EXPECTED.read_text())
    if omission == "reference":
        actual["files"].pop()
    else:
        text = {"dialogue": "Ada，等一下。", "audio": "non_diegetic_music: No music.",
            "visual rule": "no captions, subtitles", "audio-only rule": "each dialogue cue only as speech in the audio track"}[omission]
        actual["data"]["prompt"] = actual["data"]["prompt"].replace(text, "")
    with pytest.raises(AssertionError):
        assert_authored_requirements(actual)


def test_audio_cannot_be_disabled_to_satisfy_a_functional_request():
    snapshot, prompt, images = authored_request()
    snapshot["request"]["audio"] = False
    with pytest.raises(VideoProviderError, match="does not match its profile"):
        capture_request(snapshot, prompt, images)


@pytest.mark.parametrize("action", [
    (
        "人物只抬起信封，可以插入同一信封的近景，不要求连续完成动作。",
        "The person only raises the envelope. An insert of that same envelope is permitted; continuous execution of the action is not required.",
    ),
    (
        "人物只抬起信封，以一个连续固定机位长镜头完成，不允许插入或剪辑。",
        "The person only raises the envelope in one continuous static-camera shot, with no inserts or cuts.",
    ),
])
def test_final_request_shot_structure_remains_authored(action):
    snapshot, prompt, images = authored_request(action=action)
    original = deepcopy(snapshot)
    actual = capture_request(snapshot, prompt, images)
    final = actual["data"]["prompt"]
    assert action[1] in final
    assert final.count("one continuous") == action[1].count("one continuous")
    assert "at the end of this single shot" not in final
    assert_authored_requirements(actual)
    assert snapshot == original


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
def test_production_brief_does_not_override_authored_insert_permission(locale):
    from plotloom.production_brief import production_brief
    from tests.test_production_brief_display import snapshot_for

    snapshot = snapshot_for(locale)
    snapshot["shot"]["action"] = (
        "可以插入同一信封的近景，不要求连续完成动作。" if locale == "zh-CN"
        else "An insert of the same envelope is permitted; continuous action is not required."
    )
    original = deepcopy(snapshot)
    brief = production_brief(snapshot)
    constraints = " ".join(brief["adapterConstraints"])
    assert "one continuous shot" not in constraints
    assert "连续完成" not in constraints
    shot = next(section for section in brief["sections"] if section["id"] == "shot")
    assert any(item["value"] == snapshot["shot"]["action"] for item in shot["items"])
    assert snapshot == original
