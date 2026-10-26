from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CharacterImportedAppearanceRow(Base):
    """One imported project asset intentionally offered to one cast subject."""

    __tablename__ = "v2_character_imported_appearances"
    __table_args__ = (
        UniqueConstraint("project_id", "character_id", "asset_id", name="uq_v2_character_imported_appearance"),
        Index("ix_v2_character_imported_appearances_project_character", "project_id", "character_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    character_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    character_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
