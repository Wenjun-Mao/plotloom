from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

from ...domain import ProjectLifecycleStatus

class ProjectRow(Base):
    __tablename__ = "v2_projects"
    __table_args__ = (
        Index(
            "ix_v2_projects_lifecycle_status_created_at_id",
            "lifecycle_status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lifecycle_status: Mapped[str] = mapped_column(String(16), nullable=False, default=ProjectLifecycleStatus.ACTIVE.value)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectOperationalStateRow(Base):
    """Copy-safety state, deliberately separate from author lifecycle state."""

    __tablename__ = "v2_project_operational_states"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectCreationIdempotencyRow(Base):
    __tablename__ = "v2_project_creation_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
class ProjectDuplicateIdempotencyRow(Base):
    __tablename__ = "v2_project_duplicate_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    copied_through: Mapped[str | None] = mapped_column(String(32), nullable=True)
    omitted_stages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EntityRevisionRow(Base):
    __tablename__ = "v2_entity_revisions"
    __table_args__ = (UniqueConstraint("project_id", "stage", "revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StageHeadRow(Base):
    __tablename__ = "v2_stage_heads"
    __table_args__ = (UniqueConstraint("project_id", "stage"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    stale_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthoringDraftRow(Base):
    """Mutable, allowlisted editor state owned by exactly one project DB."""

    __tablename__ = "v2_authoring_drafts"
    __table_args__ = (UniqueConstraint("project_id", "editor_scope", "entity_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True
    )
    editor_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    base_canonical_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GateResultRow(Base):
    """An immutable evaluation result for one exact canonical revision."""

    __tablename__ = "v2_gate_results"
    __table_args__ = (
        UniqueConstraint("entity_revision_id", "gate_set_version", "gate_id"),
        UniqueConstraint("entity_revision_id", "gate_set_version", "sequence"),
        Index("ix_v2_gate_results_project_id", "project_id"),
        Index("ix_v2_gate_results_entity_revision_id", "entity_revision_id"),
    )

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    entity_revision_id: Mapped[str] = mapped_column(
        ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_set_version: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    # Gate IDs include stable authoring IDs to make review paths readable.
    # They are intentionally unbounded text; the row primary key is a fixed
    # hash so database identity never depends on authored identifier length.
    gate_id: Mapped[str] = mapped_column(Text, nullable=False)
    gate_version: Mapped[str] = mapped_column(String(128), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_path: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApprovalDecisionRow(Base):
    """Append-only human approval ledger; current state is derived, never stored."""

    __tablename__ = "v2_approval_decisions"
    __table_args__ = (
        Index("ix_v2_approval_decisions_project_id_created_at", "project_id", "created_at"),
        Index("ix_v2_approval_decisions_entity_revision_id", "entity_revision_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    entity_revision_id: Mapped[str] = mapped_column(
        ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    gate_set_version: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(256), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
