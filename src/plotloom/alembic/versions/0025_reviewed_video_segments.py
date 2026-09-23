"""Persist non-destructive reviewed video playback segment proposals."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0025_reviewed_video_segments"
down_revision = "0024_art_reference_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_video_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_id", sa.String(100), nullable=False),
        sa.Column("video_job_id", sa.String(67), sa.ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_binding", sa.JSON(), nullable=False),
        sa.Column("source_binding_hash", sa.String(64), nullable=False),
        sa.Column("original_hash", sa.String(64), nullable=False),
        sa.Column("in_frame", sa.Integer(), nullable=False),
        sa.Column("out_frame", sa.Integer(), nullable=False),
        sa.Column("authored_duration_units", sa.Integer(), nullable=False),
        sa.Column("source_probe", sa.JSON(), nullable=False),
        sa.Column("derivative_probe", sa.JSON(), nullable=False),
        sa.Column("derivative_uri", sa.Text(), nullable=False),
        sa.Column("derivative_hash", sa.String(64), nullable=False),
        sa.Column("proposal_hash", sa.String(64), nullable=False),
        sa.Column("selected_revision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "shot_id", "selected_revision", name="uq_v2_video_segment_selected_revision"),
    )
    op.create_index("ix_v2_video_segments_job_created", "v2_video_segments", ["video_job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_v2_video_segments_job_created", table_name="v2_video_segments")
    op.drop_table("v2_video_segments")
