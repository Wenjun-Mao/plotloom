"""Truthful attribution for a creator action without an authenticated name."""

from typing import Literal

from plotloom.domain_base import CamelModel


class UnnamedCreatorConfirmation(CamelModel):
    kind: Literal["unnamed_creator"] = "unnamed_creator"
