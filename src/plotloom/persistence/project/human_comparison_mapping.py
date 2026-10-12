"""Explicit human comparison context for manually completed non-v3 material."""
from ...domain import StageName
from ...exceptions import InvalidTransitionError
from ..schema import ManagedAssetRow


def human_mapping(session, binding, canonical, references):
    board = canonical._load_stage_payload(session, binding.project_id, StageName.STORYBOARD)
    bible = canonical._load_stage_payload(session, binding.project_id, StageName.STORY_BIBLE)
    shot = next((item for item in board.shots if item.id == binding.shot_id), None)
    if shot is None:
        raise InvalidTransitionError("human comparison requires the current shot")
    characters = {item.id: item for item in bible.characters}
    mapping = []
    for character_id in shot.character_ids:
        reference = references.current_character_reference_in_session(session, binding.project_id, characters[character_id])
        if reference is None:
            raise InvalidTransitionError("human comparison requires each current character reference")
        assets = [session.get(ManagedAssetRow, identifier) for identifier in [reference.primary_asset_id, *reference.complementary_asset_ids]]
        mapping.append({"characterId": character_id, "referenceDecisionId": reference.id,
            "referenceRevision": reference.reference_revision,
            "assets": [{"originalHash": asset.original_hash} for asset in assets]})
    return mapping
