"""Keep P2 cancellation intent separate from provider execution state."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0018_video_cancel_intent"
down_revision = "0017_bounded_wan_video_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("v2_video_jobs") as batch:
        batch.add_column(sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("v2_video_jobs") as batch:
        batch.drop_column("cancel_requested_at")
