"""Exact saved context displayed and endorsed by whole-pack confirmation."""
from ...bulk_material_contracts import SavedIntentContext
from ..codec import stable_hash
from .handoff_visual_intents import authored_intent


def storyboard_intent(shot, entity_id, revision, content_hash):
    return {"role": "shot_keyframe", "compositionIntent": shot["visualIntent"] + " " + shot["composition"],
        "sourceRefs": [f"storyboard:{entity_id}:shot:{shot['id']}"],
        "sourceEndorsement": {"kind": "saved_storyboard", "entityRevisionId": entity_id,
            "revision": revision, "contentHash": content_hash, "shotId": shot["id"]}}


def assert_source_intent(connection, project_id, payload):
    from ...canonical_schema import StoryboardV2
    from ...source_endorsed_intent import SourceEndorsedIntent
    parsed = SourceEndorsedIntent.model_validate(payload)
    source = parsed.source_endorsement
    row = connection.execute("SELECT project_id,stage,revision,content_hash,payload FROM v2_entity_revisions WHERE id=?", (source.entity_revision_id,)).fetchone()
    if row is None or row[:4] != (project_id, "storyboard", source.revision, source.content_hash):
        raise ValueError("endorsed intent lacks its exact saved storyboard revision")
    board = StoryboardV2.model_validate_json(row[4])
    shot = next((item for item in board.shots if item.id == source.shot_id), None)
    authored = {key: value for key, value in payload.items() if key != "attribution"}
    if shot is None or authored != storyboard_intent(shot.model_dump(mode="json", by_alias=True), source.entity_revision_id, source.revision, source.content_hash):
        raise ValueError("endorsed intent differs from exact saved source text")


def context_for_frame(inventory, shot, intent=None):
    raw = shot.model_dump(mode="json", by_alias=True)
    if intent is not None:
        return SavedIntentContext(kind="reviewed_intent", source_id=intent.id, revision=intent.revision,
            content_hash=stable_hash(intent.intent), shot_id=shot.id, intent=authored_intent(intent.intent))
    return SavedIntentContext(kind="storyboard", source_id=inventory.entity_revision_id,
        revision=inventory.storyboard_revision, content_hash=inventory.storyboard_hash,
        shot_id=shot.id, intent=storyboard_intent(raw, inventory.entity_revision_id, inventory.storyboard_revision, inventory.storyboard_hash))


def assert_saved_context(connection, project_id, frame, inventory, shot):
    context = frame.intent_context
    if context is None or context.shot_id != frame.shot_id:
        raise ValueError("bulk frame lacks its exact saved intent context")
    if context.kind == "storyboard":
        if ((context.source_id, context.revision, context.content_hash) !=
                (inventory.entity_revision_id, inventory.storyboard_revision, inventory.storyboard_hash)):
            raise ValueError("saved storyboard context identity changed")
        expected = storyboard_intent(shot, inventory.entity_revision_id, inventory.storyboard_revision, inventory.storyboard_hash)
    else:
        import json
        row = connection.execute("SELECT project_id,asset_id,revision,intent FROM v2_visual_intents WHERE id=?", (context.source_id,)).fetchone()
        binding = connection.execute("SELECT visual_intent_id,visual_intent_revision FROM v2_reviewed_shot_bindings WHERE id=? AND project_id=? AND shot_id=? AND asset_id=?",
            (frame.source_id, project_id, frame.shot_id, frame.asset_id)).fetchone()
        if (row is None or row[:3] != (project_id, frame.asset_id, context.revision)
                or binding != (context.source_id, context.revision) or stable_hash(json.loads(row[3])) != context.content_hash):
            raise ValueError("saved reviewed intent identity changed")
        expected = authored_intent(json.loads(row[3]))
    from ...source_endorsed_intent import parse_saved_intent
    if context.intent.model_dump(mode="json", by_alias=True) != parse_saved_intent(expected).model_dump(mode="json", by_alias=True):
        raise ValueError("displayed saved intent differs from source")
