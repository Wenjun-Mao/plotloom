"""Trusted speech estimates; provider cut limits and route allocation live elsewhere."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import Field, model_serializer, model_validator

from .domain_base import CamelModel
from .language_policy import TIMING_POLICY_VERSION


class DialogueDeliveryPace(str, Enum):
    """Only explicit bounded pace changes timing; free-form notes do not."""

    MEASURED = "measured"
    NATURAL = "natural"
    BRISK = "brisk"


class DialogueTimingRule(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    language: Annotated[str, Field(min_length=1)]
    delivery: DialogueDeliveryPace
    units_per_character: Annotated[int, Field(ge=1)]
    units_per_word: Annotated[int, Field(ge=0)] = 0


    @model_serializer(mode="wrap")
    def preserve_frozen_optional_rule_field(self, handler):
        # unitsPerWord is additive. Retained hashes bind the original omission;
        # reading a rule must not invent a field in its recorded wire identity.
        value = handler(self)
        if "units_per_word" not in self.model_fields_set:
            value.pop("unitsPerWord", None)
            value.pop("units_per_word", None)
        return value


class DialogueTimingProfile(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    version: Annotated[str, Field(min_length=1)]
    rules: Annotated[list[DialogueTimingRule], Field(min_length=1)]

    @model_validator(mode="after")
    def _rules_are_unique(self) -> DialogueTimingProfile:
        pairs = [(rule.language, rule.delivery) for rule in self.rules]
        if len(pairs) != len(set(pairs)):
            raise ValueError("dialogue timing rules must be unique by language and delivery")
        return self

    def rule_for(self, *, language: str, delivery: DialogueDeliveryPace) -> DialogueTimingRule | None:
        exact = next((rule for rule in self.rules if (rule.language, rule.delivery) == (language, delivery)), None)
        fallback = next((rule for rule in self.rules if (rule.language, rule.delivery) == ("*", delivery)), None)
        return exact or fallback

    def estimate_text_duration_units(self, *, text: str, language: str,
            delivery: DialogueDeliveryPace) -> int | None:
        rule = self.rule_for(language=language, delivery=delivery)
        if rule is None:
            return None
        if rule.units_per_word:
            # Python code points match JS Array.from; do not count UTF-16 units.
            # Tokens deliberately remain whitespace-delimited: no model tokenizer,
            # guessing the language of proper names, or faster rate for long words.
            characters = sum(not character.isspace() for character in text)
            return max(characters * rule.units_per_character, len(text.split()) * rule.units_per_word)
        return len(text.strip()) * rule.units_per_character

    def estimate_duration_units(self, cue: Any) -> int | None:
        return self.estimate_text_duration_units(text=cue.text, language=cue.language, delivery=cue.delivery)


def _rules(language: str, characters: tuple[int, int, int], words=(0, 0, 0)):
    return [DialogueTimingRule(language=language, delivery=pace,
        units_per_character=character, units_per_word=word)
        for pace, character, word in zip(DialogueDeliveryPace, characters, words, strict=True)]


DEFAULT_DIALOGUE_TIMING_PROFILE = DialogueTimingProfile(
    version=TIMING_POLICY_VERSION,
    rules=[
        *_rules("zh-CN", (420, 330, 260)),
        *_rules("en-US", (85, 70, 55), (500, 400, 330)),
        *_rules("en", (85, 70, 55), (500, 400, 330)),
        *_rules("*", (85, 70, 55)),
    ],
)


def default_dialogue_timing_profile() -> DialogueTimingProfile:
    return DEFAULT_DIALOGUE_TIMING_PROFILE.model_copy(deep=True)
