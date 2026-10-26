"""Raw receiving keeps decimal precision; production owns integer-ms admission."""
import subprocess
from copy import deepcopy

import pytest

from plotloom.creative_handoff_identity import canonical_json
from plotloom.persistence.project.storyboard_review import (
    ProjectStoryboardReviewPersistence,
)
from plotloom.production_dialogue_timing import freeze_f5_dialogue_timing
from tests.f5_dialogue_timing_fixtures import f5_script_seeds as f5_script_seeds
from tests.test_f5_dialogue_timing import ROOT, invoke, narrated_board
from tests.test_f5_dialogue_timing import prepared as prepared_fixture

prepared = prepared_fixture


@pytest.mark.parametrize("prepared", ["realistic", "brief"], indirect=True)
@pytest.mark.parametrize("seconds,valid", [(7.9199, False), (7.92, True), (7.9201, True)])
def test_both_real_receiving_routes_preserve_exact_raw_minimum(prepared, tmp_path, seconds, valid):
    _storage, _store, candidate, frozen = prepared
    style = "brief" if candidate.binding.storyboard_render_contract else "realistic"
    board = narrated_board(seconds, style=style)
    inputs = frozen.input_artifacts
    for render in (False, True):
        result = invoke(tmp_path, frozen, board, render=render)
        assert (result.returncode == 0) is valid, result.stderr.decode()
        if not valid:
            assert b"Canonical dialogue minima" in result.stderr
    args = (board, candidate.binding, inputs["script.json"], inputs["outline.json"], inputs["cast.json"], frozen)
    if valid:
        ProjectStoryboardReviewPersistence._validate(*args)
    else:
        with pytest.raises(ValueError, match="Canonical dialogue minima"):
            ProjectStoryboardReviewPersistence._validate(*args)


def receiving_inputs():
    script = {"episodes": [{"ep": ep, "scenes": [{"flow": []}]} for ep in (1, 2, 3)]}
    timing = freeze_f5_dialogue_timing(script, script_content_hash="a" * 64, language="zh-CN")
    params = {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}
    admission = {
        "scriptRevision": 1, "scriptContentHash": "a" * 64,
        "sectionBindings": [{"episode": ep, "sectionId": name} for ep, name in enumerate(("start", "a", "b"), 1)],
        "completeRouteSectionIds": [["start", "decision", "a"], ["start", "decision", "b"]],
        "routeOnlySectionIds": ["decision"], "targetPlaythroughSeconds": 5, "reviewTiming": params,
    }
    request = {"stage": "storyboard", "source": {"acceptedScriptRevision": 1, "acceptedScriptContentHash": "a" * 64},
               "inputArtifacts": {"script.json": script, "storyboard-admission.json": admission,
                                  "dialogue-timing-contract.json": timing.model_dump(mode="json", by_alias=True)}}
    board = {"params": params, "episodes": [{"ep": ep, "segments": [{"sceneIndex": 1,
             "cuts": [{"seconds": seconds, "beats": [1, 1]}]}]} for ep, seconds in enumerate((2.5001, 2.4999, 2), 1)]}
    return board, request


def receiving_result(tmp_path, board, request, *, nonfinite=""):
    path = tmp_path / "receiving.json"
    path.write_bytes(canonical_json({"board": board, "request": request}))
    program = "import {validateF5ReceivingTiming} from './scripts/storyboard-dialogue-timing.mjs'; import {readFileSync} from 'node:fs'; const {board,request}=JSON.parse(readFileSync(process.argv[1],'utf8')); if(process.argv[2]) board.episodes[0].segments[0].cuts[0].seconds=Number(process.argv[2]); validateF5ReceivingTiming(board,request);"
    return subprocess.run(["node", "--input-type=module", "--eval", program, str(path), nonfinite], cwd=ROOT, capture_output=True, check=False)


@pytest.mark.parametrize("ending,valid", [(2.4998, True), (2.4999, True), (2.4999001, False), (2.499900000000001, False)])
def test_exact_shared_prefix_routes_do_not_floor_fractional_milliseconds(tmp_path, ending, valid):
    board, request = receiving_inputs()
    board["episodes"][1]["segments"][0]["cuts"][0]["seconds"] = ending
    result = receiving_result(tmp_path, board, request)
    assert (result.returncode == 0) is valid, result.stderr.decode()
    if not valid:
        assert b"Complete storyboard route exceeds" in result.stderr


@pytest.mark.parametrize("seconds", [True, "2.5", None, 0, -2, 9007199254740992])
def test_raw_receiving_rejects_invalid_or_unsafe_duration(tmp_path, seconds):
    board, request = receiving_inputs()
    board["episodes"][0]["segments"][0]["cuts"][0]["seconds"] = seconds
    result = receiving_result(tmp_path, board, request)
    assert result.returncode != 0 and b"Source cut seconds" in result.stderr


@pytest.mark.parametrize("ceiling", [True, "5", None, 0, -5, 9007199254740992])
def test_raw_receiving_rejects_invalid_or_unsafe_ceiling(tmp_path, ceiling):
    board, request = receiving_inputs()
    request["inputArtifacts"]["storyboard-admission.json"]["targetPlaythroughSeconds"] = ceiling
    result = receiving_result(tmp_path, board, request)
    assert result.returncode != 0 and b"Author playthrough maximum" in result.stderr


@pytest.mark.parametrize("ceiling,valid", [(21000000000000, True), (20000000000000, False)])
def test_exact_different_scales_and_exponents_have_no_accumulated_integer_cap(tmp_path, ceiling, valid):
    board, request = receiving_inputs()
    request["inputArtifacts"]["storyboard-admission.json"]["targetPlaythroughSeconds"] = ceiling
    # This isolated arithmetic stress case must still obey its own frozen caps.
    limits = {"minCutSeconds": 2.5e-7, "maxCutSeconds": 5000000000000,
              "maxSegmentSeconds": 10000000000001}
    board["params"] = limits
    request["inputArtifacts"]["storyboard-admission.json"]["reviewTiming"] = limits
    for episode in board["episodes"]:
        episode["segments"][0]["cuts"] = [{"seconds": 5000000000000, "beats": [1, 1]},
                                           {"seconds": 5000000000000, "beats": [1, 1]},
                                           {"seconds": 2.5e-7, "beats": [1, 1]}]
    result = receiving_result(tmp_path, board, request)
    assert (result.returncode == 0) is valid, result.stderr.decode()
    if not valid:
        assert b"Complete storyboard route exceeds" in result.stderr


@pytest.mark.parametrize("nonfinite", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_raw_numbers_fail_at_the_receiving_boundary(tmp_path, nonfinite):
    board, request = receiving_inputs()
    result = receiving_result(tmp_path, board, request, nonfinite=nonfinite)
    assert result.returncode != 0 and b"Source cut seconds" in result.stderr


@pytest.mark.parametrize("seconds,valid", [(7.9199, False), (7.92, True), (7.9201, True)])
def test_multiline_minimum_uses_exact_sum_before_fractional_comparison(tmp_path, seconds, valid):
    board, request = receiving_inputs()
    script = request["inputArtifacts"]["script.json"]
    script["episodes"][0]["scenes"][0]["flow"] = [{"line": "字" * 12}, {"line": "词" * 12}]
    request["inputArtifacts"]["dialogue-timing-contract.json"] = freeze_f5_dialogue_timing(
        script, script_content_hash="a" * 64, language="zh-CN").model_dump(mode="json", by_alias=True)
    request["inputArtifacts"]["storyboard-admission.json"]["targetPlaythroughSeconds"] = 11
    board["episodes"][0]["segments"][0]["cuts"][0].update(seconds=seconds, beats=[1, 2])
    result = receiving_result(tmp_path, board, request)
    assert (result.returncode == 0) is valid, result.stderr.decode()
    if not valid:
        assert b"Canonical dialogue minima" in result.stderr


@pytest.mark.parametrize("minimum", [0, -1, True, 9007199254740992])
def test_unsafe_or_nonpositive_minimum_is_refused_even_with_matching_hash(tmp_path, minimum):
    from hashlib import sha256
    board, request = receiving_inputs()
    script = request["inputArtifacts"]["script.json"]
    script["episodes"][0]["scenes"][0]["flow"] = [{"line": "字"}]
    timing = freeze_f5_dialogue_timing(script, script_content_hash="a" * 64, language="zh-CN").model_dump(mode="json", by_alias=True)
    timing["lines"][0]["minimumDurationUnits"] = minimum
    payload = deepcopy(timing)
    payload.pop("contentHash")
    timing["contentHash"] = sha256(canonical_json(payload)).hexdigest()
    request["inputArtifacts"]["dialogue-timing-contract.json"] = timing
    result = receiving_result(tmp_path, board, request)
    assert result.returncode != 0 and b"minimum/pace is invalid" in result.stderr
