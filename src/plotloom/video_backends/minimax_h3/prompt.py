"""Compile one frozen canonical shot into the H3 single-image prompt contract."""

from __future__ import annotations

from typing import Any

from .directions import bind_reviewed_directions

_FIRST_FRAME = (
    "For the target video, at 0.00 seconds into the target video, "
    "<Picture 1> (from [Shot 1]) is fully referenced."
)
def compile_i2va_prompt(snapshot: dict[str, Any], reviewed_directions: dict[str, Any]) -> str:
    """Place reviewed source-bound English directions into H3's I2VA roles."""

    shot = snapshot["shot"]
    context = snapshot["resolvedContext"]
    rendered = bind_reviewed_directions(snapshot, reviewed_directions)
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
            description.append(rendered[f"shot.{field}"])
    camera = str(shot.get("cameraMovement") or "").strip()
    if camera:
        description.append(rendered["shot.cameraMovement"])

    speaker_ids: dict[str, str] = {}
    characters = {
        item["id"]: item for item in context.get("characters", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    events = shot.get("audioPlan", {}).get("events", [])
    for event_index, event in enumerate(events):
        if event.get("kind") in {"diegetic_sound", "diegetic_music"} and event.get("description"):
            description.append(rendered[f"shot.audioPlan.events.{event_index}.description"])
    for cue_index, cue in enumerate(cues):
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
        voice = "; ".join(
            rendered[f"resolvedContext.characters.{identity}.voiceAnchors.{index}"]
            for index, item in enumerate(character.get("voiceAnchors", [])) if item
        )
        speaker = (
            f"The visible speaker established by <Picture 1> ({speaker_id})"
            if not cue.get("voiceOver") and identity in shot.get("characterIds", [])
            else f"The off-screen speaker ({speaker_id})"
        )
        if voice:
            description.append(f"{speaker} speaks with {_lower_initial(voice.rstrip('.'))}.")
        delivery = str(cue.get("delivery") or "").strip()
        performance = str(cue.get("performanceNotes") or "").strip()
        if performance:
            description.append(rendered[f"resolvedContext.dialogueCues.{cue_index}.performanceNotes"])
        delivery_phrase = (
            f" with {_lower_initial(rendered[f'resolvedContext.dialogueCues.{cue_index}.delivery'].rstrip('.'))} delivery"
            if delivery else ""
        )
        if cue.get("voiceOver"):
            description.append(
                f"{speaker}{',' + delivery_phrase + ',' if delivery_phrase else ''} says in an off-screen voiceover: "
                f"<d>[{_language(cue.get('language'))}] {text}</d>"
                + (" while their lips remain completely closed."
                   if identity in shot.get("characterIds", []) else "")
            )
        else:
            description.append(
                f"{speaker} says once{delivery_phrase}: <d>[{_language(cue.get('language'))}] {text}</d>"
            )
    description.append("Do not add text overlays or words absent from the reviewed first frame and authored shot.")

    soundscape = " ".join(
        rendered[f"shot.audioPlan.events.{index}.description"]
        for index, event in enumerate(events)
        if event.get("kind") in {"ambience", "sound_effect"} and event.get("description")
    )
    if not soundscape:
        soundscape = rendered["reviewedSoundscape"]
    music = " ".join(
        rendered[f"shot.audioPlan.events.{index}.description"]
        for index, event in enumerate(events)
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


def _lower_initial(value: str) -> str:
    return value[:1].lower() + value[1:]


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
