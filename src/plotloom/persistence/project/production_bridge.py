"""F5 review evidence to one explicitly accepted canonical V2 installation."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...canonical_schema import SceneBeatPlanV2, StoryBibleV2, StoryboardV2
from ...creative_handoff_exchange import canonical_json
from ...domain import ProjectBrief, StageName, StageStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...production_bridge_contracts import (
    ProductionBridgeAcceptRequest, ProductionBridgeConflict, ProductionBridgeProposal,
    ProductionBridgeState,
)
from ..schema.project_production_bridge import (
    ProductionBridgeAdmissionRow, ProductionBridgeHeadRow, ProductionBridgeRevisionRow,
)
from ..schema.project_cast import CastRevisionRow
from ..schema.project_storyboard_review import StoryboardReviewRevisionRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .storyboard_review import ProjectStoryboardReviewPersistence


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
        }
        return inputs, accepted.storyboard, script, cast | {"__art__": art}

    @staticmethod
    def _state() -> dict[str, Any]:
        return {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}

    def _build(self, session: Any, project_id: str, *, inputs: dict[str, Any], storyboard: dict[str, Any], script: dict[str, Any], cast_and_art: dict[str, Any]) -> tuple[dict[str, Any], list[ProductionBridgeConflict], list[dict[str, Any]], list[dict[str, Any]]]:
        project = self._access.rows.project(session, project_id)
        brief = ProjectBrief.model_validate(project.brief)
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
            characters.append({"id": canonical_id, "name": item.get("name") or canonical_id, "description": persona.get("appearance") or "Accepted cast appearance.", "visualAnchors": [persona.get("appearance") or "accepted cast"], "soundAnchors": ["accepted voice"], "allowedStates": ["present"], "continuityRules": ["preserve accepted cast identity"], "role": None, "goal": persona.get("motivation") or "Advance the accepted story.", "traits": [persona.get("arc") or "accepted"], "voiceAnchors": [((item.get("voice") or {}).get("timbre") if isinstance(item.get("voice"), dict) else None) or "accepted voice"]})
        locations = [{"id": item["id"], "name": item.get("name") or item["id"], "description": item.get("summary") or "Accepted art scene.", "visualAnchors": [item.get("summary") or item.get("name") or item["id"]], "soundAnchors": ["accepted ambience"], "allowedStates": ["unchanged"], "continuityRules": ["preserve accepted art setting"]} for item in art.get("scenes", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
        props = [{"id": item["id"], "name": item.get("name") or item["id"], "description": item.get("summary") or "Accepted art prop.", "visualAnchors": [item.get("summary") or item.get("name") or item["id"]], "soundAnchors": ["accepted prop sound"], "allowedStates": ["available"], "continuityRules": ["preserve accepted art prop"]} for item in art.get("props", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
        bible = {"logline": script.get("source") or "Accepted source story.", "premise": script.get("source") or "Accepted source story.", "genre": "interactive drama", "tone": "accepted source direction", "audience": "project audience", "narrativePromise": "Preserve accepted F1–F5 evidence.", "visualLanguage": "accepted art direction", "themes": ["choice"], "worldRules": ["Use accepted source evidence only."], "knownFacts": ["Bridge projection is deterministic."], "openQuestions": [], "sourceNotes": ["F5 H3 prompt text is review evidence, not provider input."], "characters": characters, "locations": locations, "props": props}
        conflicts: list[ProductionBridgeConflict] = []
        f4_episodes = {item.get("ep"): item for item in script.get("episodes", []) if isinstance(item, dict)}
        section_by_episode = {item.get("episode"): item.get("sectionId") for item in script.get("sectionBindings", []) if isinstance(item, dict)}
        scenes: list[dict[str, Any]] = []; beats: list[dict[str, Any]] = []; cues: list[dict[str, Any]] = []; shots: list[dict[str, Any]] = []; links: list[dict[str, Any]] = []
        visual_scenes: list[dict[str, Any]] = []; visual_cuts: list[dict[str, Any]] = []
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
                character_ids = [mappings.get(value, value) for value in source_scene.get("characters", []) if mappings.get(value, value) in canonical_character_ids] if isinstance(source_scene.get("characters"), list) else []
                location_id = source_scene.get("sceneId") if source_scene.get("sceneId") in {item["id"] for item in locations} else None
                scenes.append({"id": scene_id, "storyNodeId": section_id, "order": index, "title": source_scene.get("sceneId") or scene_id, "objective": "Preserve the accepted F4 scene occurrence.", "locationId": location_id, "characterIds": character_ids, "beatIds": beat_ids, "durationBudgetUnits": sum(int(cut.get("seconds", 0)) * 1000 for _, _, _, cut in cuts if isinstance(cut, dict)), "entryState": state, "exitState": state})
                for order, beat_id in enumerate(beat_ids, 1):
                    value = flow[order - 1] if order <= len(flow) else {}
                    description = value.get("action") if isinstance(value, dict) else None
                    beats.append({"id": beat_id, "sceneId": scene_id, "order": order, "description": description or "Accepted F4 action.", "purpose": "Advance the accepted scene.", "visibleEvent": description or "Accepted action.", "immediateResult": "Scene continues.", "dramaticChange": "Accepted progression.", "entryState": state, "exitState": state, "continuityAnchors": [], "continuityDelta": {}})
                    if isinstance(value, dict) and isinstance(value.get("line"), str) and value["line"].strip():
                        source_speaker = value.get("speaker")
                        speaker_id = mappings.get(source_speaker, source_speaker) if isinstance(source_speaker, str) else None
                        if speaker_id not in canonical_character_ids:
                            conflicts.append(ProductionBridgeConflict(code="dialogue_speaker_unknown", message="不能安装：F4 台词说话人不在已接受角色映射中", section_id=section_id, episode=ep, scene_index=index))
                        else:
                            source_delivery = value.get("delivery")
                            cues.append({"id": f"{beat_id}-d1", "beatId": beat_id, "order": 1, "speakerId": speaker_id, "voiceOver": None, "text": value["line"], "language": "zh-CN", "delivery": source_delivery if source_delivery in {"measured", "natural", "brisk"} else "natural", "performanceNotes": source_delivery if isinstance(source_delivery, str) else "No explicit F4 performance direction.", "estimatedDurationUnits": max(1, len(value["line"].strip()) * 330)})
                visual_scenes.append({"sectionId": section_id, "episode": ep, "sceneIndex": index, "sceneId": scene_id, "title": source_scene.get("sceneId") or scene_id, "cutCount": len(cuts)})
                for order, (segment_order, segment, source_cut_index, cut) in enumerate(cuts, 1):
                    if not isinstance(cut, dict) or not isinstance(cut.get("seconds"), int):
                        conflicts.append(ProductionBridgeConflict(code="cut_duration_invalid", message="不能安装：F5 镜头时长无效", section_id=section_id, episode=ep, scene_index=index)); continue
                    shot_id = f"{scene_id}-c{order}"; start, end = (cut.get("beats") or [1, len(beat_ids)])
                    selected = beat_ids[max(0, int(start) - 1):min(len(beat_ids), int(end))] if isinstance(start, int) and isinstance(end, int) else beat_ids
                    if not selected: selected = [beat_ids[0]]
                    frame = cut.get("frame") if isinstance(cut.get("frame"), str) else ""
                    cue_ids = [cue["id"] for cue in cues if cue["beatId"] in selected]
                    shots.append({"id": shot_id, "sceneId": scene_id, "order": order, "title": frame or f"F5 cut {order}", "shotSize": {"extreme-wide":"extreme_wide", "wide":"wide", "medium":"medium", "close":"close_up", "extreme-close":"extreme_close_up"}.get(cut.get("size"), "medium"), "durationUnits": cut["seconds"] * 1000, "cameraAngle": "eye level", "cameraMovement": cut.get("camera") or "static", "composition": frame or "accepted F5 framing", "visualIntent": frame or "accepted F5 frame", "motionIntent": cut.get("camera") or "accepted movement", "action": frame or "accepted F5 cut", "transition": "cut", "cueIds": cue_ids, "audioPlan": {"events": []}, "characterIds": character_ids, "locationId": location_id, "propIds": [], "requiredEntityStates": [], "entryState": state, "exitState": state})
                    links.extend({"shotId": shot_id, "beatId": beat_id, "role": "primary", "coverageWeight": 1 / len(selected)} for beat_id in selected)
                    visual_cuts.append({"sectionId": section_id, "episode": ep, "sceneIndex": index, "cutIndex": order, "shotId": shot_id, "seconds": cut["seconds"], "beats": cut.get("beats"), "frame": frame, "h3Prompt": segment.get("h3Prompt"), "source": {"segmentIndex": segment_order, "segmentSceneIndex": index, "cutIndex": source_cut_index}})
        return {"bible": bible, "sceneBeats": {"scenes": scenes, "beats": beats, "dialogueCues": cues}, "storyboard": {"shots": shots, "shotBeatLinks": links}}, conflicts, visual_scenes, visual_cuts

    def _current(self, session: Any, project_id: str, inputs: dict[str, Any]) -> list[str]:
        try: current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error: return [str(error)]
        return [f"{key} changed" for key, value in inputs.items() if current.get(key) != value]

    def get_state(self, project_id: str) -> ProductionBridgeState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id); head = self._head(session, project_id)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision)) if head.revision else None
            stale = self._current(session, project_id, row.inputs) if row else []
            proposal = ProductionBridgeProposal(revision=row.revision, content_hash=row.content_hash, inputs=row.inputs, scenes=row.proposal["scenes"], cuts=row.proposal["cuts"], conflicts=[ProductionBridgeConflict.model_validate(item) for item in row.conflicts], installable=row.installable, prepared_at=row.prepared_at) if row else None
            admission = session.scalar(select(ProductionBridgeAdmissionRow).where(ProductionBridgeAdmissionRow.project_id == project_id).order_by(ProductionBridgeAdmissionRow.accepted_at.desc()).limit(1))
            return ProductionBridgeState(proposal=proposal, status="stale" if stale else head.status, stale_reasons=stale, installed_stage_revisions=admission.installed_stage_revisions if admission and not stale else None)

    def prepare(self, project_id: str) -> ProductionBridgeState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id)); head = self._head(session, project_id)
            inputs, storyboard, script, cast_art = self._context(session, project_id)
            payload, conflicts, scenes, cuts = self._build(session, project_id, inputs=inputs, storyboard=storyboard, script=script, cast_and_art=cast_art)
            proposal = {"payload": payload, "scenes": scenes, "cuts": cuts}; digest = sha256(canonical_json({"inputs": inputs, "proposal": proposal, "conflicts": [item.model_dump(mode="json") for item in conflicts]})).hexdigest(); now = utc_now()
            head.revision += 1; head.status, head.updated_at = "ready", now
            session.add(ProductionBridgeRevisionRow(id=new_id(), project_id=project_id, revision=head.revision, content_hash=digest, inputs=inputs, proposal=proposal, conflicts=[item.model_dump(mode="json") for item in conflicts], installable=not conflicts, prepared_at=now))
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
