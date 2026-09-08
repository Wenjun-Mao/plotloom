"""Add reversible availability state without changing profile configuration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_text_profile_availability"
down_revision = "0010_v2_schema_approvals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These columns are deliberately outside the settings JSON. Existing
    # snapshots, hashes, plans, and receipts stay byte-for-byte historical.
    op.add_column(
        "v2_text_provider_profiles",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "v2_text_provider_profiles",
        sa.Column("availability_revision", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    with op.batch_alter_table("v2_text_provider_profiles") as batch:
        batch.drop_column("availability_revision")
        batch.drop_column("enabled")
