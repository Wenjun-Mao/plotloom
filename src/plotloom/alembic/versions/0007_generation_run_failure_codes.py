"""Stable run-level failure classification for pre-attempt failures.

Revision ID: 0007_v2_run_failure_codes
Revises: 0006_v2_model_profiles
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_v2_run_failure_codes"
down_revision = "0006_v2_model_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("v2_generation_runs") as batch:
        batch.add_column(sa.Column("failure_code", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("failed_stage", sa.String(length=32), nullable=True))
    # 0006 intentionally terminated pre-contract non-terminal runs before
    # these columns existed. Backfill only its exact application-owned error;
    # arbitrary historic prose must never be parsed into a new classification.
    op.execute(
        """
        UPDATE v2_generation_runs
        SET failure_code = 'migration.execution_contract_changed'
        WHERE failure_code IS NULL
          AND status = 'failed'
          AND error = 'Generation run predates the frozen model-profile/topology contract; submit a new run'
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("v2_generation_runs") as batch:
        batch.drop_column("failed_stage")
        batch.drop_column("failure_code")
