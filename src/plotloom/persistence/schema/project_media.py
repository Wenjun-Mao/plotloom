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


# Registration must remain between asset and visual declarations (no DDL change).
from . import project_reference_appearance as _reference_appearance  # noqa: E402,F401


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
    confirmation_receipt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
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
