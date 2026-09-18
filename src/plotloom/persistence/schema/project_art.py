"""Independent F3A art-review rows; generated images remain out of scope."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ArtHeadRow(Base):
    __tablename__ = "v2_art_heads"
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_job_id: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtCandidateRow(Base):
    __tablename__ = "v2_art_candidates"
    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    expected_art_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    binding: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128))
    manifest_hash: Mapped[str | None] = mapped_column(String(64))
    art: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    report_html: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ArtRevisionRow(Base):
    __tablename__ = "v2_art_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_job_id: Mapped[str] = mapped_column(String(80), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    binding: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    art: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
