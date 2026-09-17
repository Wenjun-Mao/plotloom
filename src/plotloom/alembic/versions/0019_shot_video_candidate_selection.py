"""Persist revisioned shot-scoped video candidate selection."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0019_shot_video_candidate_selection"
down_revision = "0018_video_cancel_intent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_video_candidate_selections",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("shot_id", sa.String(100), primary_key=True),
        sa.Column("selected_video_job_id", sa.String(67), sa.ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "shot_id", name="uq_v2_video_candidate_selection_shot"),
    )


def downgrade() -> None:
    op.drop_table("v2_video_candidate_selections")
