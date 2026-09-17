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
    # One explicit transition preserves retained selections made under the
    # retired latest-review projection. New reads use this table exclusively.
    op.execute("""
        INSERT INTO v2_video_candidate_selections
          (project_id, shot_id, selected_video_job_id, revision, updated_at)
        SELECT job.project_id, json_extract(job.snapshot, '$.shot.id'), review.video_job_id, 1, review.created_at
        FROM v2_video_reviews AS review
        JOIN v2_video_jobs AS job ON job.id = review.video_job_id
        WHERE review.decision = 'select'
          AND review.id = (
            SELECT newer.id
            FROM v2_video_reviews AS newer
            JOIN v2_video_jobs AS newer_job ON newer_job.id = newer.video_job_id
            WHERE newer_job.project_id = job.project_id
              AND json_extract(newer_job.snapshot, '$.shot.id') = json_extract(job.snapshot, '$.shot.id')
            ORDER BY newer.created_at DESC, newer.id DESC LIMIT 1
          )
    """)


def downgrade() -> None:
    op.drop_table("v2_video_candidate_selections")
