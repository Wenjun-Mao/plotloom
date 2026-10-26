"""F5 receives canonical timing before Bridge installation."""
from __future__ import annotations

import json
import subprocess
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.authored_route_timing import route_budget_hash
from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.creative_handoff_identity import canonical_json
from plotloom.stage_contracts import StageName
from plotloom.persistence.project.storyboard_review import (
    ProjectStoryboardReviewPersistence,
)
from plotloom.persistence.schema.project_creative_handoff import (
    CreativeHandoffExecutionPinRow,
)
from plotloom.persistence.schema.project_storyboard_review import (
    StoryboardReviewCandidateRow,
)
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from plotloom.production_dialogue_timing import (
    TIMING_FILENAME,
    FrozenF5DialogueTiming,
    freeze_f5_dialogue_timing,
    projected_dialogue_timing,
)
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.f5_dialogue_timing_fixtures import (
    LINE,
    NOTES,
    open_f5_script_copy,
    variant_for,
)
from tests.f5_dialogue_timing_fixtures import f5_script_seeds as f5_script_seeds
from tests.production_bridge_fixtures import (
    _review_fixture_presentation,
    _source_shaped_review_board,
)
from tests.storyboard_brief_fixtures import brief_board

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("text,language,delivery,expected", [
    (LINE, "zh-CN", NOTES, 7920), (LINE, "zh-CN", "brisk", 6240),
    (LINE, "en", NOTES, 1440), ("  A 😀 B  ", "zh-CN", "natural", 1650),
    ("台 词。", "zh-CN", "measured", 1680), ("abc", "en-US", NOTES, 210),
])
def test_shared_projection_uses_spoken_language_pace_and_unicode(text, language, delivery, expected):
    value = {"speaker": "VO", "line": text, "delivery": delivery}
    result = projected_dialogue_timing(value, language)
    assert result["estimatedDurationUnits"] == expected
    assert result["performanceNotes"] == delivery
    script = {"lang": "en", "episodes": [{"ep": 1, "scenes": [{"flow": [value]}]}]}
    contract = freeze_f5_dialogue_timing(script, script_content_hash="a" * 64, language=language)
    assert contract.lines[0].minimum_duration_units == expected
    assert contract.lines[0].text_hash == sha256(text.encode()).hexdigest()
    assert contract.language == language
    assert contract.model_dump(mode="json", by_alias=True)["lines"][0]["delivery"] == result["delivery"]


@pytest.fixture
def prepared(tmp_path, request, f5_script_seeds):
    configuration = getattr(request, "param", "realistic")
    storage, store = open_f5_script_copy(tmp_path, f5_script_seeds[variant_for(configuration)])
    with closing(store):
        candidate, frozen = store.prepare_storyboard_review_candidate("ch_" + "t" * 32)
        yield storage, store, candidate, frozen


def narrated_board(seconds, *, style):
    board = _source_shaped_review_board(seconds=2.9)
    segment = board["episodes"][0]["segments"][0]
    for index, cut in enumerate(segment["cuts"]):
        cut["seconds"] = 2 if index < 3 else seconds
    alignment = "How the reference pictures align with the target video — " + "; ".join(
        f"Picture {index} (from Shot {index}) aligns with the {start:.2f}-second mark of the target video"
        for index, start in enumerate([0, 2, 4, 6], 1)) + "."
    shots = ["[Shot 1] Cinematic, live-action, cool gray palette. The empty room of <Picture 1> holds in a static shot."]
    for index, start in enumerate([2, 4, 6], 2):
        shots.append(f"[Shot {index}] At 00:{start:06.3f}, the camera cuts to <Picture {index}> and holds a static shot in the empty room.")
    shots[-1] += f" An off-screen narrator VO says <d>[Chinese] {LINE}</d>."
    segment["h3Prompt"] = alignment + "\n\nintegrated_multimodal_description:\n" + "\n".join(shots) + "\n\noverall_soundscape: Quiet wind.\n\nnon_diegetic_music: N/A"
    return brief_board(board, "direction") if style == "brief" else board


def invoke(tmp_path, frozen, board, *, render=False):
    request_path, board_path = tmp_path / "request.json", tmp_path / "board.json"
    request_path.write_bytes(canonical_json(frozen.model_dump(mode="json", by_alias=True)))
    board_path.write_bytes(canonical_json(board))
    saved = "storyboard-style-contract.json" in frozen.input_artifacts
    adapter = "brief-storyboard-style.mjs" if saved else "storyboard-receiving.mjs"
    return subprocess.run(["node", str(ROOT / "scripts" / adapter), "render" if render else "validate",
                           str(board_path), "--request", str(request_path)], capture_output=True, check=False)


@pytest.mark.parametrize("prepared", ["realistic", "brief"], indirect=True)
def test_fresh_prompt_plan_and_both_validators_refuse_upstream_only_fit(prepared, tmp_path):
    _storage, store, candidate, frozen = prepared
    saved = candidate.binding.storyboard_render_contract is not None
    adapter = "brief-storyboard-style.mjs" if saved else "storyboard-receiving.mjs"
    other = "storyboard-receiving.mjs" if saved else "brief-storyboard-style.mjs"
    assert TIMING_FILENAME in frozen.creative_brief and "sum of minima" in frozen.creative_brief
    assert f"scripts/{adapter}" in frozen.creative_brief and f"scripts/{other}" not in frozen.creative_brief
    plan = build_text_validation_plan(frozen, execution_pin=store.creative_handoff_execution_pin(frozen), source_revision="a" * 40)
    assert all(step.argv[0].endswith(adapter) for step in plan.steps)
    board = narrated_board(6.5, style="brief" if saved else "realistic")
    inputs = frozen.input_artifacts
    # Original upstream validation accepts these exact bytes. Receiving must
    # additionally reject them on the unchanged canonical minimum.
    program = "import {validateStoryboard,STYLE_PRESETS} from './third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs'; import {readFileSync} from 'node:fs'; STYLE_PRESETS['saved-brief']={phrase:'saved brief direction'}; let [b,r]=process.argv.slice(1).map(p=>JSON.parse(readFileSync(p,'utf8'))); let a=r.inputArtifacts; console.log(JSON.stringify(validateStoryboard(b,{script:a['script.json'],outline:a['outline.json'],cast:a['cast.json']})));"
    result = invoke(tmp_path, frozen, board)
    upstream = subprocess.run(["node", "--input-type=module", "--eval", program, str(tmp_path / "board.json"), str(tmp_path / "request.json")], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(upstream.stdout) == []
    assert result.returncode != 0 and b"Canonical dialogue minima" in result.stderr
    with pytest.raises(ValueError, match="Canonical dialogue minima"):
        ProjectStoryboardReviewPersistence._validate(board, candidate.binding, inputs["script.json"], inputs["outline.json"], inputs["cast.json"], frozen)


def adopt_rendered_board(store, candidate, frozen, board, tmp_path):
    rendered = invoke(tmp_path, frozen, board, render=True)
    assert rendered.returncode == 0, rendered.stderr.decode()
    exchange = store.creative_handoff_exchange()
    pin = store.creative_handoff_execution_pin(frozen)
    paths = exchange.write_package(frozen, pin)
    package, delivery = Path(paths["packagePath"]), Path(paths["deliveryPath"])
    delivery.mkdir()
    (delivery / "storyboard.json").write_bytes(canonical_json(board))
    (delivery / "report.html").write_bytes(rendered.stdout)
    manifest = json.loads((package / "completion-manifest.example.json").read_text())
    manifest["deliveryId"] = "prospective-timing-fixture"
    for kind, path in (("candidate", delivery / "storyboard.json"), ("report", delivery / "report.html")):
        manifest[kind]["sha256"] = sha256(path.read_bytes()).hexdigest()
    manifest["executorProvenance"]["codeRevision"] = "a" * 40
    manifest["limitations"] = ["provider-free prospective fixture; no retained evidence changed"]
    (delivery / "completion.json").write_text(json.dumps(manifest))
    ready = store.admit_storyboard_review_delivery(exchange.read_delivery(frozen, pin))
    store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))


def install_current_bridge(store):
    proposal = store.prepare_production_bridge(store.production_bridge_state().preparation.request).proposal
    proposal = _review_fixture_presentation(store, proposal)
    proposal = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
        expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
        entries=[{"id": item.id, "text": "作者确认的当前戏剧目的"} for item in proposal.intent_package.entries],
    )).proposal
    assert proposal.installable, proposal.conflicts
    store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))


@pytest.mark.parametrize("prepared", ["realistic", "brief"], indirect=True)
def test_distinct_prospective_schedule_installs_exact_canonical_vo_and_reopens(prepared, tmp_path):
    storage, store, candidate, frozen = prepared
    project_id = store.manifest.project_id
    source_before = deepcopy(store.script_state().accepted_script.script)
    board = narrated_board(7.92, style="brief" if candidate.binding.storyboard_render_contract else "realistic")
    adopt_rendered_board(store, candidate, frozen, board, tmp_path)
    install_current_bridge(store)
    plan = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
    installed = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    cue, = plan.dialogue_cues
    assert (cue.text, cue.performance_notes, cue.language, cue.delivery.value, cue.estimated_duration_units) == (LINE, NOTES, "zh-CN", "natural", 7920)
    assert cue.speaker_id is None and cue.voice_over == "VO"
    shot, = [item for item in installed.shots if cue.id in item.cue_ids]
    assert shot.duration_units == 7920 and cue.beat_id.endswith("-b4") and shot.order == 4
    assert store.script_state().accepted_script.script == source_before
    store.close()
    with closing(storage.projects.open(project_id)) as reopened:
        assert reopened.production_bridge_state().installation.status == "current"
        assert reopened.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS) == plan


@pytest.mark.parametrize("prepared", ["realistic", "brief"], indirect=True)
@pytest.mark.parametrize("mutation", ["missing", "minimum", "text", "language"])
def test_missing_or_drifted_contract_fails_both_receiving_boundaries(prepared, tmp_path, mutation):
    _storage, _store, candidate, frozen = prepared
    artifacts = deepcopy(frozen.input_artifacts)
    if mutation == "missing": del artifacts[TIMING_FILENAME]
    elif mutation == "minimum": artifacts[TIMING_FILENAME]["lines"][0]["minimumDurationUnits"] = 1
    elif mutation == "text": artifacts[TIMING_FILENAME]["lines"][0]["textHash"] = "0" * 64
    else: artifacts[TIMING_FILENAME]["language"] = "en"
    altered = frozen.model_copy(update={"input_artifacts": artifacts})
    with pytest.raises(ValueError, match="timing|content hash"):
        build_text_validation_plan(altered, execution_pin={
            "upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64,
        }, source_revision="a" * 40)
    board = narrated_board(7.92, style="brief" if candidate.binding.storyboard_render_contract else "realistic")
    result = invoke(tmp_path, altered, board)
    assert result.returncode != 0 and b"canonical dialogue timing" in result.stderr.lower()
    inputs = frozen.input_artifacts
    with pytest.raises(ValueError, match="canonical dialogue timing"):
        ProjectStoryboardReviewPersistence._validate(board, candidate.binding, inputs["script.json"], inputs["outline.json"], inputs["cast.json"], altered)
    if mutation != "missing":
        with pytest.raises(ValueError, match="content hash"):
            FrozenF5DialogueTiming.model_validate(artifacts[TIMING_FILENAME])


@pytest.mark.parametrize("prepared", [{"style": "realistic", "multi": True}], indirect=True)
def test_multiline_beat_range_uses_sum_and_exact_single_shot_ownership(prepared, tmp_path):
    _storage, store, candidate, frozen = prepared
    board = narrated_board(7.92, style="realistic")
    segment = board["episodes"][0]["segments"][0]
    segment["cuts"][3]["beats"] = [4, 5]
    segment["h3Prompt"] = segment["h3Prompt"].replace(
        f"<d>[Chinese] {LINE}</d>", f"<d>[Chinese] {LINE[:12]}</d> <d>[Chinese] {LINE[12:]}</d>")
    second = board["episodes"][0]["segments"][1]
    # Preserve five cuts while repartitioning the remaining action beats 6–10.
    for cut, beat in zip(second["cuts"], range(6, 11), strict=True):
        cut["beats"] = [beat, beat]
    result = invoke(tmp_path, frozen, board)
    assert result.returncode == 0, result.stderr.decode()
    assert [item.minimum_duration_units for item in candidate.binding.dialogue_timing_contract.lines] == [3960, 3960]
    segment["cuts"][3]["seconds"] = 7.919
    rejected = invoke(tmp_path, frozen, board)
    assert rejected.returncode != 0 and b"Canonical dialogue minima" in rejected.stderr
    segment["cuts"][3]["seconds"] = 7.92
    for beats in ([4, 4], [4, 6]):
        broken = deepcopy(board)
        broken["episodes"][0]["segments"][0]["cuts"][3]["beats"] = beats
        assert invoke(tmp_path, frozen, broken).returncode != 0
    adopt_rendered_board(store, candidate, frozen, board, tmp_path)
    install_current_bridge(store)
    cues = store.authoring.get_stage_payload(store.manifest.project_id, StageName.SCENE_BEATS).dialogue_cues
    assert [cue.text for cue in cues] == [LINE[:12], LINE[12:]]
    containing = [shot for shot in store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORYBOARD).shots if shot.cue_ids]
    assert len(containing) == 1 and containing[0].cue_ids == [cue.id for cue in cues]
    assert containing[0].duration_units == sum(cue.estimated_duration_units for cue in cues) == 7920


def test_impossible_line_refuses_fresh_preparation_without_creating_a_job(prepared):
    _storage, store, candidate, _frozen = prepared
    store.cancel_storyboard_review_candidate(candidate.job_id)
    before = store.storyboard_review_state()
    with pytest.raises(ValueError, match="cannot fit the chosen F5 maximum"):
        store.prepare_storyboard_review_candidate("ch_" + "u" * 32, max_cut_seconds=7)
    assert store.storyboard_review_state() == before
    with store.repository._read() as session:
        assert session.get(StoryboardReviewCandidateRow, "ch_" + "u" * 32) is None
        assert session.get(CreativeHandoffExecutionPinRow, "ch_" + "u" * 32) is None


@pytest.mark.parametrize("prepared", [
    {"style": "realistic", "dialogue": False}, {"style": "brief", "dialogue": False},
], indirect=True)
@pytest.mark.parametrize("seconds,bridge_conflict", [(2.5, False), (2.5001, True), (2.5000001, True)])
def test_action_only_raw_precision_admits_but_bridge_conversion_stays_strict(prepared, tmp_path, seconds, bridge_conflict):
    _storage, store, candidate, frozen = prepared
    assert frozen.input_artifacts[TIMING_FILENAME]["lines"] == []
    board = _source_shaped_review_board(seconds)
    if candidate.binding.storyboard_render_contract:
        board = brief_board(board, "direction")
    validated = invoke(tmp_path, frozen, board)
    assert validated.returncode == 0, validated.stderr.decode()
    adopt_rendered_board(store, candidate, frozen, board, tmp_path)
    accepted = store.storyboard_review_state().accepted_review
    assert accepted is not None and accepted.storyboard == board
    proposal = store.prepare_production_bridge(store.production_bridge_state().preparation.request).proposal
    assert proposal is not None
    assert any(conflict.code == "cut_duration_invalid" for conflict in proposal.conflicts) is bridge_conflict
    if bridge_conflict:
        assert not proposal.installable
    artifacts = deepcopy(frozen.input_artifacts)
    del artifacts[TIMING_FILENAME]
    missing = invoke(tmp_path, frozen.model_copy(update={"input_artifacts": artifacts}), board)
    assert missing.returncode != 0 and b"canonical dialogue timing" in missing.stderr.lower()


@pytest.mark.parametrize("prepared", ["realistic", "brief"], indirect=True)
@pytest.mark.parametrize("seconds,accepted", [
    (7.9199999, False), (7.919999999999999, False), (7.92, True),
    (7.920000000000001, True), (7.9200001, True),
])
def test_raw_precision_compares_exactly_against_canonical_minimum(prepared, tmp_path, seconds, accepted):
    _storage, _store, candidate, frozen = prepared
    board = narrated_board(seconds, style="brief" if candidate.binding.storyboard_render_contract else "realistic")
    for render in (False, True):
        result = invoke(tmp_path, frozen, board, render=render)
        if accepted:
            assert result.returncode == 0, result.stderr.decode()
        else:
            assert result.returncode != 0 and b"Canonical dialogue minima" in result.stderr


@pytest.mark.parametrize("prepared", [
    {"style": "realistic", "dialogue": False}, {"style": "brief", "dialogue": False},
], indirect=True)
@pytest.mark.parametrize("last_seconds,accepted", [(2.4999999, True), (2.5, True), (2.5000001, False)])
def test_mixed_decimal_route_sum_obeys_exact_ceiling(prepared, tmp_path, last_seconds, accepted):
    _storage, _store, candidate, frozen = prepared
    board = _source_shaped_review_board(2.5)
    # Each episode totals exactly 22.5 seconds. Either complete route is 45;
    # mutually exclusive endings must never be summed together.
    for episode in board["episodes"]:
        cuts = [cut for segment in episode["segments"] for cut in segment["cuts"]]
        for index, cut in enumerate(cuts[:-1]):
            cut["seconds"] = 2.5001 if index % 2 == 0 else 2.4999
    board["episodes"][1]["segments"][-1]["cuts"][-1]["seconds"] = last_seconds
    if candidate.binding.storyboard_render_contract:
        board = brief_board(board, "direction")
    artifacts = deepcopy(frozen.input_artifacts)
    admission = artifacts["storyboard-admission.json"]
    admission["targetPlaythroughSeconds"] = 45
    admission["routeBudgetHash"] = route_budget_hash(
        target_seconds=45, section_bindings=admission["sectionBindings"],
        routes=admission["completeRouteSectionIds"], route_only_ids=admission["routeOnlySectionIds"],
    )
    limited = frozen.model_copy(update={"input_artifacts": artifacts})
    for render in (False, True):
        result = invoke(tmp_path, limited, board, render=render)
        if accepted:
            assert result.returncode == 0, result.stderr.decode()
        else:
            assert result.returncode != 0 and b"Complete storyboard route exceeds" in result.stderr


@pytest.mark.parametrize("prepared", [
    {"style": "realistic", "dialogue": False}, {"style": "brief", "dialogue": False},
], indirect=True)
@pytest.mark.parametrize("seconds", [True, None, "2.5", 0, -1, float("nan"), float("inf"), -float("inf")])
def test_raw_precision_does_not_admit_invalid_source_seconds(prepared, tmp_path, seconds):
    _storage, _store, candidate, frozen = prepared
    board = _source_shaped_review_board(2.5)
    board["episodes"][0]["segments"][0]["cuts"][0]["seconds"] = seconds
    if candidate.binding.storyboard_render_contract:
        board = brief_board(board, "direction")
    result = invoke(tmp_path, frozen, board)
    assert result.returncode != 0


@pytest.mark.parametrize("prepared", [
    {"style": "realistic", "dialogue": False}, {"style": "brief", "dialogue": False},
], indirect=True)
@pytest.mark.parametrize("literal", ["2.5001e0", "25001e-4", "0.25001e+1"])
def test_raw_precision_accepts_supported_json_exponent_notation(prepared, tmp_path, literal):
    _storage, _store, candidate, frozen = prepared
    board = _source_shaped_review_board(2.5001)
    if candidate.binding.storyboard_render_contract:
        board = brief_board(board, "direction")
    baseline = invoke(tmp_path, frozen, board)
    assert baseline.returncode == 0, baseline.stderr.decode()
    path = tmp_path / "board.json"
    original = path.read_bytes()
    assert b'"seconds":2.5001' in original
    path.write_bytes(original.replace(b'"seconds":2.5001', f'"seconds":{literal}'.encode()))
    assert json.loads(path.read_bytes()) == board
    result = subprocess.run(baseline.args, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize("prepared", [
    {"style": "realistic", "dialogue": False}, {"style": "brief", "dialogue": False},
], indirect=True)
@pytest.mark.parametrize("boundary,seconds,accepted", [
    ("cut", 1.9999999, False), ("cut", 2, True), ("cut", 8, True), ("cut", 8.0000001, False),
    ("segment", 2.9999999, True), ("segment", 3, True), ("segment", 3.0000001, False),
])
def test_raw_precision_preserves_frozen_cut_and_segment_limits(prepared, tmp_path, boundary, seconds, accepted):
    _storage, _store, candidate, frozen = prepared
    board = _source_shaped_review_board(2.7 if boundary == "cut" else 3)
    if boundary == "cut":
        # Keep all episodes within the independent upstream 25-second target;
        # this segment can then exercise either 2- or 8-second cut admission.
        board["episodes"][0]["segments"][0] = _source_shaped_review_board(2)["episodes"][0]["segments"][0]
    segment = board["episodes"][0]["segments"][0 if boundary == "cut" else 1]
    segment["cuts"][-1]["seconds"] = seconds
    if candidate.binding.storyboard_render_contract:
        board = brief_board(board, "direction")
    for render in (False, True):
        result = invoke(tmp_path, frozen, board, render=render)
        assert (result.returncode == 0) is accepted, result.stderr.decode()
