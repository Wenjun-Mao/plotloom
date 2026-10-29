"""Transport authored soundtrack context without classifying its prose."""
from hashlib import sha256

COMPILER_VERSION = "plotloom.h3-production-brief.v8"


def authored_audio_sources(snapshot):
    if snapshot.get("compilerVersion") != COMPILER_VERSION:
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
    if not isinstance(text, str):
        raise TypeError("authored soundtrack context must be an exact composition scalar")
    provenance = {"text": text, "sourcePath": path,
        "sourceTextHash": sha256(text.encode()).hexdigest(), "sourceCoordinates": coordinates}
    return [
        provenance | {"path": "reviewedSoundscape", "label": "作者环境声、动作声音与发声范围限制",
            "role": "ambient_effects_and_sound_exclusions"},
        provenance | {"path": "reviewedMusic", "label": "作者非叙事内配乐与配乐限制",
            "role": "non_diegetic_music"},
    ]
