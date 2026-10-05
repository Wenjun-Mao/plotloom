"""F5 review evidence to one explicitly accepted canonical V2 installation."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...canonical_schema import default_dialogue_timing_profile
from ...creative_handoff_exchange import canonical_json
from ...domain import ProjectBrief, StageName
from ...production_bridge_contracts import ProductionBridgeConflict, ProductionBridgeIntentEntry, ProductionBridgeIntentPackage
from ..schema.project_cast import CastRevisionRow
from ...production_timing import source_seconds_to_milliseconds


class ProductionBridgeProjection:
    """Deterministic source mapping; review and persistence stay separate."""

    @staticmethod
    def _state() -> dict[str, Any]:
        return {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}

    def _build(self, session: Any, project_id: str, *, inputs: dict[str, Any], storyboard: dict[str, Any], script: dict[str, Any], cast_and_art: dict[str, Any]) -> tuple[dict[str, Any], ProductionBridgeIntentPackage, list[ProductionBridgeConflict], list[ProductionBridgeConflict], list[dict[str, Any]], list[dict[str, Any]]]:
        project = self._access.rows.project(session, project_id)
        brief = ProjectBrief.model_validate(project.brief)
        graph = self._canonical._load_stage_payload(session, project_id, StageName.STORY_GRAPH)
        graph_nodes = {node.id: node for node in getattr(graph, "nodes", [])}
        cast, art = dict(cast_and_art), cast_and_art["__art__"]
        cast.pop("__art__", None)
        cast.pop("__section_map__", None)
        # Consumer mappings name the canonical V2 IDs; they do not select media.
        cast_owner = self._review._script._art._cast
        cast_head = cast_owner._head(session, project_id)
        cast_revision = session.scalar(select(CastRevisionRow).where(
            CastRevisionRow.project_id == project_id, CastRevisionRow.revision == cast_head.revision,
        )) if cast_head.revision else None
        mappings = {
            item.get("castCharacterId"): item.get("consumerCharacterId")
            for item in (cast_revision.consumer_mappings if cast_revision else [])
            if isinstance(item, dict) and isinstance(item.get("castCharacterId"), str) and isinstance(item.get("consumerCharacterId"), str)
        }
        characters = []
        for item in cast.get("characters", []):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            canonical_id = mappings.get(item["id"])
            if canonical_id is None:
                continue
            persona = item.get("persona") if isinstance(item.get("persona"), dict) else {}
            appearance = persona.get("appearance") if isinstance(persona.get("appearance"), str) else ""
            voice = (item.get("voice") or {}).get("timbre") if isinstance(item.get("voice"), dict) else None
            characters.append({"id": canonical_id, "name": item.get("name") if isinstance(item.get("name"), str) and item["name"].strip() else canonical_id, "description": appearance, "visualAnchors": [appearance] if appearance else [], "soundAnchors": [voice] if isinstance(voice, str) and voice.strip() else [], "allowedStates": [], "continuityRules": [], "role": None, "goal": persona.get("motivation") if isinstance(persona.get("motivation"), str) else "", "traits": [persona["arc"]] if isinstance(persona.get("arc"), str) and persona["arc"].strip() else [], "voiceAnchors": [voice] if isinstance(voice, str) and voice.strip() else []})
        def art_entity(item: dict[str, Any]) -> dict[str, Any]:
            anchors = [entry.get("desc") for entry in item.get("anchors", []) if isinstance(entry, dict) and isinstance(entry.get("desc"), str) and entry["desc"].strip()]
            states = [entry.get("state") for entry in item.get("lighting", []) if isinstance(entry, dict) and isinstance(entry.get("state"), str) and entry["state"].strip()]
            return {"id": item["id"], "name": item.get("name") if isinstance(item.get("name"), str) and item["name"].strip() else item["id"], "description": item.get("summary") if isinstance(item.get("summary"), str) else "", "visualAnchors": anchors, "soundAnchors": [], "allowedStates": states, "continuityRules": []}
        locations = [art_entity(item) for item in art.get("scenes", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
        props = [art_entity(item) for item in art.get("props", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
        bible = {"logline": brief.synopsis, "premise": brief.synopsis, "genre": brief.genre_direction or "", "tone": "", "audience": "", "narrativePromise": "", "visualLanguage": brief.visual_direction or "", "themes": [], "worldRules": [], "knownFacts": [], "openQuestions": [], "sourceNotes": ["F5 H3 prompt text is review evidence, not provider input."], "characters": characters, "locations": locations, "props": props}
        conflicts: list[ProductionBridgeConflict] = []
        advisories: list[ProductionBridgeConflict] = []
        f4_episodes = {item.get("ep"): item for item in script.get("episodes", []) if isinstance(item, dict)}
        section_by_episode = {item.get("episode"): item.get("sectionId") for item in script.get("sectionBindings", []) if isinstance(item, dict)}
        scenes: list[dict[str, Any]] = []; beats: list[dict[str, Any]] = []; cues: list[dict[str, Any]] = []; shots: list[dict[str, Any]] = []; links: list[dict[str, Any]] = []
        visual_scenes: list[dict[str, Any]] = []; visual_cuts: list[dict[str, Any]] = []; intent_entries: list[ProductionBridgeIntentEntry] = []
        for episode in storyboard.get("episodes", []):
            if not isinstance(episode, dict) or not isinstance(episode.get("ep"), int): continue
            ep, section_id = episode["ep"], section_by_episode.get(episode["ep"])
            f4 = f4_episodes.get(ep)
            if not section_id or not isinstance(f4, dict):
                conflicts.append(ProductionBridgeConflict(code="f4_mapping_missing", message="不能安装：F5 集数没有当前 F4 场次映射", episode=ep)); continue
            grouped: dict[int, list[tuple[int, dict[str, Any]]]] = {}
            for segment_order, segment in enumerate(episode.get("segments", []), 1):
                if not isinstance(segment, dict) or not isinstance(segment.get("sceneIndex"), int):
                    conflicts.append(ProductionBridgeConflict(code="scene_index_missing", message="不能安装：F5 分段缺少场次索引", section_id=section_id, episode=ep)); continue
                grouped.setdefault(segment["sceneIndex"], []).append((segment_order, segment))
            for index, source_segments in grouped.items():
                f4_scenes = f4.get("scenes", [])
                if not isinstance(f4_scenes, list) or index < 1 or index > len(f4_scenes):
                    conflicts.append(ProductionBridgeConflict(code="scene_index_unknown", message="不能安装：F5 场次索引不在当前 F4 中", section_id=section_id, episode=ep, scene_index=index)); continue
                source_scene = f4_scenes[index - 1]
                cuts = [(segment_order, segment, cut_order, cut) for segment_order, segment in source_segments for cut_order, cut in enumerate(segment.get("cuts", []), 1)]
                if not isinstance(source_scene, dict) or not isinstance(cuts, list) or not cuts:
                    conflicts.append(ProductionBridgeConflict(code="scene_cuts_missing", message="不能安装：F5 场次没有镜头", section_id=section_id, episode=ep, scene_index=index)); continue
                if not brief.shots_per_scene_min <= len(cuts) <= brief.shots_per_scene_max:
                    issue = ProductionBridgeConflict(
                        code="brief_shot_count" if brief.shot_count_is_strict else "shot_count_preference",
                        message=(
                            f"不能安装：源场次有 {len(cuts)} 个镜头，当前项目规则为 {brief.shots_per_scene_min}–{brief.shots_per_scene_max} 个"
                            if brief.shot_count_is_strict else
                            f"创作提示：源场次有 {len(cuts)} 个镜头，偏好范围为 {brief.shots_per_scene_min}–{brief.shots_per_scene_max} 个；此项不阻止确认"
                        ),
                        section_id=section_id, episode=ep, scene_index=index,
                    )
                    (conflicts if brief.shot_count_is_strict else advisories).append(issue)
                cut_durations: dict[int, int] = {}
                for cut_order, (_, _, _, source_cut) in enumerate(cuts, 1):
                    try:
                        cut_durations[cut_order] = source_seconds_to_milliseconds(source_cut.get("seconds") if isinstance(source_cut, dict) else None)
                    except ValueError:
                        conflicts.append(ProductionBridgeConflict(code="cut_duration_invalid", message="不能安装：F5 镜头时长不能精确表示为正整数毫秒", section_id=section_id, episode=ep, scene_index=index))
                scene_id = f"{section_id}-s{index}"; flow = source_scene.get("flow", []) if isinstance(source_scene.get("flow"), list) else []
                beat_ids = [f"{scene_id}-b{order}" for order in range(1, max(1, len(flow)) + 1)]
                state = self._state(); canonical_character_ids = {item["id"] for item in characters}
                source_characters = source_scene.get("characters") if isinstance(source_scene.get("characters"), list) else []
                character_ids = [mappings.get(value) for value in source_characters if isinstance(value, str)]
                if len(character_ids) != len(source_characters) or any(value not in canonical_character_ids for value in character_ids):
                    conflicts.append(ProductionBridgeConflict(code="scene_character_unmappable", message="不能安装：F4 场次角色不能映射到已接受角色", section_id=section_id, episode=ep, scene_index=index))
                source_location = source_scene.get("sceneId")
                location_ids = {item["id"] for item in locations}
                location_id = source_location if isinstance(source_location, str) and source_location in location_ids else None
                if isinstance(source_location, str) and source_location and location_id is None:
                    conflicts.append(ProductionBridgeConflict(code="scene_location_unmappable", message="不能安装：F4 场次地点不能映射到已接受美术", section_id=section_id, episode=ep, scene_index=index))
                node = graph_nodes.get(section_id)
                source_props = source_scene.get("props") if isinstance(source_scene.get("props"), list) else []
                prop_ids = {item["id"] for item in props}
                if any(not isinstance(value, str) or value not in prop_ids for value in source_props):
                    conflicts.append(ProductionBridgeConflict(code="scene_prop_unmappable", message="不能安装：F4 场次道具不能映射到已接受美术", section_id=section_id, episode=ep, scene_index=index))
                f1_summary = getattr(node, "summary", None)
                flow_seed = next(((flow_index, value, value.get("action") or value.get("line")) for flow_index, value in enumerate(flow, 1) if isinstance(value, dict) and isinstance(value.get("action") or value.get("line"), str) and (value.get("action") or value.get("line")).strip()), None)
                scene_seed = f1_summary if isinstance(f1_summary, str) and f1_summary.strip() else flow_seed[2] if flow_seed else None
                if not scene_seed:
                    conflicts.append(ProductionBridgeConflict(code="scene_intent_unmappable", message="不能安装：F4 场次缺少可审阅的戏剧意图来源", section_id=section_id, episode=ep, scene_index=index)); continue
                scene_intent_id = f"{scene_id}-objective"
                if isinstance(f1_summary, str) and f1_summary.strip():
                    source_coordinates, source_value = {"stage": "F1", "storyNodeId": section_id, "sectionId": section_id, "episode": ep, "sceneIndex": index}, node.model_dump(mode="json", by_alias=True)
                else:
                    assert flow_seed is not None
                    source_coordinates, source_value = {"stage": "F4", "sectionId": section_id, "episode": ep, "sceneIndex": index, "flowIndex": flow_seed[0]}, flow_seed[1]
                intent_entries.append(ProductionBridgeIntentEntry(id=scene_intent_id, target_kind="scene_objective", target_id=scene_id, source_coordinates=source_coordinates, source_content_hash=sha256(canonical_json(source_value)).hexdigest(), source_excerpt=scene_seed, text=""))
                scenes.append({"id": scene_id, "storyNodeId": section_id, "order": index, "title": source_scene.get("sceneId") or scene_id, "objective": "", "locationId": location_id, "characterIds": character_ids, "beatIds": beat_ids, "durationBudgetUnits": sum(cut_durations.values()), "entryState": state, "exitState": state})
                for order, beat_id in enumerate(beat_ids, 1):
                    value = flow[order - 1] if order <= len(flow) else {}
                    description = value.get("action") if isinstance(value, dict) else None
                    if not isinstance(description, str) or not description.strip():
                        description = value.get("line") if isinstance(value, dict) else None
                    if not isinstance(description, str) or not description.strip():
                        conflicts.append(ProductionBridgeConflict(code="beat_intent_unmappable", message="不能安装：F4 流条目缺少可审阅的戏剧意图来源", section_id=section_id, episode=ep, scene_index=index)); continue
                    intent_id = f"{beat_id}-purpose"
                    intent_entries.append(ProductionBridgeIntentEntry(id=intent_id, target_kind="beat_purpose", target_id=beat_id, source_coordinates={"sectionId": section_id, "episode": ep, "sceneIndex": index, "flowIndex": order}, source_content_hash=sha256(canonical_json(value)).hexdigest(), source_excerpt=description, text=""))
                    beats.append({"id": beat_id, "sceneId": scene_id, "order": order, "description": description, "purpose": "", "visibleEvent": description, "immediateResult": "", "dramaticChange": "", "entryState": state, "exitState": state, "continuityAnchors": [], "continuityDelta": {}})
                    if isinstance(value, dict) and isinstance(value.get("line"), str) and value["line"].strip():
                        source_speaker = value.get("speaker")
                        speaker_id = mappings.get(source_speaker, source_speaker) if isinstance(source_speaker, str) else None
                        if speaker_id not in canonical_character_ids:
                            conflicts.append(ProductionBridgeConflict(code="dialogue_speaker_unknown", message="不能安装：F4 台词说话人不在已接受角色映射中", section_id=section_id, episode=ep, scene_index=index))
                        else:
                            source_delivery = value.get("delivery")
                            delivery = source_delivery if source_delivery in {"measured", "natural", "brisk"} else "natural"
                            estimate = default_dialogue_timing_profile().estimate_text_duration_units(text=value["line"], language=brief.language, delivery=delivery)
                            if estimate is None:
                                conflicts.append(ProductionBridgeConflict(code="dialogue_timing_unmappable", message="不能安装：F4 台词没有当前语言的时长规则", section_id=section_id, episode=ep, scene_index=index))
                            else:
                                cues.append({"id": f"{beat_id}-d1", "beatId": beat_id, "order": 1, "speakerId": speaker_id, "voiceOver": None, "text": value["line"], "language": brief.language, "delivery": delivery, "performanceNotes": source_delivery if isinstance(source_delivery, str) else "", "estimatedDurationUnits": estimate})
                visual_scenes.append({"sectionId": section_id, "episode": ep, "sceneIndex": index, "sceneId": scene_id, "title": source_scene.get("sceneId") or scene_id, "cutCount": len(cuts)})
                for order, (segment_order, segment, source_cut_index, cut) in enumerate(cuts, 1):
                    if not isinstance(cut, dict) or order not in cut_durations:
                        continue
                    shot_id = f"{scene_id}-c{order}"; beat_range = cut.get("beats")
                    if not (isinstance(beat_range, list) and len(beat_range) == 2 and all(isinstance(value, int) for value in beat_range)):
                        conflicts.append(ProductionBridgeConflict(code="cut_beats_unmappable", message="不能安装：F5 镜头缺少连续且明确的 F4 节拍范围", section_id=section_id, episode=ep, scene_index=index)); continue
                    start, end = beat_range
                    selected = beat_ids[max(0, start - 1):min(len(beat_ids), end)] if start >= 1 and end >= start else []
                    if len(selected) != end - start + 1:
                        conflicts.append(ProductionBridgeConflict(code="cut_beats_unmappable", message="不能安装：F5 镜头节拍范围无法映射到当前 F4", section_id=section_id, episode=ep, scene_index=index)); continue
                    frame = cut.get("frame") if isinstance(cut.get("frame"), str) and cut["frame"].strip() else None
                    size = {"extreme-wide":"extreme_wide", "wide":"wide", "medium":"medium", "close":"close_up", "extreme-close":"extreme_close_up"}.get(cut.get("size"))
                    if size is None:
                        conflicts.append(ProductionBridgeConflict(code="cut_size_unmappable", message="不能安装：F5 镜头景别不在当前规范映射中", section_id=section_id, episode=ep, scene_index=index)); continue
                    cut_characters = cut.get("characters") if isinstance(cut.get("characters"), list) else []
                    mapped_cut_characters = [mappings.get(value) for value in cut_characters if isinstance(value, str)]
                    if len(mapped_cut_characters) != len(cut_characters) or any(value not in canonical_character_ids for value in mapped_cut_characters):
                        conflicts.append(ProductionBridgeConflict(code="cut_character_unmappable", message="不能安装：F5 镜头角色不能映射到已接受角色", section_id=section_id, episode=ep, scene_index=index)); continue
                    cut_props = cut.get("props") if isinstance(cut.get("props"), list) else []
                    if any(not isinstance(value, str) or value not in prop_ids for value in cut_props):
                        conflicts.append(ProductionBridgeConflict(code="cut_prop_unmappable", message="不能安装：F5 镜头道具不能映射到已接受美术", section_id=section_id, episode=ep, scene_index=index)); continue
                    cue_ids = [cue["id"] for cue in cues if cue["beatId"] in selected]
                    action = "\n".join(value["action"] for value in flow[start - 1:end] if isinstance(value, dict) and isinstance(value.get("action"), str) and value["action"].strip())
                    visible_props = list(dict.fromkeys([*source_props, *cut_props]))
                    shots.append({"id": shot_id, "sceneId": scene_id, "order": order, "title": frame or action, "shotSize": size, "durationUnits": cut_durations[order], "cameraAngle": "", "cameraMovement": cut.get("camera") if isinstance(cut.get("camera"), str) else "", "composition": frame or "", "visualIntent": "", "motionIntent": "", "action": action, "transition": "", "cueIds": cue_ids, "audioPlan": {"events": []}, "characterIds": mapped_cut_characters, "locationId": location_id, "propIds": visible_props, "requiredEntityStates": [], "entryState": state, "exitState": state})
                    links.extend({"shotId": shot_id, "beatId": beat_id, "role": "primary", "coverageWeight": 1 / len(selected)} for beat_id in selected)
                    visual_cuts.append({"sectionId": section_id, "episode": ep, "sceneIndex": index, "cutIndex": order, "shotId": shot_id, "seconds": cut["seconds"], "beats": cut.get("beats"), "frame": frame, "h3Prompt": segment.get("h3Prompt"), "source": {"segmentIndex": segment_order, "segmentSceneIndex": index, "cutIndex": source_cut_index}})
        package = ProductionBridgeIntentPackage(suggestion_origin="none", review_state="pending", entries=intent_entries)
        return {"bible": bible, "sceneBeats": {"scenes": scenes, "beats": beats, "dialogueCues": cues}, "storyboard": {"shots": shots, "shotBeatLinks": links}}, package, conflicts, advisories, visual_scenes, visual_cuts
