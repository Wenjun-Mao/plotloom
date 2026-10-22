"""Minimum author-confirmed design, not a judgment of creative quality."""
import re
from typing import Any


def _has_description(value: Any) -> bool:
    # Match the editor's lossless legacy annotation presentation; never mutate it.
    return isinstance(value, str) and bool(re.sub(r"\s*(?:（推断）|\(推断\))\s*$", "", value).strip())


def validate_cast_design(cast: dict[str, Any]) -> None:
    for character in cast["characters"]:
        persona = character.get("persona")
        persona = persona if isinstance(persona, dict) else {}
        name = character.get("name") or character["id"]
        traits = persona.get("personality")
        if not isinstance(traits, list) or not all(isinstance(value, str) for value in traits) or not any(_has_description(value) for value in traits):
            raise ValueError(f"{name}：请至少填写一个性格特点。")
        if not _has_description(persona.get("appearance")):
            raise ValueError(f"{name}：请填写角色外观，作为后续外观参考的依据。")
