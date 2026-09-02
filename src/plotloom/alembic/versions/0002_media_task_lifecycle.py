from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_v2_media_lifecycle"
down_revision = "0001_v2_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "v2_media_tasks",
        sa.Column("provider_task_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "v2_media_tasks",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "v2_media_tasks",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("v2_media_tasks") as batch:
        batch.drop_column("finished_at")
        batch.drop_column("started_at")
        batch.drop_column("provider_task_id")
