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
    assert "Ada，等一下。" in prompt, "authored dialogue missing"
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


def test_seed_only_change_has_exactly_one_intended_final_request_difference():
    snapshot, prompt, images = authored_request()
    before = capture_request(snapshot, prompt, images)
    revised = deepcopy(snapshot)
    revised["request"]["seed"] = 23
    after = capture_request(revised, prompt, images)
    assert after == before | {"data": before["data"] | {"seed": "23"}}
    assert_authored_requirements(after)


@pytest.mark.parametrize("omission", ["dialogue", "reference", "audio"])
def test_omission_controls_fail_the_same_authored_requirement_assertions(omission):
    actual = json.loads(EXPECTED.read_text())
    if omission == "reference":
        actual["files"].pop()
    else:
        text = "Ada，等一下。" if omission == "dialogue" else "non_diegetic_music: No music."
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
