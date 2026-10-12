"""Verify complete inventory against historical accepted and canonical owners."""
import json
from ...autopilot_materials import MaterialInventory, MaterialSubject
from ...canonical_schema import StoryGraphV2, SceneBeatPlanV2, StoryboardV2
from ...source_structures import complete_routes


def assert_inventory_binding(connection, project_id, raw):
    inventory = MaterialInventory.model_validate(raw)
    board = connection.execute("SELECT project_id,stage,revision,content_hash,input_revisions,payload FROM v2_entity_revisions WHERE id=?", (inventory.entity_revision_id,)).fetchone()
    if board is None or board[:4] != (project_id, "storyboard", inventory.storyboard_revision, inventory.storyboard_hash):
        raise ValueError("inventory storyboard owner changed")
    inputs = json.loads(board[4])
    def upstream(stage):
        row = connection.execute("SELECT payload FROM v2_entity_revisions WHERE project_id=? AND stage=? AND revision=?", (project_id, stage, inputs[stage])).fetchone()
        if row is None:
            raise ValueError("inventory upstream canonical owner missing")
        return json.loads(row[0])
    graph = StoryGraphV2.model_validate(upstream("story_graph"))
    beats = SceneBeatPlanV2.model_validate(upstream("scene_beats"))
    shots = StoryboardV2.model_validate(json.loads(board[5])).shots
    routes = complete_routes(graph)
    reachable = {node for route in routes for node in route}
    filmed = {node.id for node in graph.nodes if node.id in reachable and node.footage_mode == "footage"}
    scenes = {scene.id for scene in beats.scenes if scene.story_node_id in filmed}
    expected = []
    for table, field, revision in (("v2_cast_revisions", "cast", inventory.cast_revision), ("v2_art_revisions", "art", inventory.art_revision)):
        retained = connection.execute(f'SELECT "{field}" FROM "{table}" WHERE project_id=? AND revision=?', (project_id, revision)).fetchone()
        if retained is None:
            raise ValueError("inventory accepted subject owner missing")
        payload = json.loads(retained[0])
        if field == "cast":
            expected.extend(MaterialSubject(owner="character-reference", id=item["id"]) for item in payload["characters"])
        else:
            for kind, key in (("scene", "scenes"), ("prop", "props")):
                expected.extend(MaterialSubject(owner="art-reference", subject_type=kind, id=item["id"]) for item in payload[key])
    for shot in shots:
        if shot.scene_id not in scenes or len(shot.character_ids) > 8:
            raise ValueError("inventory shot is not supported reachable filmed material")
        expected.append(MaterialSubject(owner="image", id=shot.id, scene_id=shot.scene_id, character_ids=shot.character_ids))
    if inventory.subjects != expected or inventory.route_count != len(routes):
        raise ValueError("inventory omits or changes required subjects or unique filmed shots")
