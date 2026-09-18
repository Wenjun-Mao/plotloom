"""Rows for the independent F1A source-to-outline review record."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SourceOutlineHeadRow(Base):
    __tablename__ = "v2_source_outline_heads"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outline_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_job_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    outline_status: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceOutlineSourceRevisionRow(Base):
    __tablename__ = "v2_source_outline_source_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    material: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceOutlineCandidateRow(Base):
    __tablename__ = "v2_source_outline_candidates"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_outline_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outline: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    report_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceOutlineRevisionRow(Base):
    __tablename__ = "v2_source_outline_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_job_id: Mapped[str] = mapped_column(String(80), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outline: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceOutlineSectionMapHeadRow(Base):
    __tablename__ = "v2_source_outline_section_map_heads"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="missing")
    stale_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceOutlineSectionMapRevisionRow(Base):
    __tablename__ = "v2_source_outline_section_map_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    outline_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    outline_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceOutlineGraphAdmissionRow(Base):
    """Binding receipt for a source-map-owned canonical graph revision."""

    __tablename__ = "v2_source_outline_graph_admissions"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outline_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    outline_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    section_map_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    section_map_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    graph_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    graph_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    stale_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
