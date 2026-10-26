from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CharacterReferenceStateRow(Base):
    """The mutable pointer/revision over immutable reference decisions."""

    __tablename__ = "v2_character_reference_states"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceDecisionRow(Base):
    """An append-only asset/hash/context reference decision for one character."""

    __tablename__ = "v2_character_reference_decisions"
    __table_args__ = (
        UniqueConstraint("project_id", "character_id", "reference_revision", name="uq_v2_character_reference_revision"),
        Index("ix_v2_character_reference_decisions_project_character", "project_id", "character_id", "reference_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    character_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    character_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    complementary_asset_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    asset_hashes: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceProposalRow(Base):
    """A non-Approval exploratory character appearance request."""

    __tablename__ = "v2_character_reference_proposals"
    __table_args__ = (Index("ix_v2_character_reference_proposals_project_created", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_candidate_asset_id: Mapped[str | None] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceProposalDeliveryRow(Base):
    __tablename__ = "v2_character_reference_proposal_deliveries"
    __table_args__ = (
        UniqueConstraint("proposal_id", "delivery_id", name="uq_v2_character_proposal_delivery_identity"),
        Index("uq_v2_character_proposal_final_delivery", "proposal_id", unique=True, sqlite_where=text("delivery_id IS NOT NULL")),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_character_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    diagnostic_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    publication_phase: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceProposalCandidateRow(Base):
    __tablename__ = "v2_character_reference_proposal_candidates"
    __table_args__ = (UniqueConstraint("delivery_id", "asset_id", name="uq_v2_character_proposal_candidate_asset"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_character_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("v2_character_reference_proposal_deliveries.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(180), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtReferenceProposalRow(Base):
    """A manual environment/prop study tied to one accepted-art revision."""

    __tablename__ = "v2_art_reference_proposals"
    __table_args__ = (Index("ix_v2_art_reference_proposals_project_created", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtReferenceProposalDeliveryRow(Base):
    __tablename__ = "v2_art_reference_proposal_deliveries"
    __table_args__ = (
        UniqueConstraint("proposal_id", "delivery_id", name="uq_v2_art_proposal_delivery_identity"),
        Index("uq_v2_art_proposal_final_delivery", "proposal_id", unique=True, sqlite_where=text("delivery_id IS NOT NULL")),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_art_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    diagnostic_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtReferenceProposalCandidateRow(Base):
    __tablename__ = "v2_art_reference_proposal_candidates"
    __table_args__ = (UniqueConstraint("delivery_id", "asset_id", name="uq_v2_art_proposal_candidate_asset"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_art_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("v2_art_reference_proposal_deliveries.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(180), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtReferenceDecisionStateRow(Base):
    """CAS head for one explicit environment or prop reference decision."""

    __tablename__ = "v2_art_reference_decision_states"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_decision_id: Mapped[str | None] = mapped_column(ForeignKey("v2_art_reference_decisions.id", ondelete="RESTRICT"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtReferenceDecisionRow(Base):
    """Append-only F3B subject choice; it has no production-consumption meaning."""

    __tablename__ = "v2_art_reference_decisions"
    __table_args__ = (
        Index("ix_v2_art_reference_decisions_project_subject", "project_id", "subject_type", "subject_id", "reference_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_art_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_art_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    subject_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    asset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_art_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("v2_art_reference_proposal_candidates.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SamePersonReviewStateRow(Base):
    __tablename__ = "v2_same_person_review_states"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SamePersonReviewRow(Base):
    __tablename__ = "v2_same_person_reviews"
    __table_args__ = (Index("ix_v2_same_person_reviews_project_binding_revision", "project_id", "binding_id", "review_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    binding_id: Mapped[str] = mapped_column(ForeignKey("v2_reviewed_shot_bindings.id", ondelete="RESTRICT"), nullable=False)
    review_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_bindings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    comparisons: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # Empty only for a receipt-bound unnamed creator confirmation (ADR0162).
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
