"""Necessary speech bounds are explicit and independent of UI/provider capacity."""
import pytest

from plotloom.canonical_schema import DialogueDeliveryPace, default_dialogue_timing_profile
from plotloom.production_dialogue_timing import projected_dialogue_timing


@pytest.mark.parametrize("locale,text,expected", [
    ("en-US", "I am here.", 1200),
    ("en-US", "Please keep the light on.", 2000),
    ("en-US", "extraordinarily", 1050),
    ("en-US", "  I\n am\t here. ", 1200),
    ("zh-CN", "请把灯留着。", 1980),
    ("zh-CN", "  A 😀 B  ", 1650),
])
def test_natural_word_and_character_lower_bounds(locale, text, expected):
    profile = default_dialogue_timing_profile()
    assert profile.version == "dialogue.bilingual.v2"
    rule = profile.rule_for(language=locale, delivery=DialogueDeliveryPace.NATURAL)
    assert rule.language == locale
    assert profile.estimate_text_duration_units(text=text, language=locale,
        delivery=DialogueDeliveryPace.NATURAL) == expected


def test_explicit_spoken_language_and_bounded_pace_own_estimate():
    ordinary = projected_dialogue_timing({"line": "I am here.", "delivery": "natural"}, "en-US")
    freeform = projected_dialogue_timing({"line": "I am here.", "delivery": "very fast to fit"}, "en-US")
    assert ordinary["estimatedDurationUnits"] == freeform["estimatedDurationUnits"] == 1200
    literal = projected_dialogue_timing({"line": "请把灯留着。", "language": "zh-CN", "delivery": "measured"}, "en-US")
    assert literal["language"] == "zh-CN"
    assert literal["estimatedDurationUnits"] == 2520


def test_timing_profile_copy_cannot_rewrite_default():
    profile = default_dialogue_timing_profile()
    profile.rules.pop()
    assert len(default_dialogue_timing_profile().rules) == len(profile.rules) + 1
