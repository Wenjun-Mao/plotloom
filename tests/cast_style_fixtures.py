"""Explicit style-complete candidates for persistence fixtures, not native delivery."""
from copy import deepcopy


def style_fixture(cast, contract):
    result = deepcopy(cast)
    if contract.get("authority") == "saved_brief":
        result["style"], result["lang"] = "saved-brief", "zh"
        for character in result["characters"]:
            character.update({"aliases": [], "importance": "protagonist", "oneLiner": "在航标与码头之间做选择。"})
            character["persona"].update({"gender": "女（推断）", "ageRange": "成年（推断）", "identity": "航标看守者（推断）", "temperament": "谨慎（推断）", "relationships": [], "evidence": ["Lin chooses the beacon or dock."]})
            character["voice"] = {"timbre": "平静清晰（推断）", "pitch": "中音（推断）", "pace": "缓慢（推断）", "accent": "普通话（推断）", "emotion": "沉着（推断）", "referenceHint": "不模仿特定演员", "prompt": "Calm clear voice with a measured pace"}
            character["image"] = {"style": "Saved Brief direction", "prompt": "A character portrait in muted watercolor collage", "sheet": "A character detail sheet in muted watercolor collage", "negativePrompt": "blurry", "tags": []}
        return result
    preset = contract["preset"]
    result["style"] = contract["style"]
    for character in result["characters"]:
        character["image"] = {
            **character.get("image", {}), "style": preset["label"],
            "prompt": preset["render"], "sheet": preset["render"],
            "negativePrompt": preset["negative"], "tags": preset["tags"],
        }
    return result
