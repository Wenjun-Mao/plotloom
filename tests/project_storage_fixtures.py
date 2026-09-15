"""Legacy-free deterministic text fixtures for direct project-folder tests."""

from __future__ import annotations

import json
from typing import Any

from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse, ProviderUsage
from plotloom.provider_profiles import TextProviderProfileSnapshotV3


def fixture_profile(*, max_semantic_corrections: int = 2) -> TextProviderProfileSnapshotV3:
    values = {
        "profileId": "offline_fixture", "profileVersion": 1,
        "textProvider": "fixture-provider", "textBaseUrl": "http://127.0.0.1:9/v1",
        "textModel": "fixture-model", "textAuthMode": "none",
        "textCapabilities": {"jsonSchema": True}, "textContextWindowTokens": 32768,
        "textMaxOutputTokens": 8192, "textAttemptTimeoutSeconds": 300,
        "stageMaxOutputTokens": {
            "storyBible": 8192, "storyGraph": 8192, "sceneBeats": 4096, "storyboard": 4096,
        },
        "profileSchemaVersion": 3, "adapterId": "openai_compatible", "adapterVersion": "1",
        "maxSemanticCorrections": max_semantic_corrections,
        "presetId": "custom" if max_semantic_corrections == 0 else "compatible_v1",
        "profileHash": "",
    }
    return TextProviderProfileSnapshotV3.model_validate(values)


def _json_after(content: str, marker: str) -> Any:
    decoder = json.JSONDecoder()
    offset = 0
    while (index := content.find(marker, offset)) != -1:
        try:
            return decoder.raw_decode(content[index + len(marker):].lstrip())[0]
        except json.JSONDecodeError:
            offset = index + len(marker)
    raise AssertionError(f"no JSON value follows marker {marker!r}")


class FixtureProvider:
    """Offline project-folder provider with no retained repository fixture."""

    name = "fixture-provider"
    capabilities = ProviderCapabilities(json_schema=True)

    def generate(self, request: Any, secret: object | None) -> ProviderResponse:
        assert secret is None
        prompt = "\n".join(message.content for message in request.messages)
        state = {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}
        if "【不可变图骨架清单】" in prompt:
            topology = _json_after(prompt, "【不可变图骨架清单】")
            payload = {
                "nodes": [{"id": node["id"], "title": "固定节点", "summary": "角色继续前行。"} for node in topology["nodes"]],
                "edges": [{"id": edge["id"], "choiceText": "继续" if edge["kind"] == "choice" else None, "stateEffects": {"route": edge["id"]} if edge["kind"] == "choice" else {}, "entityStateEffects": []} for edge in topology["edges"]],
                "joinContracts": [{"id": item["id"], "requiredStateKeys": [], "allowedDifferences": [], "reconciliation": "不同路线汇合。", "notes": ""} for item in topology["joinContracts"]],
            }
        elif "【目标故事节点】" in prompt:
            node = _json_after(prompt, "【目标故事节点】")
            scene_id, beat_id = f"scene-{node['id']}", f"beat-{node['id']}"
            payload = {
                "scenes": [{"localSceneId": scene_id, "order": 1, "title": node["title"], "objective": "推进叙事", "locationId": None, "characterIds": [], "durationWeight": 1, "entryState": state, "exitState": state}],
                "beats": [{"localBeatId": beat_id, "sceneLocalId": scene_id, "order": 1, "description": "角色在雪中前行。", "purpose": "推进叙事", "visibleEvent": "角色握紧信件。", "immediateResult": "角色继续前行。", "dramaticChange": "继续前行", "entryState": state, "exitState": state, "continuityAnchors": [], "continuityDelta": {}}],
                "dialogueCues": [],
            }
        elif "【目标戏剧场景】" in prompt:
            scene = _json_after(prompt, "【目标戏剧场景】")
            beats = _json_after(prompt, "【该场景节拍】")
            beat_id = beats[0]["id"]
            payload = {
                "shots": [{"localShotId": f"shot-{scene['id']}", "order": 1, "title": "信件特写", "shotSize": "medium", "durationUnits": 1, "cameraAngle": "", "cameraMovement": "", "composition": "", "visualIntent": "交代选择", "motionIntent": "稳定推进", "action": "角色握紧信件。", "transition": "硬切", "cueIds": [], "audioPlan": {"events": []}, "characterIds": [], "locationId": None, "propIds": [], "requiredEntityStates": [], "entryState": state, "exitState": state}],
                "primaryShotLocalIdByBeat": {beat_id: f"shot-{scene['id']}"}, "supportingBeatLinks": [],
            }
        else:
            payload = {"logline": "角色做出选择。", "premise": "一封信改变当下。", "genre": "", "tone": "", "audience": "", "narrativePromise": "", "visualLanguage": "", "themes": [], "worldRules": [], "knownFacts": [], "openQuestions": [], "sourceNotes": [], "characters": [], "locations": [], "props": []}
        content = json.dumps(payload, ensure_ascii=False)
        return ProviderResponse(
            provider=self.name, model=request.model,
            raw={"choices": [{"message": {"role": "assistant", "content": content}}]},
            usage=ProviderUsage(input_tokens=7, output_tokens=11),
        )


class FixtureResolver:
    def __init__(self) -> None:
        self.provider = FixtureProvider()

    def resolve(self, provider_snapshot: dict[str, object]) -> tuple[FixtureProvider, str]:
        return self.provider, str(provider_snapshot["textModel"])
