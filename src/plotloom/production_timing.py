"""Exact raw-source seconds at the integer-millisecond production boundary."""
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
