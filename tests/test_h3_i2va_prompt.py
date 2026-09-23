from __future__ import annotations

import pytest

from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
from plotloom.video_jobs import VideoJobService


def _snapshot() -> dict:
    return {
        "shot": {
            "composition": "Medium shot of the keeper with a brass fuse between two sockets.",
            "visualIntent": "Cold blue storm light and warm instrument light.",
            "action": "She holds the fuse between the sockets.",
            "motionIntent": "A slow push toward her hand.",
            "cameraMovement": "Push In",
            "characterIds": ["C01"],
            "audioPlan": {"events": [{"kind": "ambience", "description": "Rain taps the glass."}]},
        },
        "resolvedContext": {
            "characters": [{"id": "C01", "voiceAnchors": ["A steady lower female voice."]}],
            "dialogueCues": [{"speakerId": "C01", "voiceOver": None, "language": "zh-CN", "text": "一枚，只够一边。"}],
        },
    }


def test_single_image_prompt_assigns_dialogue_once_and_keeps_soundscape_separate() -> None:
    prompt = compile_i2va_prompt(_snapshot())
    assert prompt.startswith("For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n")
    assert prompt.count("一枚，只够一边。") == 1
    assert "<d>[Chinese] 一枚，只够一边。</d>" in prompt
    assert "overall_soundscape: Rain taps the glass." in prompt
    assert "non_diegetic_music: N/A" in prompt
    assert prompt.index("integrated_multimodal_description:") < prompt.index("overall_soundscape:") < prompt.index("non_diegetic_music:")


def test_duplicate_authored_dialogue_is_rejected_before_dispatch() -> None:
    snapshot = _snapshot()
    snapshot["shot"]["action"] += " 一枚，只够一边。"
    with pytest.raises(ValueError, match="dialogue is repeated"):
        compile_i2va_prompt(snapshot)


def test_voiceover_stays_offscreen_without_invented_visible_lips() -> None:
    snapshot = _snapshot()
    snapshot["resolvedContext"]["dialogueCues"][0].update({"speakerId": None, "voiceOver": "C01"})
    prompt = compile_i2va_prompt(snapshot)
    assert "says in an off-screen voiceover" in prompt
    assert "visible speaker established" not in prompt
    assert "lips remain completely closed" not in prompt


def test_named_speaker_outside_visible_cast_stays_offscreen() -> None:
    snapshot = _snapshot()
    snapshot["shot"]["characterIds"] = []
    prompt = compile_i2va_prompt(snapshot)
    assert "The off-screen speaker (S1)" in prompt
    assert "says once" in prompt
    assert "visible speaker established" not in prompt


def test_canonical_music_and_performance_use_their_owned_fields() -> None:
    snapshot = _snapshot()
    snapshot["shot"]["audioPlan"]["events"].extend([
        {"kind": "diegetic_music", "description": "A radio plays a short melody."},
        {"kind": "score", "description": "Sparse low strings at a slow tempo."},
    ])
    snapshot["resolvedContext"]["dialogueCues"][0].update({
        "delivery": "measured", "performanceNotes": "Quiet and deliberate",
    })
    prompt = compile_i2va_prompt(snapshot)
    body, soundscape = prompt.split("overall_soundscape:", 1)
    assert "A radio plays a short melody." in body
    assert "A radio plays a short melody." not in soundscape
    assert "non_diegetic_music: Sparse low strings at a slow tempo." in prompt
    assert "delivery: measured" in body
    assert "performance: Quiet and deliberate" in body


def test_existing_prepared_job_keeps_its_named_flat_compiler() -> None:
    snapshot = _snapshot()
    snapshot["compilerVersion"] = "p2-video-adapters-v2"
    legacy = VideoJobService._prompt(snapshot)
    assert legacy.startswith("Cold blue storm light")
    assert "Dialogue (zh-CN; speaker=C01" in legacy
    assert "integrated_multimodal_description" not in legacy
    snapshot["compilerVersion"] = "plotloom.h3-i2va.v1"
    assert "integrated_multimodal_description" in VideoJobService._prompt(snapshot)
    snapshot["compilerVersion"] = "plotloom.h3-i2va.v2"
    snapshot["compiledPrompt"] = "exact frozen provider payload"
    assert VideoJobService._prompt(snapshot) == "exact frozen provider payload"
