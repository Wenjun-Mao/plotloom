"""Normal creator review is actionable prose; technical evidence stays exact."""
from copy import deepcopy
from html.parser import HTMLParser

import pytest

from plotloom import canonical_schema as dto
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.language_policy import language_contract
from plotloom.production_brief import assert_adaptable, production_brief
from plotloom.production_brief_display import SHAPES, TECHNICAL
from plotloom.video_backends.minimax_h3.directions import direction_sources
from plotloom.video_directions_contract import bind_draft, bind_fidelity, render_report
from tests.video_fidelity_fixtures import fidelity_for


def snapshot_for(locale):
    en = locale == "en-US"
    def words(zh, english): return english if en else zh
    state = {"facts": {"door_open": False, "requirement": {"hands": ["left", "right"]}},
        "entityStates": [{"entityType": "prop", "entityId": "P01", "state": words("仍未寄出", "Still unsent")}],
        "screenDirection": words("面向左侧", "Faces left"), "lighting": words("柔和晨光", "Soft morning light"),
        "sound": words("远处雨声", "Distant rain"), "notes": [words("不要打开门", "Do not open the door")]}
    shot = {"id": "SH01", "sceneId": "S01", "order": 1, "title": words("信件", "The letter"),
        "shotSize": "medium", "durationUnits": 5000, "cameraAngle": words("平视", "Eye level"),
        "cameraMovement": words("保持固定", "Hold still"), "composition": words("门左侧的人物", "A person left of the door"),
        "visualIntent": words("清晰可见的信封", "Clearly visible envelope"), "motionIntent": words("缓慢抬手", "Slowly raise one hand"),
        "action": words("人物不打开门，只抬起信封。", "The person does not open the door and only raises the envelope."),
        "visibleTexts": [{"text": "NO ENTRY / 请勿进入", "sourceCoordinates": {"shot": 1}, "sourceContentHash": "a"*64}],
        "transition": words("硬切", "Hard cut"), "cueIds": ["D01"], "characterIds": ["C01"], "locationId": "L01", "propIds": ["P01"],
        "requiredEntityStates": state["entityStates"], "entryState": state, "exitState": state,
        "audioPlan": {"events": [{"id": "A01", "kind": "sound_effect", "description": words("衣袖轻响", "A sleeve rustles"), "startOffsetUnits": 1000, "durationUnits": 2000}]}}
    entity = {"id": "C01", "name": "Ada", "description": words("穿蓝色外套的人", "A person in a blue coat"),
        "visualAnchors": [words("蓝色外套", "Blue coat")], "soundAnchors": [], "allowedStates": [], "continuityRules": []}
    context = {"scene": {"id": "S01", "storyNodeId": "N01", "order": 1, "title": shot["title"], "locationId": "L01",
        "characterIds": ["C01"], "beatIds": ["B01"], "durationBudgetUnits": 5000, "entryState": state, "exitState": state},
        "beats": [{"id": "B01", "sceneId": "S01", "order": 1, "visibleEvent": shot["action"], "entryState": state, "exitState": state}],
        "dialogueCues": [{"id": "D01", "beatId": "B01", "order": 1, "speakerId": "C01", "voiceOver": None,
            "text": words("Ada，等一下。", "Ada, wait."), "language": locale, "delivery": "natural", "performanceNotes": words("克制地说", "Speak with restraint"), "estimatedDurationUnits": 1000}],
        "characters": [entity | {"role": "lead", "goal": words("留下信件", "Leave the letter"), "traits": [], "voiceAnchors": [words("沉稳声线", "A steady voice")]}],
        "locations": [entity | {"id": "L01"}], "props": [entity | {"id": "P01"}], "requiredEntityStates": state["entityStates"]}
    return {"shot": shot, "resolvedContext": context, "languageContract": language_contract(locale),
        "shotPresentation": {"id": "presentation", "revision": 1, "sourceHash": "f"*64, "source": {"shot": shot},
            "review": {"messagePresentation": "popped_out_send", "reason": words("明确显示发送结果", "Clearly show the sent state"), "physical": {key: shot[key] for key in ("action", "composition", "visualIntent", "motionIntent", "cameraMovement")}, "literalSources": [{"shotId": "SH01", "index": 0}], "reviewed": True}, "effectiveShot": shot},
        "keyframe": {"assetId": "opening", "originalHash": "b"*64, "width": 576, "height": 1024,
            "intent": {"role": "shot_keyframe", "compositionIntent": shot["composition"], "sourceRefs": ["SH01"]}},
        "endFrame": {"revision": 1, "assetId": "ending", "originalHash": "c"*64, "width": 576, "height": 1024, "aspectPolicy": "contain_pad"},
        "identityLineage": [{"characterId": "C01", "referenceDecisionId": "ref", "referenceRevision": 1, "characterContextHash": "d"*64, "assets": [{"assetId": "face", "originalHash": "e"*64}]}],
        "samePersonReviewId": "review", "sourceTiming": {"kind": "canonical", "shotId": "SH01", "storyboardRevision": 1, "durationUnits": 5000}, "playbackIntent": "segment_required",
        "provider": {"provider": "minimax_h3_gateway", "model": "H3 quality 8", "adapterId": "minimax_h3_gateway", "adapterVersion": "v1", "capabilityVersion": 1, "costPolicy": "local_capacity_v1"},
        "request": {"durationSeconds": 8, "resolution": "576x1024", "audio": True, "aspectPolicy": "contain_pad", "seed": 17,
            "profileId": "H3 portrait", "profileVersion": 2, "width": 576, "height": 1024, "fps": 24, "frameCount": 192,
            "quality": 8, "allowLetterbox": True, "allowCenterCrop": False}}


def draft_request(snapshot):
    target = direction_sources(snapshot) | {"shotId": "SH01", "snapshot": snapshot}
    request = CreativeHandoffRequest(job_id="ch_" + "a"*32, project_id="project", section_id="section", stage="video-directions",
        expected_stage_revision=1, source={"operation": "draft"}, input_artifacts={"video-targets.json": {"targets": [target]},
            "language-contract.json": snapshot["languageContract"]}, creative_brief="Draft faithful directions.")
    draft = {"version": "video-directions.draft.v1", "targets": [{"shotId": "SH01", "sourceHash": target["sourceHash"],
        "fields": [{"path": source["path"], "english": "Preserve this exact authored physical requirement."} for source in target["sources"]]}]}
    return request, draft


class VisibleReview(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details = 0
        self.primary = []
    def handle_starttag(self, tag, attrs):
        if tag == "details": self.details += 1
        if not self.details: assert tag != "pre", "raw evidence cannot be the primary production brief"
    def handle_endtag(self, tag):
        if tag == "details": self.details -= 1
    def handle_data(self, data):
        if not self.details: self.primary.append(data)


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
def test_readable_projection_preserves_current_audience_effects_and_exact_literals(locale):
    snapshot = snapshot_for(locale)
    original = deepcopy(snapshot)
    brief = production_brief(snapshot)
    assert not brief["conflicts"], brief["conflicts"]
    assert brief["version"] == "plotloom.production-brief.v2"
    assert brief["displayVersion"] == "plotloom.production-brief-display.v1"
    items = [item for section in brief["sections"] for item in section["items"]]
    values = [item["value"] for item in items]
    for exact in (snapshot["shot"]["action"], snapshot["shot"]["visibleTexts"][0]["text"], snapshot["resolvedContext"]["dialogueCues"][0]["text"]):
        assert exact in values
    assert ("1 seconds" if locale == "en-US" else "1 秒") in values
    assert ("2 seconds" if locale == "en-US" else "2 秒") in values
    assert ("Gateway pads to retain the complete frame" if locale == "en-US" else "网关填边，保留完整画面") in values
    assert "MiniMax H3" in values and "Ada (C01)" in values
    assert snapshot == original
    request, draft = draft_request(snapshot)
    report = render_report(request, draft).decode()
    parser = VisibleReview()
    parser.feed(report)
    primary = " ".join(parser.primary)
    for machine_key in ("cameraMovement", "resolvedContext", "startOffsetUnits", "performanceNotes", "sourceHash", "aspectPolicy"):
        assert machine_key not in primary
        assert machine_key in report  # Full unmodified snapshot is technical evidence.
    assert ("Camera movement" if locale == "en-US" else "镜头运动") in primary
    assert ("not spoken" if locale == "en-US" else "不发声") in primary
    changed = deepcopy(snapshot)
    changed["request"]["seed"] += 1
    assert production_brief(changed)["briefHash"] != brief["briefHash"]


@pytest.mark.parametrize("path", ["shot.unknownCreativeRequirement", "resolvedContext.characters.0.newPerformance", "request.faceReplacement", "shotPresentation.review.newAudienceEffect"])
def test_unknown_requirements_conflict_at_exact_owner_before_adaptation(path):
    snapshot = snapshot_for("zh-CN")
    value = snapshot
    parts = path.split(".")
    for part in parts[:-1]: value = value[int(part)] if isinstance(value, list) else value[part]
    value[parts[-1]] = "Do not silently drop this requirement."
    conflict = next(item for item in production_brief(snapshot)["conflicts"] if item["path"] == path)
    assert conflict["owner"] and "所属来源" in conflict["message"]
    with pytest.raises(ValueError, match=parts[-1]): assert_adaptable(snapshot)


@pytest.mark.parametrize("model,shape", [(dto.ShotV2, "shot"), (dto.CharacterV2, "character"), (dto.ContinuityStateV2, "continuity"),
    (dto.DialogueCue, "cue"), (dto.AudioEvent, "event"), (dto.AuthoredVisibleText, "visible"), (dto.DramaticSceneV2, "scene")])
def test_active_dto_fields_have_explicit_readable_or_technical_ownership(model, shape):
    expected = {field.alias or name for name, field in model.model_fields.items()}
    assert expected <= set(SHAPES[shape].split()) | set(TECHNICAL.get(shape, "").split())


@pytest.mark.parametrize("path,valid", [("shot.action", True), ("resolvedContext.dialogueCues.0.text", True),
    ("directions.fields.0.english", True), ("compiledPrompt.overall_soundscape", True),
    ("shot.invented", False), ("resolvedContext.dialogueCues.9.text", False), ("directions.fields.999.english", False), ("compiledPrompt.invented", False)])
def test_finding_paths_resolve_exact_frozen_source_or_candidate_fields(path, valid):
    request, draft = draft_request(snapshot_for("en-US"))
    bound = bind_draft(request, draft)["SH01"]
    target = request.input_artifacts["video-targets.json"]["targets"][0] | bound
    check_request = request.model_copy(update={"source": {"operation": "fidelity-check"}, "input_artifacts": request.input_artifacts | {"video-targets.json": {"targets": [target]}}})
    result = fidelity_for(check_request, reject=True)
    result["targets"][0]["findings"][0]["path"] = path
    if valid:
        finding = bind_fidelity(check_request, result)["SH01"]["findings"][0]
        assert finding["sourceOwner"] and finding["sourcePath"]
    else:
        with pytest.raises(ValueError, match="finding path"): bind_fidelity(check_request, result)


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
def test_f5_provider_source_is_technical_while_voiceover_effect_is_readable(locale):
    snapshot = snapshot_for(locale)
    snapshot["sourceTiming"] |= {"kind": "f5_bridge", "cut": {"sectionId": "N01", "episode": 1, "sceneIndex": 1,
        "cutIndex": 1, "shotId": "SH01", "seconds": 5, "beats": ["B01"], "frame": "TECHNICAL ENGLISH IMAGE PROMPT",
        "h3Prompt": "TECHNICAL ENGLISH VIDEO PROMPT", "source": {"segmentIndex": 1}}}
    snapshot["resolvedContext"]["dialogueCues"][0].update({"speakerId": None, "voiceOver": "C01"})
    brief = production_brief(snapshot)
    assert not brief["conflicts"]
    values = [item["value"] for section in brief["sections"] for item in section["items"]]
    assert not any("TECHNICAL ENGLISH" in value for value in values)
    assert any(("lips completely closed" if locale == "en-US" else "双唇完全闭合") in value for value in values)
    assert brief["sections"][4]["content"]["sourceTiming"]["cut"]["frame"] == "TECHNICAL ENGLISH IMAGE PROMPT"
