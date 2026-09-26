"""Trusted execution pins for immutable project-owned creative handoffs."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CreativeHandoffExecutionPinRow(Base):
    """The project database, not an editable package, owns the expected pin."""

    __tablename__ = "v2_creative_handoff_execution_pins"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_pin: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovered_from_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
