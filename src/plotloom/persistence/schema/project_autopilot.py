"""Project-owned orchestration and separate machine/provisional evidence."""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AutopilotRunRow(Base):
    __tablename__ = "v2_autopilot_runs"
    __table_args__ = (
        UniqueConstraint("project_id"), UniqueConstraint("id", "project_id"),
        CheckConstraint("state IN ('running','waiting','paused','cancelled','stale','blocked','awaiting_review','handed_off','taken_over')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    brief_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    brief_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    claim: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_closure: Mapped[str] = mapped_column(String(64), nullable=False)
    blocker: Mapped[dict[str, str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    bundle: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    bundle_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handoff: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AutopilotCheckpointRow(Base):
    __tablename__ = "v2_autopilot_checkpoints"
    __table_args__ = (
        ForeignKeyConstraint(["run_id", "project_id"], ["v2_autopilot_runs.id", "v2_autopilot_runs.project_id"], ondelete="CASCADE"),
        UniqueConstraint("run_id", "operation_key"), UniqueConstraint("id", "run_id", "project_id"),
        CheckConstraint("state IN ('prepared','sent','outcome_unknown','failed','delivered','adopted')", name="ck_v2_autopilot_checkpoints_state"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation_key: Mapped[str] = mapped_column(String(160), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AutopilotExecAttemptRow(Base):
    """One project-owned initial CLI attempt and its atomic image budget."""
    __tablename__ = "v2_autopilot_exec_attempts"
    __table_args__ = (
        ForeignKeyConstraint(["run_id", "project_id"], ["v2_autopilot_runs.id", "v2_autopilot_runs.project_id"], ondelete="CASCADE"),
        UniqueConstraint("run_id", "operation_key"),
        UniqueConstraint("project_id", "job_id"),
        CheckConstraint("state IN ('reserved','spawn_intent','running','outcome_unknown','cancel_requested','completed','failed','settled')"),
        CheckConstraint("domain IN ('text','image')"),
        CheckConstraint("image_budget_state IN ('none','reserved','consumed','released')"),
        CheckConstraint("(domain = 'text' AND image_budget_state = 'none' AND reserved_image_outputs = 0) OR (domain = 'image' AND image_budget_state != 'none' AND reserved_image_outputs BETWEEN 1 AND 4)"),
        Index("ix_v2_autopilot_exec_attempts_run_state", "run_id", "state"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation_key: Mapped[str] = mapped_column(String(160), nullable=False)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    image_budget_state: Mapped[str] = mapped_column(String(12), nullable=False)
    reserved_image_outputs: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    receipt: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AutopilotDecisionRow(Base):
    __tablename__ = "v2_autopilot_decisions"
    __table_args__ = (
        ForeignKeyConstraint(["run_id", "project_id"], ["v2_autopilot_runs.id", "v2_autopilot_runs.project_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["checkpoint_id", "run_id", "project_id"], ["v2_autopilot_checkpoints.id", "v2_autopilot_checkpoints.run_id", "v2_autopilot_checkpoints.project_id"], ondelete="RESTRICT"),
        UniqueConstraint("id", "project_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    checkpoint_id: Mapped[str] = mapped_column(String(36), nullable=False)
    scope: Mapped[str] = mapped_column(String(40), nullable=False)
    decision: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AutopilotFrameRow(Base):
    __tablename__ = "v2_autopilot_frames"
    __table_args__ = (
        ForeignKeyConstraint(["run_id", "project_id"], ["v2_autopilot_runs.id", "v2_autopilot_runs.project_id"], ondelete="CASCADE"),
        UniqueConstraint("run_id", "shot_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    decision_id: Mapped[str] = mapped_column(ForeignKey("v2_autopilot_decisions.id", ondelete="RESTRICT"), nullable=False)
    frame: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AutopilotHandoffRow(Base):
    """Append-only human handoffs; a run pointer never replaces review history."""
    __tablename__ = "v2_autopilot_handoffs"
    __table_args__ = (
        ForeignKeyConstraint(["run_id", "project_id"], ["v2_autopilot_runs.id", "v2_autopilot_runs.project_id"], ondelete="CASCADE"),
        UniqueConstraint("id", "project_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    receipt: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
