"""Recoverable author input, deliberately separate from accepted review models."""

import json
import re
from typing import Literal

from pydantic import Field, model_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value


class ReviewBufferPayload(CamelModel):
    editor: Literal["source", "cast", "art", "script"]
    basis: str = Field(min_length=1, max_length=4_000)
    text: str = Field(max_length=200_000)

    @model_validator(mode="after")
    def protect_embedded_credentials(self) -> "ReviewBufferPayload":
        # JSON editors may be incomplete. They are author text, not canonical
        # models, but valid embedded JSON still obeys the project secret guard.
        try:
            authored = json.loads(self.text)
        except ValueError:
            authored = self.text
        if contains_secret_setting(authored) or contains_secret_value(authored) or re.search(
            r'"[^"\\]*(?:apiKey|api_key|password|credential|authorization|accessToken|access_token)"\s*:',
            self.text, flags=re.IGNORECASE,
        ):
            raise ValueError("review drafts must not contain credentials")
        if isinstance(authored, dict):
            for value in authored.values():
                if isinstance(value, str):
                    try:
                        embedded = json.loads(value)
                    except ValueError:
                        continue
                    if contains_secret_setting(embedded) or contains_secret_value(embedded):
                        raise ValueError("review drafts must not contain embedded credentials")
        return self
