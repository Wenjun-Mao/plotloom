"""Immutable standalone build inventory owned by one project."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PlayerExportRow(Base):
    __tablename__ = "v2_player_exports"

    receipt_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    receipt_uri: Mapped[str] = mapped_column(String, nullable=False)
    archive_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    archive_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
