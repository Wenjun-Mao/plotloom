"""Verify complete inventory against historical accepted and canonical owners."""
import json

from ...autopilot_materials import MaterialInventory, MaterialSubject
from ...canonical_schema import SceneBeatPlanV2, StoryboardV2, StoryGraphV2
from ...source_structures import complete_routes


def assert_inventory_binding(connection, project_id, raw, *, executor_contract):
    inventory = MaterialInventory.model_validate(raw)
    if executor_contract == "plotloom.codex-exec.v8" and inventory.version != "pre-video.inventory.v2":
        raise ValueError("current CLI inventories require the explicit consumer identity contract")
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
        columns = '"cast",consumer_mappings' if field == "cast" else '"art"'
        retained = connection.execute(f'SELECT {columns} FROM "{table}" WHERE project_id=? AND revision=?', (project_id, revision)).fetchone()
        if retained is None:
            raise ValueError("inventory accepted subject owner missing")
        payload = json.loads(retained[0])
        if field == "cast":
            consumers = {item["castCharacterId"]: item["consumerCharacterId"] for item in json.loads(retained[1])}
            if set(consumers) != {item["id"] for item in payload["characters"]}:
                raise ValueError("inventory Cast owner has no exact consumer mapping")
            expected.extend(MaterialSubject(owner="character-reference", id=item["id"],
                consumer_character_id=consumers[item["id"]] if inventory.version == "pre-video.inventory.v2" else None)
                for item in payload["characters"])
        else:
            for kind, key in (("scene", "scenes"), ("prop", "props")):
                expected.extend(MaterialSubject(owner="art-reference", subject_type=kind, id=item["id"]) for item in payload[key])
    for shot in shots:
        if shot.scene_id not in scenes or len(shot.character_ids) > 8:
            raise ValueError("inventory shot is not supported reachable filmed material")
        expected.append(MaterialSubject(owner="image", id=shot.id, scene_id=shot.scene_id, character_ids=shot.character_ids))
    if inventory.subjects != expected or inventory.route_count != len(routes):
        raise ValueError("inventory omits or changes required subjects or unique filmed shots")
