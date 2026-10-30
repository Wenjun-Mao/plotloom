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
