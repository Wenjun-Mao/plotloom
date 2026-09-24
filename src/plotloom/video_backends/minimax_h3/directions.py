"""Bind reviewed English H3 directions to exact canonical source coordinates."""

from __future__ import annotations

import re
from typing import Any

from ...persistence.codec import stable_hash


_STRUCTURAL_MARKER = re.compile(
    r"<\s*/?\s*(?:d|Picture)\b|\[\s*Shot\s+\d+\s*\]|"
    r"\b(?:integrated_multimodal_description|overall_soundscape|non_diegetic_music)\s*:",
    re.IGNORECASE,
)


def direction_sources(snapshot: dict[str, Any]) -> dict[str, Any]:
    shot = snapshot["shot"]
    context = snapshot["resolvedContext"]
    sources: list[dict[str, str]] = []
    seen_paths: set[str] = set()

    def add(path: str, text: object, label: str) -> None:
        value = str(text or "").strip()
        if value and path not in seen_paths:
            sources.append({"path": path, "text": value, "label": label})
            seen_paths.add(path)

    for field, label in (
        ("composition", "构图与首帧"),
        ("visualIntent", "视觉意图"),
        ("action", "动作"),
        ("motionIntent", "动态意图"),
        ("cameraMovement", "镜头运动"),
    ):
        add(f"shot.{field}", shot.get(field), label)

    events = shot.get("audioPlan", {}).get("events", [])
    for index, event in enumerate(events):
        if event.get("kind") in {"ambience", "sound_effect", "diegetic_sound", "diegetic_music", "score"}:
            add(f"shot.audioPlan.events.{index}.description", event.get("description"), f"声音事件 {index + 1}")

    characters = {item.get("id"): item for item in context.get("characters", []) if isinstance(item, dict)}
    for index, cue in enumerate(context.get("dialogueCues", [])):
        if not cue.get("text"):
            continue
        identity = cue.get("speakerId") or cue.get("voiceOver")
        character = characters.get(identity) or {}
        for anchor_index, anchor in enumerate(character.get("voiceAnchors", [])):
            add(f"resolvedContext.characters.{identity}.voiceAnchors.{anchor_index}", anchor, f"角色 {identity} 声线")
        for field, label in (("delivery", "对白表达方式"), ("performanceNotes", "对白表演说明")):
            add(f"resolvedContext.dialogueCues.{index}.{field}", cue.get(field), f"对白 {index + 1} {label}")

    if not any(event.get("kind") in {"ambience", "sound_effect"} and event.get("description") for event in events):
        # The author can describe a physically grounded sound without
        # changing canonical audio events. Its provenance is a supplement.
        sources.append({
            "path": "reviewedSoundscape",
            "text": "No ambient or physical sound event is authored in this shot.",
            "label": "补充环境与动作声音（根据画面审阅）",
        })

    return {
        # This binds the review to dialogue, visibility, keyframe, provider,
        # and timing as well as the rendered fields. A changed final prompt
        # cannot inherit approval merely because the action text stayed put.
        "sourceHash": stable_hash(snapshot),
        "sources": sources,
    }


def bind_reviewed_directions(snapshot: dict[str, Any], package: dict[str, Any] | None) -> dict[str, str]:
    requirement = direction_sources(snapshot)
    if package is None:
        raise ValueError("H3 needs reviewed English directions; inspect prompt sources before preparing")
    if package.get("sourceHash") != requirement["sourceHash"]:
        raise ValueError("H3 direction source changed; review the current shot again")
    if package.get("reviewedEnglish") is not True:
        raise ValueError("H3 English directions need explicit package review")
    fields = package.get("fields")
    if not isinstance(fields, list):
        raise ValueError("H3 direction fields are missing")
    expected = {source["path"] for source in requirement["sources"]}
    rendered: dict[str, str] = {}
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("path"), str) or not isinstance(field.get("english"), str):
            raise ValueError("H3 direction field is malformed")
        path, english = field["path"], field["english"].strip()
        if path in rendered or path not in expected or not english:
            raise ValueError("H3 direction fields contain a duplicate, extra, or blank rendering")
        if "\n" in english or "\r" in english or _STRUCTURAL_MARKER.search(english):
            raise ValueError("H3 direction fields cannot create prompt sections or reserved markup")
        rendered[path] = english
    if set(rendered) != expected:
        raise ValueError("H3 direction fields do not cover every current source")
    for cue in snapshot["resolvedContext"].get("dialogueCues", []):
        text = str(cue.get("text") or "")
        if text and any(text in english for english in rendered.values()):
            raise ValueError("H3 dialogue is repeated in reviewed directions")
    return rendered
