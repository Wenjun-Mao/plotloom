from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_v2_project_creation_idempotency"
down_revision = "0003_v2_repair_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_project_creation_idempotency",
        sa.Column("idempotency_key", sa.String(length=255), primary_key=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("v2_projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("v2_project_creation_idempotency")
