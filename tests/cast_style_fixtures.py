"""Explicit style-complete candidates for persistence fixtures, not native delivery."""
from copy import deepcopy


def style_fixture(cast, contract):
    result = deepcopy(cast)
    preset = contract["preset"]
    result["style"] = contract["style"]
    for character in result["characters"]:
        character["image"] = {
            **character.get("image", {}), "style": preset["label"],
            "prompt": preset["render"], "sheet": preset["render"],
            "negativePrompt": preset["negative"], "tags": preset["tags"],
        }
    return result
