"""Transport authored soundtrack context without classifying its prose."""
from hashlib import sha256

COMPILER_VERSION = "plotloom.h3-production-brief.v10"


def authored_audio_sources(snapshot):
    version = snapshot.get("compilerVersion")
    if version not in {"plotloom.h3-production-brief.v8", "plotloom.h3-production-brief.v9", COMPILER_VERSION}:
        return []
    timing = snapshot["sourceTiming"]
    if timing["kind"] == "f5_bridge":
        cut = timing["cut"]
        text = cut["composition"]
        path = "sourceTiming.cut.composition"
        coordinates = {key: cut[key] for key in (
            "sectionId", "episode", "sceneIndex", "cutIndex", "shotId", "source"
        ) if key in cut}
    else:
        text = snapshot["shot"].get("composition", "")
        path = "shot.composition"
        coordinates = {"shotId": snapshot["shot"]["id"]}
    sources = _role_views(text, path, coordinates)
    if version in {"plotloom.h3-production-brief.v9", COMPILER_VERSION}:
        sources.extend(_role_views(snapshot["shot"].get("action", ""), "shot.action",
            {"shotId": snapshot["shot"]["id"]}, prefix="reviewedAction"))
    return sources


def _role_views(text, path, coordinates, *, prefix="reviewed"):
    if not isinstance(text, str):
        raise TypeError("authored soundtrack context must be an exact source scalar")
    provenance = {"text": text, "sourcePath": path,
        "sourceTextHash": sha256(text.encode()).hexdigest(), "sourceCoordinates": coordinates}
    return [
        provenance | {"path": prefix + "Soundscape", "label": "作者环境声、动作声音与发声范围限制",
            "role": "ambient_effects_and_sound_exclusions"},
        provenance | {"path": prefix + "Music", "label": "作者非叙事内配乐与配乐限制",
            "role": "non_diegetic_music"},
    ]
