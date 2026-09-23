"""Compile one frozen canonical shot into the H3 single-image prompt contract."""

from __future__ import annotations

from typing import Any

_FIRST_FRAME = (
    "For the target video, at 0.00 seconds into the target video, "
    "<Picture 1> (from [Shot 1]) is fully referenced."
)


def compile_i2va_prompt(snapshot: dict[str, Any]) -> str:
    """Keep authored facts verbatim while assigning each sound one H3 role.

    The canonical shot and resolved context own content. This formatter owns
    only the I2VA alignment, speaker IDs, and field placement; it does not
    translate or invent actions, dialogue, ambience, or music.
    """

    shot = snapshot["shot"]
    context = snapshot["resolvedContext"]
    cues = context.get("dialogueCues", [])
    description = [
        (
            "[Shot 1] <Picture 1> establishes the opening visual style, composition, "
            "subjects, objects, and spatial relationships; preserve them as the "
            "action develops in one continuous shot."
        )
    ]
    for field in ("composition", "visualIntent", "action", "motionIntent"):
        value = str(shot.get(field) or "").strip()
        if value:
            description.append(value)
    camera = str(shot.get("cameraMovement") or "").strip()
    if camera:
        description.append(f"Camera movement: {camera}.")

    speaker_ids: dict[str, str] = {}
    characters = {
        item["id"]: item for item in context.get("characters", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    events = shot.get("audioPlan", {}).get("events", [])
    for event in events:
        if event.get("kind") in {"diegetic_sound", "diegetic_music"} and event.get("description"):
            description.append(str(event["description"]).strip())
    for cue in cues:
        text = str(cue.get("text") or "")
        if not text:
            continue
        # A duplicate line in action or visual intent is ambiguous: the
        # author must resolve it before the provider sees a second utterance.
        if any(text in str(shot.get(field) or "") for field in ("composition", "visualIntent", "action", "motionIntent", "cameraMovement")) or any(text in str(event.get("description") or "") for event in events):
            raise ValueError("dialogue is repeated in the authored shot description")
        identity = str(cue.get("speakerId") or cue.get("voiceOver") or "")
        if not identity:
            raise ValueError("dialogue cue has no stable speaker identity")
        speaker_id = speaker_ids.setdefault(identity, f"S{len(speaker_ids) + 1}")
        character = characters.get(identity, {})
        voice = "; ".join(str(item) for item in character.get("voiceAnchors", []) if item)
        speaker = (
            f"The visible speaker established by <Picture 1> ({speaker_id})"
            if not cue.get("voiceOver") and identity in shot.get("characterIds", [])
            else f"The off-screen speaker ({speaker_id})"
        )
        if voice:
            speaker += f", voice character: {voice}"
        delivery = str(cue.get("delivery") or "").strip()
        performance = str(cue.get("performanceNotes") or "").strip()
        if delivery:
            speaker += f", delivery: {delivery}"
        if performance:
            speaker += f", performance: {performance}"
        if cue.get("voiceOver"):
            description.append(
                f"{speaker} says in an off-screen voiceover: "
                f"<d>[{_language(cue.get('language'))}] {text}</d>"
            )
        else:
            description.append(
                f"{speaker} says once: <d>[{_language(cue.get('language'))}] {text}</d>"
            )
    description.append("No captions, subtitles, or newly visible words.")

    soundscape = " ".join(
        str(event.get("description") or "").strip()
        for event in events
        if event.get("kind") in {"ambience", "sound_effect"} and event.get("description")
    )
    if not soundscape:
        soundscape = "Only environmental and physical sounds of the depicted scene; no additional voices."
    music = " ".join(
        str(event.get("description") or "").strip()
        for event in events
        if event.get("kind") == "score" and event.get("description")
    ) or "N/A"
    return (
        f"{_FIRST_FRAME}\n\n"
        f"integrated_multimodal_description: {' '.join(description)}\n\n"
        f"overall_soundscape: {soundscape}\n\n"
        f"non_diegetic_music: {music}"
    )


def _language(value: object) -> str:
    return {"zh-CN": "Chinese", "en-US": "English"}.get(str(value), str(value))


def compile_i2va_prompt_v1(snapshot: dict[str, Any]) -> str:
    """Reconstruct the one submitted trial's already frozen v1 prompt exactly.

    New jobs use v2's stored prompt bytes. This legacy formatter exists only
    so a prepared v1 job cannot silently change text after a code restart.
    """

    shot = snapshot["shot"]
    context = snapshot["resolvedContext"]
    description = [
        (
            "[Shot 1] Cinematic live-action. <Picture 1> establishes the opening "
            "composition, person, objects, and their positions; preserve them as the "
            "action develops in one continuous shot."
        )
    ]
    for field in ("composition", "visualIntent", "action", "motionIntent"):
        value = str(shot.get(field) or "").strip()
        if value:
            description.append(value)
    camera = str(shot.get("cameraMovement") or "").strip()
    if camera:
        description.append(f"Camera movement: {camera}.")
    speaker_ids: dict[str, str] = {}
    characters = {
        item["id"]: item for item in context.get("characters", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for cue in context.get("dialogueCues", []):
        text = str(cue.get("text") or "")
        if not text:
            continue
        if any(text in str(shot.get(field) or "") for field in ("composition", "visualIntent", "action", "motionIntent")):
            raise ValueError("dialogue is repeated in the authored shot description")
        identity = str(cue.get("speakerId") or cue.get("voiceOver") or "")
        if not identity:
            raise ValueError("dialogue cue has no stable speaker identity")
        speaker_id = speaker_ids.setdefault(identity, f"S{len(speaker_ids) + 1}")
        character = characters.get(identity, {})
        voice = "; ".join(str(item) for item in character.get("voiceAnchors", []) if item)
        speaker = f"The speaker established by <Picture 1> ({speaker_id})"
        if voice:
            speaker += f", voice character: {voice}"
        if cue.get("voiceOver"):
            description.append(
                f"{speaker} says in an off-screen voiceover: "
                f"<d>[{_language(cue.get('language'))}] {text}</d> "
                "while their lips remain completely closed."
            )
        else:
            description.append(
                f"{speaker} says once: <d>[{_language(cue.get('language'))}] {text}</d>"
            )
    description.append("No captions, subtitles, or newly visible words.")
    events = shot.get("audioPlan", {}).get("events", [])
    soundscape = " ".join(
        str(event.get("description") or "").strip()
        for event in events
        if event.get("kind") not in {"dialogue", "music"} and event.get("description")
    )
    if not soundscape:
        soundscape = "Only environmental and physical sounds of the depicted scene; no additional voices."
    music = " ".join(
        str(event.get("description") or "").strip()
        for event in events
        if event.get("kind") == "music" and event.get("description")
    ) or "N/A"
    return (
        f"{_FIRST_FRAME}\n\n"
        f"integrated_multimodal_description: {' '.join(description)}\n\n"
        f"overall_soundscape: {soundscape}\n\n"
        f"non_diegetic_music: {music}"
    )
