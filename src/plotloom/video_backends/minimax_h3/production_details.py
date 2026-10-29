"""Deterministic H3 settings that used to disappear from authored shot meaning."""
import json


def append_production_details(description, shot, rendered):
    for field in ("cameraAngle", "transition"):
        if shot.get(field):
            description.append(rendered[f"shot.{field}"])
    size = {"extreme_wide": "extreme wide shot", "wide": "wide shot", "full": "full shot",
        "medium_wide": "medium wide shot", "medium": "medium shot", "medium_close": "medium close-up",
        "close_up": "close-up", "extreme_close_up": "extreme close-up", "insert": "insert shot"}.get(shot.get("shotSize"))
    if size:
        description.append(f"Use the authored {size} framing.")
    for field, label in (("entryState", "Start continuity"), ("exitState", "End continuity"),
            ("requiredEntityStates", "Required entity states")):
        if shot.get(field):
            description.append(rendered[f"shot.{field}"])


def detail_sources(shot):
    return [(f"shot.{field}", json.dumps(shot[field], ensure_ascii=False, sort_keys=True), label)
        for field, label in (("entryState", "开始连续性"), ("exitState", "结束连续性"),
            ("requiredEntityStates", "必需实体状态")) if shot.get(field)]
