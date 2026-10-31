"""Authored pacing targets and their relation to H3 playback requests."""
from fractions import Fraction
import math


def source_seconds_to_milliseconds(seconds: object) -> int:
    """Interpret the JSON number's decimal value; never round source time."""
    if type(seconds) not in {int, float} or isinstance(seconds, float) and not math.isfinite(seconds):
        raise ValueError("source seconds must be a finite positive number")
    value = Fraction(str(seconds)) * 1000
    if value <= 0 or value.denominator != 1:
        raise ValueError("source seconds must be exactly representable as positive integer milliseconds")
    return int(value)


def h3_playback_intent_valid(intent: str, target_ms: int, frames: int) -> bool:
    if type(target_ms) is not int or type(frames) is not int or min(target_ms, frames) <= 0:
        return False
    if intent == "whole_take":
        return True
    target_scaled = target_ms * 24
    if target_scaled % 1000 or frames * 1000 < target_scaled:
        return False
    return intent == ("source_exact" if frames * 1000 == target_scaled else "segment_required")
