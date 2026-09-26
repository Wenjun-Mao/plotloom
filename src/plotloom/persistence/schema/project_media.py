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


class ManagedAssetRow(Base):
    """One project-scoped declaration over immutable imported bytes."""

    __tablename__ = "v2_managed_assets"
    __table_args__ = (Index("ix_v2_managed_assets_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    original_uri: Mapped[str] = mapped_column(Text, nullable=False)
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    display_uri: Mapped[str] = mapped_column(Text, nullable=False)
    display_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
class ManagedAssetProvenanceRow(Base):
    """An immutable origin declaration, intentionally separate from byte identity."""

    __tablename__ = "v2_managed_asset_provenance"
    __table_args__ = (Index("ix_v2_managed_asset_provenance_asset_id", "asset_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    declaration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class VisualIntentRow(Base):
    __tablename__ = "v2_visual_intents"
    __table_args__ = (Index("ix_v2_visual_intents_project_id_asset_id", "project_id", "asset_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    intent: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VisualSelectionStateRow(Base):
    __tablename__ = "v2_visual_selection_states"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewedShotBindingRow(Base):
    __tablename__ = "v2_reviewed_shot_bindings"
    __table_args__ = (
        Index("ix_v2_reviewed_shot_bindings_project_shot_revision", "project_id", "shot_id", "selection_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    visual_intent_id: Mapped[str | None] = mapped_column(ForeignKey("v2_visual_intents.id", ondelete="RESTRICT"), nullable=True)
    visual_intent_revision: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    storyboard_entity_revision_id: Mapped[str] = mapped_column(ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    storyboard_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    compatibility_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StillPreviewRow(Base):
    __tablename__ = "v2_still_previews"
    __table_args__ = (Index("ix_v2_still_previews_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    storyboard_entity_revision_id: Mapped[str] = mapped_column(ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    selection_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# P2 intentionally has its own lifecycle.  These rows are not MediaTask rows:
# Historical raw-shot media submission is not admitted by project storage.

class VideoJobRow(Base):
    __tablename__ = "v2_video_jobs"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="uq_v2_video_jobs_project_idempotency"),
        Index("ix_v2_video_jobs_project_created", "project_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_prediction_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VideoEndFrameDecisionRow(Base):
    """Append-only shot decision; a later revision invalidates frozen video inputs."""

    __tablename__ = "v2_video_end_frame_decisions"
    __table_args__ = (
        UniqueConstraint("project_id", "shot_id", "revision", name="uq_v2_video_end_frame_shot_revision"),
        Index("ix_v2_video_end_frame_shot", "project_id", "shot_id", "revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True)
    original_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    aspect_policy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    storyboard_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_timing: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VideoReviewRow(Base):
    __tablename__ = "v2_video_reviews"
    __table_args__ = (Index("ix_v2_video_reviews_job_created", "video_job_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_job_id: Mapped[str] = mapped_column(ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VideoCandidateSelectionRow(Base):
    """The revisioned, per-shot authority for one selected video candidate."""

    __tablename__ = "v2_video_candidate_selections"
    __table_args__ = (UniqueConstraint("project_id", "shot_id", name="uq_v2_video_candidate_selection_shot"),)

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    shot_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    selected_video_job_id: Mapped[str | None] = mapped_column(ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VideoSegmentRow(Base):
    """Immutable reviewed playback proposal; selection is CAS-bound to its shot revision."""

    __tablename__ = "v2_video_segments"
    __table_args__ = (
        UniqueConstraint("project_id", "shot_id", "selected_revision", name="uq_v2_video_segment_selected_revision"),
        Index("ix_v2_video_segments_job_created", "video_job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    video_job_id: Mapped[str] = mapped_column(ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=False)
    source_binding: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_binding_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    in_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    out_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    authored_duration_units: Mapped[int] = mapped_column(Integer, nullable=False)
    source_probe: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    derivative_probe: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    derivative_uri: Mapped[str] = mapped_column(Text, nullable=False)
    derivative_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_revision: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectVideoDispatchRow(Base):
    """Project evidence binding one job to an application-owned lease ID.

    The application database deliberately has no project foreign key.  This
    row is the project-side half of the cross-database dispatch boundary.
    """

    __tablename__ = "v2_project_video_dispatches"

    video_job_id: Mapped[str] = mapped_column(
        ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), primary_key=True
    )
    dispatch_identity: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionUnitRow(Base):
    """A single-shot approved projection frozen for P1 image work."""

    __tablename__ = "v2_production_units"
    __table_args__ = (Index("ix_v2_production_units_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
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
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
