"""Persistent F5 bridge proposal and immutable installation admission."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProductionBridgeHeadRow(Base):
    __tablename__ = "v2_production_bridge_heads"
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="missing")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionBridgeRevisionRow(Base):
    __tablename__ = "v2_production_bridge_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    proposal: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    installable: Mapped[bool] = mapped_column(nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionBridgeAdmissionRow(Base):
    __tablename__ = "v2_production_bridge_admissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    installed_stage_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionBridgeIntentJobRow(Base):
    """One durable, non-idempotent bridge inference attempt."""

    __tablename__ = "v2_production_bridge_intent_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    proposal_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prompt_trace: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prompt_messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    response_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expected_entries: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    response_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    candidate: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    provider_request_id: Mapped[str | None] = mapped_column(String(255))
    response_hash: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    result_proposal_revision: Mapped[int | None] = mapped_column(Integer)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
