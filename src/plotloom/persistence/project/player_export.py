"""One coherent installed-source and selected-media snapshot for static export."""
from contextlib import nullcontext
from copy import deepcopy

from ...canonical_schema import (
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryboardV2,
    StoryGraphV2,
)
from ...exceptions import InvalidTransitionError
from ...stage_contracts import StageName
from ..codec import stable_hash
from ..schema import (
    EntityRevisionRow,
    ManagedAssetRow,
    VideoCandidateSelectionRow,
    VideoJobRow,
)
from .selected_media_policy import selected_playback_policy


def capture_player_export(repository, project_id, request, *, in_session=None):
    """BEGIN IMMEDIATE prevents mixed authority; no media I/O holds this lock."""
    lease = nullcontext(in_session) if in_session is not None else repository._lifecycle_write()
    with selected_playback_policy(project_id), lease as session:
        installed = repository.production_bridge.installation_in_session(session, project_id)
        if installed is None or installed.status != "current" or installed.admission_id != request.admission_id:
            raise InvalidTransitionError("standalone export requires the exact current installed production")
        project = repository._project_access.rows.project(session, project_id)
        payloads, revisions = {}, {}
        for stage, model in ((StageName.STORY_BIBLE, StoryBibleV2), (StageName.STORY_GRAPH, StoryGraphV2),
                (StageName.SCENE_BEATS, SceneBeatPlanV2), (StageName.STORYBOARD, StoryboardV2)):
            head = repository._project_access.rows.stage(session, project_id, stage)
            row = session.get(EntityRevisionRow, head.entity_revision_id)
            if row is None or stable_hash(row.payload) != row.content_hash:
                raise InvalidTransitionError("installed canonical payload is inconsistent")
            payloads[stage.value] = model.model_validate(deepcopy(row.payload)).model_dump(mode="json", by_alias=True)
            revisions[stage.value] = {"revision": head.revision, "id": row.id, "hash": row.content_hash}
        graph, beats, board, bible = (payloads[s.value] for s in (
            StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD, StageName.STORY_BIBLE))
        _assert_graph(graph, installed.runtime_choice)
        node_ids = {n["id"] for n in graph["nodes"]}
        endings = {n["id"] for n in graph["nodes"] if not any(e["sourceNodeId"] == n["id"] for e in graph["edges"])}
        for bindings, targets in ((request.node_bindings, node_ids),
                (request.edge_bindings, {e["id"] for e in graph["edges"]}),
                (request.slot_bindings, {s["id"] for s in board["shots"]})):
            if set(bindings.values()) - targets:
                raise InvalidTransitionError("export logical binding names an unknown installed identity")
        if set(request.ending_cards) - endings:
            raise InvalidTransitionError("ending card names a non-ending node")
        names = {c["id"]: c["name"] for c in bible["characters"]}
        cues = {c["id"]: c for c in beats["dialogueCues"]}
        choices = {c["sectionId"]: c for c in (installed.runtime_choice or {}).get("choices", [])}
        nodes, media = [], []
        for node in graph["nodes"]:
            scenes = sorted((s for s in beats["scenes"] if s["storyNodeId"] == node["id"]), key=lambda s: (s["order"], s["id"]))
            shots = [shot for scene in scenes for shot in sorted(
                (s for s in board["shots"] if s["sceneId"] == scene["id"]), key=lambda s: (s["order"], s["id"]))]
            if node["footageMode"] != "route_only" and not shots:
                raise InvalidTransitionError("standalone export is missing node footage")
            clips = []
            for shot in shots:
                selection = session.get(VideoCandidateSelectionRow, (project_id, shot["id"]))
                if selection is None or not selection.selected_video_job_id:
                    raise InvalidTransitionError("standalone export requires every authored shot to have a selected segment")
                evidence = repository._media.video_segments.selected_storage_in_session(
                    session, project_id, selection.selected_video_job_id)
                job = session.get(VideoJobRow, selection.selected_video_job_id)
                asset_ids = {job.snapshot["keyframe"]["assetId"]}
                asset_ids.update(item["assetId"] for reference in job.snapshot.get("identityLineage", []) for item in reference["assets"])
                if job.snapshot.get("endFrame", {}).get("assetId"):
                    asset_ids.add(job.snapshot["endFrame"]["assetId"])
                sources = []
                for asset_id in sorted(asset_ids):
                    asset = session.get(ManagedAssetRow, asset_id)
                    if asset is None or asset.project_id != project_id:
                        raise InvalidTransitionError("selected media source asset is missing")
                    sources.append({"assetId": asset.id, "uri": asset.original_uri, "hash": asset.original_hash})
                evidence["sourceArtifacts"] = sources
                if (evidence["outFrame"] - evidence["inFrame"]) * 1000 != shot["durationUnits"] * 24:
                    raise InvalidTransitionError("selected segment does not cover the exact authored shot")
                path = f"media/{evidence['hash']}.mp4"
                media.append(evidence | {"shotId": shot["id"], "jobId": selection.selected_video_job_id,
                    "path": path, "durationUnits": shot["durationUnits"]})
                clips.append({"slot": next((k for k,v in request.slot_bindings.items() if v == shot["id"]), shot["id"]),
                    "src": path, "durationUnits": shot["durationUnits"],
                    "dialogue": [{"speaker": names.get(cues[c]["speakerId"], cues[c]["voiceOver"] or ""),
                        "text": cues[c]["text"]} for c in shot["cueIds"]],
                    "visibleText": [t["text"] for t in shot.get("visibleTexts", [])]})
            outgoing = [{"id": e["id"], "to": e["targetNodeId"], "label": e["choiceText"]}
                for e in graph["edges"] if e["sourceNodeId"] == node["id"]]
            nodes.append({"id": node["id"], "title": node["title"], "clips": clips,
                "question": choices.get(node["id"], {}).get("prompt", ""), "edges": outgoing,
                "ending": request.ending_cards[node["id"]].model_dump() if node["id"] in request.ending_cards
                    else ({"title": node["title"], "text": ""} if node["id"] in endings else None)})
        story = {"format": 1, "gameId": request.game_id, "title": project.brief["title"],
            "intro": request.intro, "start": graph["startNodeId"], "nodes": nodes}
        # Media bytes/selection changes independently from the authored story.
        source = {"admission": installed.model_dump(mode="json", by_alias=True), "stages": revisions,
            "projectRevision": project.revision, "briefHash": stable_hash(project.brief)}
        story_revision = stable_hash({"source": source, "presentation": request.model_dump(mode="json", by_alias=True)})
        story.update(storyRevision=story_revision, assetVersion=stable_hash(media))
        private = {"format": 1, "projectId": project_id, "source": source,
            "presentation": request.model_dump(mode="json", by_alias=True), "media": media,
            "storyRevision": story_revision, "assetVersion": story["assetVersion"]}
        return {"public": story, "private": private}


def _assert_graph(graph, runtime_choice):
    if graph["joinContracts"] or any(e.get("entityStateEffects") for e in graph["edges"]):
        raise InvalidTransitionError("standalone MVP supports only structural routes without state effects or joins")
    nodes = {n["id"] for n in graph["nodes"]}
    choices = (runtime_choice or {}).get("choices", [])
    by_node = {c["sectionId"]: c for c in choices}
    sources = {e["sourceNodeId"] for e in graph["edges"] if e["kind"] == "choice"}
    if len(by_node) != len(choices) or set(by_node) != sources:
        raise InvalidTransitionError("installed runtime choices do not cover the graph exactly")
    for edge in graph["edges"]:
        # The current source-map writer stores provenance in stateEffects.
        # These exact three facts are metadata, never executable player state.
        outcome = next((item for item in by_node.get(edge["sourceNodeId"], {}).get("outcomes", [])
            if item["outcomeId"] == edge["id"]), None)
        metadata = {"sourceMapChoiceId": edge["sourceNodeId"], "sourceMapOutcomeId": edge["id"],
            "sourceMapConsequence": outcome["consequence"]} if outcome else {}
        if edge["stateEffects"] not in ({}, metadata):
            raise InvalidTransitionError("standalone MVP does not execute authored state effects")
    for node in nodes:
        edges = [e for e in graph["edges"] if e["sourceNodeId"] == node]
        if any(e["targetNodeId"] not in nodes for e in edges):
            raise InvalidTransitionError("standalone graph has a dangling edge")
        if node in sources:
            actual = {(e["id"], e["targetNodeId"], e["choiceText"]) for e in edges}
            expected = {(e["outcomeId"], e["endingSectionId"], e["label"]) for e in by_node[node]["outcomes"]}
            if actual != expected or len(edges) != len(expected) or any(e["kind"] != "choice" for e in edges):
                raise InvalidTransitionError("installed runtime choices differ from canonical edges")
        elif len(edges) > 1:
            raise InvalidTransitionError("standalone continuation must have one unambiguous target")
    visited, active = set(), set()
    def visit(node):
        if node in active:
            raise InvalidTransitionError("standalone MVP does not support route cycles")
        if node in visited:
            return
        active.add(node)
        for edge in graph["edges"]:
            if edge["sourceNodeId"] == node:
                visit(edge["targetNodeId"])
        active.remove(node)
        visited.add(node)
    visit(graph["startNodeId"])
    if visited != nodes:
        raise InvalidTransitionError("standalone graph contains unreachable story content")
