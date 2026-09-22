"""F5 review evidence to one explicitly accepted canonical V2 installation."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from pydantic import ValidationError

from ...canonical_schema import SceneBeatPlanV2, StoryBibleV2, StoryboardV2, default_dialogue_timing_profile
from ...creative_handoff_exchange import canonical_json
from ...domain import ProjectBrief, StageName, StageStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...production_bridge_contracts import (
    ProductionBridgeAcceptRequest, ProductionBridgeConflict, ProductionBridgeIntentEntry,
    ProductionBridgeIntentPackage,
    ProductionBridgeIntentUpdateRequest, ProductionBridgeProposal, ProductionBridgeState,
)
from ..schema.project_production_bridge import (
    ProductionBridgeAdmissionRow, ProductionBridgeHeadRow, ProductionBridgeRevisionRow,
)
from ..schema.project_cast import CastRevisionRow
from ..schema.project_storyboard_review import StoryboardReviewRevisionRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .storyboard_review import ProjectStoryboardReviewPersistence
from ...validation import DomainValidationError, validate_stage_payload


class ProductionBridgePersistence:
    """Own the deterministic, non-generative F5-to-V2 projection seam."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence, review: ProjectStoryboardReviewPersistence) -> None:
        self._access, self._canonical, self._review = access, canonical, review

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(ProductionBridgeHeadRow, project_id) is None:
            session.add(ProductionBridgeHeadRow(project_id=project_id, revision=0, status="missing", updated_at=created_at))

    @staticmethod
    def _head(session: Any, project_id: str) -> ProductionBridgeHeadRow:
        row = session.get(ProductionBridgeHeadRow, project_id)
        if row is None:
            raise InvalidTransitionError("production bridge state is unavailable")
        return row

    def _context(self, session: Any, project_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        project = self._access.rows.project(session, project_id)
        review_head = self._review._head(session, project_id)
        accepted = session.scalar(select(StoryboardReviewRevisionRow).where(
            StoryboardReviewRevisionRow.project_id == project_id,
            StoryboardReviewRevisionRow.revision == review_head.revision,
        )) if review_head.revision else None
        if review_head.status != "accepted" or accepted is None:
            raise InvalidTransitionError("a current accepted F5 storyboard review is required")
        binding, script, _outline, cast, art = self._review._context(session, project_id)
        if self._review._stale(session, project_id, binding):
            raise InvalidTransitionError("the accepted F5 storyboard review is stale")
        inputs = {
            "reviewRevision": accepted.revision, "reviewContentHash": accepted.content_hash,
            "scriptRevision": binding.script_revision, "scriptContentHash": binding.script_content_hash,
            "graphRevision": binding.graph_revision, "graphContentHash": binding.graph_content_hash,
            "castRevision": binding.cast_revision, "castContentHash": binding.cast_content_hash,
            "artRevision": binding.art_revision, "artContentHash": binding.art_content_hash,
            "briefRevision": project.revision,
            "briefContentHash": sha256(canonical_json(project.brief)).hexdigest(),
        }
        return inputs, accepted.storyboard, script, cast | {"__art__": art}

    @staticmethod
    def _state() -> dict[str, Any]:
        return {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}

    def _build(self, session: Any, project_id: str, *, inputs: dict[str, Any], storyboard: dict[str, Any], script: dict[str, Any], cast_and_art: dict[str, Any]) -> tuple[dict[str, Any], ProductionBridgeIntentPackage, list[ProductionBridgeConflict], list[dict[str, Any]], list[dict[str, Any]]]:
        project = self._access.rows.project(session, project_id)
        brief = ProjectBrief.model_validate(project.brief)
        graph = self._canonical._load_stage_payload(session, project_id, StageName.STORY_GRAPH)
        graph_nodes = {node.id: node for node in getattr(graph, "nodes", [])}
        cast, art = dict(cast_and_art), cast_and_art["__art__"]
        cast.pop("__art__", None)
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
        bible = {"logline": brief.synopsis, "premise": brief.synopsis, "genre": brief.genre or "", "tone": "", "audience": "", "narrativePromise": "", "visualLanguage": brief.visual_style or "", "themes": [], "worldRules": [], "knownFacts": [], "openQuestions": [], "sourceNotes": ["F5 H3 prompt text is review evidence, not provider input."], "characters": characters, "locations": locations, "props": props}
        conflicts: list[ProductionBridgeConflict] = []
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
                    conflicts.append(ProductionBridgeConflict(code="brief_shot_count", message=f"不能安装：源场次有 {len(cuts)} 个镜头，当前项目规则为 {brief.shots_per_scene_min}–{brief.shots_per_scene_max} 个", section_id=section_id, episode=ep, scene_index=index))
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
                intent_entries.append(ProductionBridgeIntentEntry(id=scene_intent_id, target_kind="scene_objective", target_id=scene_id, source_coordinates=source_coordinates, source_content_hash=sha256(canonical_json(source_value)).hexdigest(), method="source_excerpt_seed.v1", suggested_text=scene_seed, text=scene_seed))
                scenes.append({"id": scene_id, "storyNodeId": section_id, "order": index, "title": source_scene.get("sceneId") or scene_id, "objective": scene_seed, "locationId": location_id, "characterIds": character_ids, "beatIds": beat_ids, "durationBudgetUnits": sum(int(cut.get("seconds", 0)) * 1000 for _, _, _, cut in cuts if isinstance(cut, dict)), "entryState": state, "exitState": state})
                for order, beat_id in enumerate(beat_ids, 1):
                    value = flow[order - 1] if order <= len(flow) else {}
                    description = value.get("action") if isinstance(value, dict) else None
                    if not isinstance(description, str) or not description.strip():
                        description = value.get("line") if isinstance(value, dict) else None
                    if not isinstance(description, str) or not description.strip():
                        conflicts.append(ProductionBridgeConflict(code="beat_intent_unmappable", message="不能安装：F4 流条目缺少可审阅的戏剧意图来源", section_id=section_id, episode=ep, scene_index=index)); continue
                    intent_id = f"{beat_id}-purpose"
                    intent_entries.append(ProductionBridgeIntentEntry(id=intent_id, target_kind="beat_purpose", target_id=beat_id, source_coordinates={"sectionId": section_id, "episode": ep, "sceneIndex": index, "flowIndex": order}, source_content_hash=sha256(canonical_json(value)).hexdigest(), method="source_excerpt_seed.v1", suggested_text=description, text=description))
                    beats.append({"id": beat_id, "sceneId": scene_id, "order": order, "description": description, "purpose": description, "visibleEvent": description, "immediateResult": "", "dramaticChange": "", "entryState": state, "exitState": state, "continuityAnchors": [], "continuityDelta": {}})
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
                    if not isinstance(cut, dict) or not isinstance(cut.get("seconds"), int):
                        conflicts.append(ProductionBridgeConflict(code="cut_duration_invalid", message="不能安装：F5 镜头时长无效", section_id=section_id, episode=ep, scene_index=index)); continue
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
                    action = next((beat["description"] for beat in beats if beat["id"] == selected[0]), None)
                    if not isinstance(action, str) or not action.strip():
                        conflicts.append(ProductionBridgeConflict(code="cut_action_unmappable", message="不能安装：F5 镜头未覆盖可用的 F4 动作或台词", section_id=section_id, episode=ep, scene_index=index)); continue
                    visible_props = list(dict.fromkeys([*source_props, *cut_props]))
                    shots.append({"id": shot_id, "sceneId": scene_id, "order": order, "title": frame or action, "shotSize": size, "durationUnits": cut["seconds"] * 1000, "cameraAngle": "", "cameraMovement": cut.get("camera") if isinstance(cut.get("camera"), str) else "", "composition": frame or "", "visualIntent": "", "motionIntent": "", "action": action, "transition": "", "cueIds": cue_ids, "audioPlan": {"events": []}, "characterIds": mapped_cut_characters, "locationId": location_id, "propIds": visible_props, "requiredEntityStates": [], "entryState": state, "exitState": state})
                    links.extend({"shotId": shot_id, "beatId": beat_id, "role": "primary", "coverageWeight": 1 / len(selected)} for beat_id in selected)
                    visual_cuts.append({"sectionId": section_id, "episode": ep, "sceneIndex": index, "cutIndex": order, "shotId": shot_id, "seconds": cut["seconds"], "beats": cut.get("beats"), "frame": frame, "h3Prompt": segment.get("h3Prompt"), "source": {"segmentIndex": segment_order, "segmentSceneIndex": index, "cutIndex": source_cut_index}})
        package = ProductionBridgeIntentPackage(method="source_excerpt_seed.v1", entries=intent_entries)
        return {"bible": bible, "sceneBeats": {"scenes": scenes, "beats": beats, "dialogueCues": cues}, "storyboard": {"shots": shots, "shotBeatLinks": links}}, package, conflicts, visual_scenes, visual_cuts

    def _validate_payload(self, session: Any, project_id: str, payload: dict[str, Any]) -> list[ProductionBridgeConflict]:
        """Run the same V2 models and gates used by canonical installation early."""

        try:
            project = self._access.rows.project(session, project_id)
            brief = ProjectBrief.model_validate(project.brief)
            bible = StoryBibleV2.model_validate(payload["bible"])
            beats = SceneBeatPlanV2.model_validate(payload["sceneBeats"])
            board = StoryboardV2.model_validate(payload["storyboard"])
            graph = self._canonical._load_stage_payload(session, project_id, StageName.STORY_GRAPH)
            validate_stage_payload(StageName.SCENE_BEATS, beats, schema_version=2, brief=brief, bible=bible, graph=graph, dialogue_timing_profile=default_dialogue_timing_profile())
            validate_stage_payload(StageName.STORYBOARD, board, schema_version=2, brief=brief, bible=bible, scene_beats=beats, dialogue_timing_profile=default_dialogue_timing_profile())
            return []
        except (ValidationError, DomainValidationError, TypeError, ValueError) as error:
            return [ProductionBridgeConflict(code="canonical_validation", message=f"不能安装：规范提案验证失败：{error}")]

    @staticmethod
    def _proposal_digest(inputs: dict[str, Any], proposal: dict[str, Any], conflicts: list[ProductionBridgeConflict]) -> str:
        return sha256(canonical_json({"inputs": inputs, "proposal": proposal, "conflicts": [item.model_dump(mode="json") for item in conflicts]})).hexdigest()

    def _apply_intent_package(self, payload: dict[str, Any], package: ProductionBridgeIntentPackage) -> dict[str, Any]:
        """Bind editable intent text to exactly the declared canonical targets."""

        patched = {"bible": payload["bible"], "sceneBeats": {key: [dict(item) for item in value] for key, value in payload["sceneBeats"].items()}, "storyboard": payload["storyboard"]}
        scenes = {item["id"]: item for item in patched["sceneBeats"]["scenes"]}
        beats = {item["id"]: item for item in patched["sceneBeats"]["beats"]}
        for entry in package.entries:
            if entry.target_kind == "scene_objective" and entry.target_id in scenes:
                scenes[entry.target_id]["objective"] = entry.text
            elif entry.target_kind == "beat_purpose" and entry.target_id in beats:
                beats[entry.target_id]["purpose"] = entry.text
            else:
                raise InvalidTransitionError("production bridge intent package has an unknown canonical target")
        return patched

    def _current(self, session: Any, project_id: str, inputs: dict[str, Any]) -> list[str]:
        try: current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error: return [str(error)]
        return [f"{key} changed" for key, value in inputs.items() if current.get(key) != value]

    def get_state(self, project_id: str) -> ProductionBridgeState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision)) if head.revision else None
            stale = self._current(session, project_id, row.inputs) if row else []
            proposal = ProductionBridgeProposal(revision=row.revision, content_hash=row.content_hash, inputs=row.inputs, intent_package=ProductionBridgeIntentPackage.model_validate(row.proposal["intentPackage"]), scenes=row.proposal["scenes"], cuts=row.proposal["cuts"], conflicts=[ProductionBridgeConflict.model_validate(item) for item in row.conflicts], installable=row.installable, prepared_at=row.prepared_at) if row else None
            admission = session.scalar(select(ProductionBridgeAdmissionRow).where(ProductionBridgeAdmissionRow.project_id == project_id).order_by(ProductionBridgeAdmissionRow.accepted_at.desc()).limit(1))
            return ProductionBridgeState(proposal=proposal, status="stale" if stale else head.status, stale_reasons=stale, installed_stage_revisions=admission.installed_stage_revisions if admission and not stale else None)

    def prepare(self, project_id: str) -> ProductionBridgeState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            inputs, storyboard, script, cast_art = self._context(session, project_id)
            payload, intent_package, conflicts, scenes, cuts = self._build(session, project_id, inputs=inputs, storyboard=storyboard, script=script, cast_and_art=cast_art)
            conflicts.extend(self._validate_payload(session, project_id, payload))
            proposal = {"payload": payload, "intentPackage": intent_package.model_dump(mode="json", by_alias=True), "scenes": scenes, "cuts": cuts}; digest = self._proposal_digest(inputs, proposal, conflicts); now = utc_now()
            head.revision += 1; head.status, head.updated_at = "ready", now
            session.add(ProductionBridgeRevisionRow(id=new_id(), project_id=project_id, revision=head.revision, content_hash=digest, inputs=inputs, proposal=proposal, conflicts=[item.model_dump(mode="json") for item in conflicts], installable=not conflicts, prepared_at=now))
        return self.get_state(project_id)

    def update_intent_package(self, project_id: str, request: ProductionBridgeIntentUpdateRequest) -> ProductionBridgeState:
        """Create one new review binding; client text cannot alter provenance."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            if head.status == "accepted":
                raise InvalidTransitionError("accepted production bridge evidence cannot be edited; prepare a new current proposal")
            if head.revision != request.expected_proposal_revision:
                raise RevisionConflictError("production bridge", request.expected_proposal_revision, head.revision)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision))
            if row is None or row.content_hash != request.expected_content_hash:
                raise InvalidTransitionError("production bridge proposal changed before its intent package was saved")
            if self._current(session, project_id, row.inputs):
                raise InvalidTransitionError("production bridge proposal is stale")
            package = ProductionBridgeIntentPackage.model_validate(row.proposal["intentPackage"])
            updates = {item.id: item.text for item in request.entries}
            known = {item.id for item in package.entries}
            if len(updates) != len(request.entries) or set(updates) != known:
                raise InvalidTransitionError("production bridge intent package must update every exact package entry once")
            updated = ProductionBridgeIntentPackage(method=package.method, entries=[entry.model_copy(update={"text": updates[entry.id]}) for entry in package.entries])
            payload = self._apply_intent_package(row.proposal["payload"], updated)
            conflicts = [ProductionBridgeConflict.model_validate(item) for item in row.conflicts if item.get("code") != "canonical_validation"]
            conflicts.extend(self._validate_payload(session, project_id, payload))
            proposal = {"payload": payload, "intentPackage": updated.model_dump(mode="json", by_alias=True), "scenes": row.proposal["scenes"], "cuts": row.proposal["cuts"]}
            digest, now = self._proposal_digest(row.inputs, proposal, conflicts), utc_now()
            head.revision += 1; head.status, head.updated_at = "ready", now
            session.add(ProductionBridgeRevisionRow(id=new_id(), project_id=project_id, revision=head.revision, content_hash=digest, inputs=row.inputs, proposal=proposal, conflicts=[item.model_dump(mode="json") for item in conflicts], installable=not conflicts, prepared_at=now))
        return self.get_state(project_id)

    def accept(self, project_id: str, request: ProductionBridgeAcceptRequest) -> ProductionBridgeState:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id); self._access.guards.active(project); head = self._head(session, project_id)
            if head.revision != request.expected_proposal_revision: raise RevisionConflictError("production bridge", request.expected_proposal_revision, head.revision)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision))
            if row is None or row.content_hash != request.expected_content_hash or not row.installable: raise InvalidTransitionError("production bridge proposal is not installable")
            if self._current(session, project_id, row.inputs): raise InvalidTransitionError("production bridge proposal is stale")
            for stage in (StageName.STORY_BIBLE, StageName.SCENE_BEATS, StageName.STORYBOARD):
                if self._access.rows.stage(session, project_id, stage).status != StageStatus.MISSING.value: raise InvalidTransitionError("first production bridge install requires empty canonical Bible, SceneBeats, and Storyboard heads")
            payload = row.proposal["payload"]; now = utc_now()
            bible = StoryBibleV2.model_validate(payload["bible"]); self._canonical._install_stage_in_session(session, project, StageName.STORY_BIBLE, bible, expected_revision=0, now=now, allow_noop=False)
            beats = SceneBeatPlanV2.model_validate(payload["sceneBeats"]); self._canonical._install_stage_in_session(session, project, StageName.SCENE_BEATS, beats, expected_revision=0, now=now, allow_noop=False)
            board = StoryboardV2.model_validate(payload["storyboard"]); self._canonical._install_stage_in_session(session, project, StageName.STORYBOARD, board, expected_revision=0, now=now, allow_noop=False)
            revisions = {stage.value: self._access.rows.stage(session, project_id, stage).revision for stage in (StageName.STORY_BIBLE, StageName.SCENE_BEATS, StageName.STORYBOARD)}
            session.add(ProductionBridgeAdmissionRow(id=new_id(), project_id=project_id, proposal_revision=row.revision, proposal_content_hash=row.content_hash, inputs=row.inputs, installed_stage_revisions=revisions, accepted_at=now)); head.status, head.updated_at = "accepted", now
        return self.get_state(project_id)
