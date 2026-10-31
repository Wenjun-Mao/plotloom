"""Authored presentation for an exact installed standalone game."""
from pydantic import Field, model_validator

from .domain_base import CamelModel
from .public_values import contains_secret_setting, contains_secret_value


class PlayerExportSafetyError(RuntimeError):
    """A generic error prevents validation responses from echoing private input."""


def assert_public_player_data(value):
    raw = value.model_dump(mode="json", by_alias=True) if isinstance(value, CamelModel) else value
    def carries_credential(item):
        if isinstance(item, dict):
            return any(contains_secret_value(str(key)) or carries_credential(child) for key, child in item.items())
        if isinstance(item, (list, tuple)):
            return any(carries_credential(child) for child in item)
        return contains_secret_value(item)
    if contains_secret_setting(raw) or carries_credential(raw):
        raise PlayerExportSafetyError("standalone presentation must not contain credential material")


class PlayerEndingCard(CamelModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)


class PlayerExportRequest(CamelModel):
    version: int = Field(default=1, ge=1, le=1)
    admission_id: str = Field(min_length=1, max_length=128)
    game_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    intro: str = Field(default="", max_length=4000)
    ending_cards: dict[str, PlayerEndingCard] = Field(default_factory=dict)
    # Keys are stable authored names, values are exact installed identities.
    node_bindings: dict[str, str] = Field(default_factory=dict)
    edge_bindings: dict[str, str] = Field(default_factory=dict)
    slot_bindings: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def protect_private_input(cls, value):
        assert_public_player_data(value)
        return value

    @model_validator(mode="after")
    def unique_bindings(self):
        import re
        for bindings in (self.node_bindings, self.edge_bindings, self.slot_bindings):
            if len(bindings.values()) != len(set(bindings.values())):
                raise ValueError("logical bindings must be one-to-one")
            if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", key) for key in bindings):
                raise ValueError("logical binding names must be stable plain identifiers")
        return self
