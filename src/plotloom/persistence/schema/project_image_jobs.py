"""Image production units, frozen jobs and delivery candidates."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base



class ProductionUnitRow(Base):
    """A single-shot approved projection frozen for P1 image work."""

    __tablename__ = "v2_production_units"
    __table_args__ = (
        Index("ix_v2_production_units_project_id_created_at", "project_id", "created_at"),
        CheckConstraint("(approval_id IS NOT NULL AND machine_decision_id IS NULL) OR (approval_id IS NULL AND machine_decision_id IS NOT NULL)", name="ck_production_unit_authority"),
        ForeignKeyConstraint(["machine_decision_id", "project_id"], ["v2_autopilot_decisions.id", "v2_autopilot_decisions.project_id"], ondelete="RESTRICT"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=True)
    machine_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    storyboard_entity_revision_id: Mapped[str] = mapped_column(ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    storyboard_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImageJobRow(Base):
    """One immutable manual assignment and its current applicability state."""

    __tablename__ = "v2_image_jobs"
    __table_args__ = (Index("ix_v2_image_jobs_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    production_unit_id: Mapped[str] = mapped_column(ForeignKey("v2_production_units.id", ondelete="RESTRICT"), nullable=False)
    parent_job_id: Mapped[str | None] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=True)
    parent_candidate_asset_id: Mapped[str | None] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImageJobDeliveryRow(Base):
    """Immutable reconciliation evidence, including rejected/late packages."""

    __tablename__ = "v2_image_job_deliveries"
    __table_args__ = (
        UniqueConstraint("job_id", "delivery_id", name="uq_v2_image_job_delivery_identity"),
        Index("ix_v2_image_job_deliveries_job_id_created_at", "job_id", "created_at"),
        Index(
            "uq_v2_image_job_final_delivery",
            "job_id",
            unique=True,
            sqlite_where=text("delivery_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    diagnostic_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImageJobCandidateRow(Base):
    """Link a managed original to the exact manual image delivery that produced it."""

    __tablename__ = "v2_image_job_candidates"
    __table_args__ = (
        UniqueConstraint("delivery_id", "asset_id", name="uq_v2_image_job_candidate_delivery_asset"),
        Index("ix_v2_image_job_candidates_job_id_created_at", "job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("v2_image_job_deliveries.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(180), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


