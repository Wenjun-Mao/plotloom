from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_v2_repair_lineage"
down_revision = "0002_v2_media_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "v2_generation_runs",
        sa.Column("repair_source", sa.JSON(), nullable=True),
    )
    op.add_column(
        "v2_artifacts",
        sa.Column("source_artifact_id", sa.String(length=36), nullable=True),
    )
    # Pre-contract queued repairs cannot be resumed safely because they did not
    # freeze exact evidence IDs. Preserve their history but force a fresh repair.
    op.execute(
        """
        UPDATE v2_generation_runs
        SET status = 'failed',
            error = 'Legacy repair lacked frozen evidence; create a new repair run',
            finished_at = CURRENT_TIMESTAMP
        WHERE kind = 'repair'
          AND status IN ('queued', 'running', 'cancel_requested')
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("v2_artifacts") as batch:
        batch.drop_column("source_artifact_id")
    with op.batch_alter_table("v2_generation_runs") as batch:
        batch.drop_column("repair_source")
