"""Common managed-asset provenance projection, preserving origin evidence."""

from typing import Any, Literal

from pydantic import ConfigDict, Field

from .domain import CamelModel


class ManagedAssetProvenance(CamelModel):
    """A total public envelope over an immutable origin-specific declaration."""

    model_config = ConfigDict(extra="allow", strict=True)

    origin: str
    rights: Literal["known", "unknown"] = "unknown"
    rights_note: str | None = None
    declared_additions: list[str] = Field(default_factory=list)


def project_asset_provenance(declaration: dict[str, Any]) -> dict[str, Any]:
    # Missing common metadata means no recorded claim, not acquired rights or
    # proof that generation introduced nothing. Never rewrite retained rows.
    return ManagedAssetProvenance.model_validate(declaration).model_dump(
        mode="json", by_alias=True
    )
